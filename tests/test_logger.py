"""Tests for pluggable pipeline logger (merge, resolve, composite)."""

import logging
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, "src")

from logger import (  # noqa: E402
    CompositeLogger,
    create_default_logger,
    merge_logger_config,
    resolve_logger,
)


class _StubCustomLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str, *args, **kwargs) -> None:
        self.messages.append(f"debug:{message}")

    def info(self, message: str, *args, **kwargs) -> None:
        self.messages.append(f"info:{message}")

    def warning(self, message: str, *args, **kwargs) -> None:
        self.messages.append(f"warning:{message}")

    def error(self, message: str, *args, **kwargs) -> None:
        self.messages.append(f"error:{message}")

    def critical(self, message: str, *args, **kwargs) -> None:
        self.messages.append(f"critical:{message}")

    def exception(self, message: str, *args, **kwargs) -> None:
        self.messages.append(f"exception:{message}")


def _stub_factory(dbutils, spark, **kwargs):
    return _StubCustomLogger()


class TestLogger(unittest.TestCase):
    def test_merge_framework_wins_by_default(self):
        framework = {"enabled": True, "level": "DEBUG", "factory_args": {"a": 1}}
        bundle = {"enabled": False, "level": "ERROR", "factory_args": {"b": 2}}
        merged = merge_logger_config(framework, bundle)
        self.assertTrue(merged["enabled"])
        self.assertEqual(merged["level"], "DEBUG")
        self.assertEqual(merged["factory_args"], {"a": 1, "b": 2})

    def test_merge_bundle_wins_when_override_allowed(self):
        framework = {
            "enabled": True,
            "level": "DEBUG",
            "allow_pipeline_logger_override": True,
            "factory_args": {"a": 1},
        }
        bundle = {"enabled": False, "level": "ERROR", "factory_args": {"b": 2}}
        merged = merge_logger_config(framework, bundle)
        self.assertFalse(merged["enabled"])
        self.assertEqual(merged["level"], "ERROR")

    def test_resolve_disabled_returns_default_logger(self):
        spark = MagicMock()
        dbutils = MagicMock()
        result = resolve_logger(spark, dbutils, {"enabled": False}, spark_log_level="WARNING")
        self.assertIsInstance(result, logging.Logger)
        self.assertEqual(result.level, logging.WARNING)

    def test_resolve_missing_library_falls_back_to_default(self):
        spark = MagicMock()
        dbutils = MagicMock()
        config = {
            "enabled": True,
            "library": "nonexistent_logger_lib_xyz",
            "module": "any",
            "factory": "any",
        }
        result = resolve_logger(spark, dbutils, config)
        self.assertIsInstance(result, logging.Logger)

    def test_resolve_custom_with_mirror(self):
        spark = MagicMock()
        dbutils = MagicMock()
        config = {
            "enabled": True,
            "module": __name__,
            "factory": "_stub_factory",
            "mirror_to_stdout": True,
            "factory_args": {},
        }
        result = resolve_logger(spark, dbutils, config)
        self.assertIsInstance(result, CompositeLogger)
        result.info("hello")
        self.assertIn("info:hello", result._primary.messages)

    def test_composite_primary_failure_still_mirrors(self):
        class _BrokenPrimary:
            def info(self, message, *args, **kwargs):
                raise RuntimeError("primary failed")

            def debug(self, *a, **k):
                pass

            def warning(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

            def critical(self, *a, **k):
                pass

            def exception(self, *a, **k):
                pass

        mirror = create_default_logger("test.mirror", "INFO")
        composite = CompositeLogger(primary=_BrokenPrimary(), mirror=mirror)
        composite.info("mirrored message")


if __name__ == "__main__":
    unittest.main()
