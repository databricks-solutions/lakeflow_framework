"""
Pluggable pipeline logging: default stdout logger, optional custom logger from logger.json,
and CompositeLogger (custom primary + framework stdout mirror).
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, Optional

from constants import FrameworkPaths, PipelineBundlePaths

if TYPE_CHECKING:
    from pyspark.dbutils import DBUtils
    from pyspark.sql import SparkSession

_REQUIRED_LOG_METHODS = ("debug", "info", "warning", "error", "critical", "exception")

_DEFAULT_LOGGER_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "factory_args": {},
    "level": "INFO",
    "mirror_to_stdout": False,
    "allow_pipeline_logger_override": False,
}


def create_default_logger(logger_name: str, log_level: str = "INFO") -> logging.Logger:
    """Create a framework default logger writing to stdout."""
    logger = logging.getLogger(logger_name)
    level = getattr(logging, log_level.upper(), None) or logging.INFO
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    return logger


def load_logger_config(config_path: str) -> Dict[str, Any]:
    """
    Load logger.json from disk. Missing or invalid files return {} and log a warning
    via a one-off default logger when possible.
    """
    if not config_path or not __import__("os").path.isfile(config_path):
        return {}

    try:
        from utility import get_json_from_file

        data = get_json_from_file(config_path, fail_on_not_exists=False)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        bootstrap = create_default_logger("DltFramework.LoggerConfig")
        bootstrap.warning(
            "Failed to load logger config from %s: %s. Using empty logger config for this source.",
            config_path,
            exc,
        )
        return {}


def merge_logger_config(
    framework_config: Optional[Dict[str, Any]],
    bundle_config: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merge framework and bundle logger.json.

    allow_pipeline_logger_override (framework only, default false):
      false -> framework wins on conflicts
      true  -> bundle wins on conflicts
    """
    framework = deepcopy(framework_config or {})
    bundle = deepcopy(bundle_config or {})
    bundle.pop("allow_pipeline_logger_override", None)

    allow_override = bool(framework.get("allow_pipeline_logger_override", False))
    # Last update wins: framework by default, bundle when override is allowed.
    base, override = (framework, bundle) if allow_override else (bundle, framework)

    merged = deepcopy(_DEFAULT_LOGGER_CONFIG)
    merged.update(base)
    merged.update(override)

    merged_factory_args = deepcopy(_DEFAULT_LOGGER_CONFIG["factory_args"])
    merged_factory_args.update(base.get("factory_args") or {})
    merged_factory_args.update(override.get("factory_args") or {})
    merged["factory_args"] = merged_factory_args

    merged["allow_pipeline_logger_override"] = allow_override
    return merged


def _library_importable(library_name: str) -> bool:
    return importlib.util.find_spec(library_name) is not None


def _validate_logger_api(logger_obj: Any) -> None:
    for name in _REQUIRED_LOG_METHODS:
        method = getattr(logger_obj, name, None)
        if not callable(method):
            raise TypeError(
                f"Custom logger must provide a callable '{name}' method; got {type(method).__name__}"
            )


def _resolve_log_level(config: Dict[str, Any], spark_log_level: Optional[str]) -> str:
    if spark_log_level:
        return spark_log_level.upper()
    level = config.get("level", "INFO")
    return str(level).upper() if level else "INFO"


