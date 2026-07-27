"""Unit tests for logger.py — config merge and CompositeLogger."""

from __future__ import annotations

import logging
import warnings
from unittest.mock import MagicMock

import pytest

from lakeflow_framework.logger import (
    CompositeLogger,
    CustomLoggerConfigWarning,
    create_default_logger,
    get_effective_logger_config,
    get_logger,
    resolve_pipeline_logger,
    _get_bundle_logger_config,
    _get_framework_logger_config,
    _get_logger_config_from_file,
    _resolve_log_level,
    _validate_logger_api,
)


class TestGetEffectiveLoggerConfig:
    def test_framework_wins_when_allow_pipeline_override_false(self):
        framework = {"enabled": True, "level": "DEBUG", "allow_pipeline_logger_override": False}
        bundle = {"enabled": False, "level": "ERROR"}
        merged = get_effective_logger_config(framework, bundle)
        assert merged["enabled"] is True
        assert merged["level"] == "DEBUG"

    def test_bundle_wins_when_allow_pipeline_override_true(self):
        framework = {
            "enabled": False,
            "level": "INFO",
            "allow_pipeline_logger_override": True,
            "factory_args": {"a": 1},
        }
        bundle = {"enabled": True, "level": "WARNING", "factory_args": {"b": 2}}
        merged = get_effective_logger_config(framework, bundle)
        assert merged["enabled"] is True
        assert merged["level"] == "WARNING"
        assert merged["factory_args"] == {"a": 1, "b": 2}


class TestResolveLogLevel:
    def test_spark_log_level_takes_precedence(self):
        assert _resolve_log_level({"level": "INFO"}, "debug") == "DEBUG"

    def test_falls_back_to_config_level(self):
        assert _resolve_log_level({"level": "warning"}, None) == "WARNING"


class TestCreateDefaultLogger:
    def test_creates_logger_with_handlers(self):
        logger = create_default_logger("test.default.logger", "INFO")
        assert logger.name == "test.default.logger"
        assert logger.handlers


class TestCompositeLogger:
    def test_logs_to_primary_and_mirror(self):
        primary = MagicMock()
        mirror = create_default_logger("test.mirror", "INFO")
        composite = CompositeLogger(primary=primary, mirror=mirror)
        composite.info("hello")
        primary.info.assert_called_once_with("hello")

    def test_primary_failure_still_attempts_mirror(self):
        primary = MagicMock()
        primary.info.side_effect = RuntimeError("primary failed")
        mirror = MagicMock()
        composite = CompositeLogger(primary=primary, mirror=mirror)
        composite.info("hello")
        mirror.info.assert_called_once()


class TestGetLogger:
    def test_returns_default_when_custom_logger_disabled(self):
        spark = MagicMock()
        dbutils = MagicMock()
        logger = get_logger(spark, dbutils, {"enabled": False}, logger_name="test.get")
        assert isinstance(logger, logging.Logger)

    def test_returns_composite_when_mirror_enabled(self, tmp_path, monkeypatch):
        mod_path = tmp_path / "custom_logger.py"
        mod_path.write_text(
            "def build_logger(dbutils, spark, **kwargs):\n"
            "    class L:\n"
            "        def debug(self, m, *a, **k): pass\n"
            "        def info(self, m, *a, **k): pass\n"
            "        def warning(self, m, *a, **k): pass\n"
            "        def error(self, m, *a, **k): pass\n"
            "        def critical(self, m, *a, **k): pass\n"
            "        def exception(self, m, *a, **k): pass\n"
            "    return L()\n"
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        spark = MagicMock()
        dbutils = MagicMock()
        config = {
            "enabled": True,
            "module": "custom_logger",
            "factory": "build_logger",
            "mirror_to_stdout": True,
        }
        logger = get_logger(spark, dbutils, config, logger_name="test.custom")
        assert isinstance(logger, CompositeLogger)

    def test_falls_back_when_custom_factory_fails(self, tmp_path, monkeypatch):
        mod_path = tmp_path / "broken_logger.py"
        mod_path.write_text("def build_logger(dbutils, spark, **kwargs):\n    raise RuntimeError('boom')\n")
        monkeypatch.syspath_prepend(str(tmp_path))
        spark = MagicMock()
        dbutils = MagicMock()
        config = {"enabled": True, "module": "broken_logger", "factory": "build_logger"}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            logger = get_logger(spark, dbutils, config, logger_name="test.fallback")
        assert isinstance(logger, logging.Logger)
        assert any(issubclass(w.category, CustomLoggerConfigWarning) for w in caught)


class TestLoggerConfigFiles:
    def test_get_logger_config_from_file_returns_empty_when_missing(self, tmp_path):
        assert _get_logger_config_from_file(str(tmp_path / "missing.json")) == {}

    def test_get_logger_config_from_file_loads_json(self, tmp_path):
        path = tmp_path / "logger.json"
        path.write_text('{"enabled": true, "level": "DEBUG"}')
        assert _get_logger_config_from_file(str(path))["level"] == "DEBUG"

    def test_get_framework_logger_config_reads_local_config(self, minimal_framework_tree):
        local = minimal_framework_tree / "local" / "config"
        local.mkdir(parents=True, exist_ok=True)
        (local / "logger.json").write_text('{"enabled": true, "level": "ERROR"}')
        cfg = _get_framework_logger_config(str(minimal_framework_tree))
        assert cfg["level"] == "ERROR"

    def test_get_bundle_logger_config_reads_pipeline_configs(self, tmp_path):
        configs = tmp_path / "pipeline_configs"
        configs.mkdir()
        (configs / "logger.json").write_text('{"enabled": false, "level": "WARNING"}')
        cfg = _get_bundle_logger_config(str(tmp_path))
        assert cfg["level"] == "WARNING"


class TestValidateLoggerApi:
    def test_raises_when_required_method_missing(self):
        with pytest.raises(TypeError, match="callable 'debug'"):
            _validate_logger_api(object())


class TestResolvePipelineLogger:
    def test_resolves_from_framework_and_bundle_configs(self, minimal_framework_tree, tmp_path):
        local = minimal_framework_tree / "local" / "config"
        local.mkdir(parents=True, exist_ok=True)
        (local / "logger.json").write_text('{"enabled": false, "level": "INFO"}')
        bundle = tmp_path / "bundle"
        configs = bundle / "pipeline_configs"
        configs.mkdir(parents=True)
        (configs / "logger.json").write_text('{"enabled": false}')
        spark = MagicMock()
        dbutils = MagicMock()
        logger = resolve_pipeline_logger(
            spark, dbutils, str(minimal_framework_tree), str(bundle)
        )
        assert isinstance(logger, logging.Logger)
