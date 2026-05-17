from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


class StructuredStdoutLogger:
    """Emits each log record as a single-line JSON object to stdout."""

    def __init__(self, level: str = "INFO", logger_name: str = "DltFramework") -> None:
        self._level_value: int = getattr(logging, level.upper(), logging.INFO)
        self._logger_name: str = logger_name

    def _should_emit(self, level: str) -> bool:
        return getattr(logging, level.upper(), logging.DEBUG) >= self._level_value

    def _emit(self, level: str, message: str, exc_info: str | None = None, **kwargs: Any) -> None:
        if not self._should_emit(level):
            return
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "logger": self._logger_name,
            "message": message,
        }
        if kwargs:
            record["extra"] = kwargs
        if exc_info:
            record["exc_info"] = exc_info
        print(json.dumps(record, default=str), file=sys.stdout, flush=True)

    @staticmethod
    def _format(message: str, args: tuple) -> str:
        if args:
            try:
                return message % args
            except (TypeError, ValueError):
                return f"{message} {args}"
        return message

    def _extract_exc_info(self, kwargs: dict) -> str | None:
        """Pop and resolve logging.Logger-compatible control kwargs."""
        exc_info = kwargs.pop("exc_info", None)
        kwargs.pop("stacklevel", None)
        kwargs.pop("stack_info", None)
        if exc_info is True:
            return traceback.format_exc()
        if isinstance(exc_info, str):
            return exc_info
        return None

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        if not self._should_emit("DEBUG"):
            return
        exc = self._extract_exc_info(kwargs)
        self._emit("DEBUG", self._format(message, args), exc_info=exc, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        if not self._should_emit("INFO"):
            return
        exc = self._extract_exc_info(kwargs)
        self._emit("INFO", self._format(message, args), exc_info=exc, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        if not self._should_emit("WARNING"):
            return
        exc = self._extract_exc_info(kwargs)
        self._emit("WARNING", self._format(message, args), exc_info=exc, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        if not self._should_emit("ERROR"):
            return
        exc = self._extract_exc_info(kwargs)
        self._emit("ERROR", self._format(message, args), exc_info=exc, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        if not self._should_emit("CRITICAL"):
            return
        exc = self._extract_exc_info(kwargs)
        self._emit("CRITICAL", self._format(message, args), exc_info=exc, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        kwargs.pop("exc_info", None)
        kwargs.pop("stacklevel", None)
        kwargs.pop("stack_info", None)
        self._emit("ERROR", self._format(message, args), exc_info=traceback.format_exc(), **kwargs)

    def close(self) -> None:
        pass


def get_logger(
    dbutils: Any,
    spark: Any,
    level: str = "INFO",
    logger_name: str = "DltFramework",
) -> StructuredStdoutLogger:
    """Factory called by the framework as factory(dbutils, spark, **factory_args)."""
    return StructuredStdoutLogger(level=level, logger_name=logger_name)