class CompositeLogger:
    """Custom logger as primary; framework default logger mirrors to stdout."""

    def __init__(self, primary: Any, mirror: logging.Logger) -> None:
        self._primary = primary
        self._mirror = mirror

    def close(self) -> None:
        closer = getattr(self._primary, "close", None)
        if callable(closer):
            closer()

    def _call_primary(self, method_name: str, message: str, args: tuple, kwargs: Dict[str, Any]) -> None:
        method = getattr(self._primary, method_name)
        if kwargs:
            method(message, **kwargs)
        elif args:
            method(message, *args)
        else:
            method(message)

    def _call_mirror(self, method_name: str, message: str, args: tuple, kwargs: Dict[str, Any]) -> None:
        method = getattr(self._mirror, method_name)
        if kwargs:
            method(message, *args, **kwargs)
        elif args:
            method(message, *args)
        else:
            method(message)

    def _log(self, method_name: str, message: str, *args: Any, **kwargs: Any) -> None:
        try:
            self._call_primary(method_name, message, args, kwargs)
        except Exception as exc:
            self._mirror.warning(
                "Custom logger failed in %s: %s",
                method_name,
                exc,
                exc_info=True,
            )
        try:
            self._call_mirror(method_name, message, args, kwargs)
        except Exception:
            pass

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log("debug", message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log("info", message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log("warning", message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log("error", message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log("critical", message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._log("exception", message, *args, **kwargs)


def resolve_logger(
    spark: "SparkSession",
    dbutils: "DBUtils",
    effective_config: Dict[str, Any],
    spark_log_level: Optional[str] = None,
    logger_name: str = "DltFramework",
) -> Any:
    """
    Resolve the pipeline logger: default only, custom only, or CompositeLogger.
    Never raises; falls back to default logger and logs warnings on failure.
    """
    level = _resolve_log_level(effective_config, spark_log_level)
    default_logger = create_default_logger(logger_name, level)

    if not effective_config.get("enabled", False):
        return default_logger

    library = effective_config.get("library")
    if library and not _library_importable(str(library)):
        default_logger.warning(
            "Logger library %r not found; using framework default logger only.",
            library,
        )
        return default_logger

    module_name = effective_config.get("module")
    factory_name = effective_config.get("factory")
    if not module_name or not factory_name:
        default_logger.warning(
            "Custom logger enabled but module/factory not configured; using framework default logger only."
        )
        return default_logger

    try:
        module = importlib.import_module(str(module_name))
        factory = getattr(module, str(factory_name))
        factory_args = dict(effective_config.get("factory_args") or {})
        # Inject the resolved log level so pipeline-level logLevel settings
        # (e.g. spark.conf logLevel = "DEBUG") propagate to the custom logger.
        # Only set if the factory accepts a "level" kwarg (detected by checking
        # factory_args; the factory itself must handle the kwarg).
        factory_args["level"] = level
        custom = factory(dbutils, spark, **factory_args)
        _validate_logger_api(custom)
    except Exception as exc:
        default_logger.warning(
            "Failed to initialize custom logger: %s",
            exc,
            exc_info=True,
        )
        return default_logger

    if effective_config.get("mirror_to_stdout", False):
        return CompositeLogger(primary=custom, mirror=default_logger)

    # Custom logger owns output. Silence the Python logging registry entry so
    # any code holding a direct logging.getLogger() reference stays quiet.
    default_logger.handlers.clear()
    default_logger.addHandler(logging.NullHandler())
    return custom


def load_framework_logger_config(framework_path: str, framework_config_root: str) -> Dict[str, Any]:
    """Load framework logger.json using the local-config resolver.

    Loads ``src/config/default/logger.json`` and deep-merges
    ``src/local/config/logger.json`` on top if present.
    The legacy ``framework_config_root`` argument is accepted for backward
    compatibility but ignored when it points to ``config/default``; when it
    points to ``config/override`` a deprecation warning is emitted by the
    underlying resolver.
    """
    from config_resolver import load_framework_config

    return load_framework_config(FrameworkPaths.LOGGER_CONFIG, framework_path, fail_on_not_exists=False)


def load_bundle_logger_config(bundle_path: str) -> Dict[str, Any]:
    """Load pipeline bundle logger.json from pipeline_configs."""
    import os

    path = os.path.join(bundle_path, PipelineBundlePaths.PIPELINE_CONFIGS_PATH, PipelineBundlePaths.LOGGER_CONFIG)
    return load_logger_config(path)


def resolve_pipeline_logger(
    spark: "SparkSession",
    dbutils: "DBUtils",
    framework_path: str,
    bundle_path: str,
    framework_config_root: Optional[str] = None,
    spark_log_level: Optional[str] = None,
) -> Any:
    """Load, merge, and resolve logger from framework and bundle logger.json files."""
    framework_cfg = load_framework_logger_config(framework_path, framework_config_root or "")
    bundle_cfg = load_bundle_logger_config(bundle_path)
    effective = merge_logger_config(framework_cfg, bundle_cfg)
    return resolve_logger(spark, dbutils, effective, spark_log_level=spark_log_level)
