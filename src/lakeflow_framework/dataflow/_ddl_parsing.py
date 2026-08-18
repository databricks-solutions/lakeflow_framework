"""Shared helpers for parsing Spark column DDL schema files (.ddl).

Used by schema-on-read sources and Delta targets so blank-line filtering,
constraint separation, and column-name extraction stay consistent (#132, #133, #139).
"""

from __future__ import annotations

import re
from typing import List, Tuple

import pyspark.sql.types as T

CONSTRAINT_KEY_WORDS = ("CONSTRAINT ", "PRIMARY KEY ", "FOREIGN KEY ")

_SIMPLE_TYPES = {
    "INT": T.IntegerType(),
    "INTEGER": T.IntegerType(),
    "BIGINT": T.LongType(),
    "LONG": T.LongType(),
    "SMALLINT": T.ShortType(),
    "TINYINT": T.ByteType(),
    "STRING": T.StringType(),
    "BOOLEAN": T.BooleanType(),
    "BOOL": T.BooleanType(),
    "DOUBLE": T.DoubleType(),
    "FLOAT": T.FloatType(),
    "REAL": T.FloatType(),
    "DATE": T.DateType(),
    "TIMESTAMP": T.TimestampType(),
    "BINARY": T.BinaryType(),
}

_DECIMAL_RE = re.compile(r"^DECIMAL\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)$", re.IGNORECASE)
_LINE_RE = re.compile(
    r"^(?:`(?P<qname>[^`]+)`|(?P<name>\S+))\s+(?P<type>.+?)\s*$",
    re.IGNORECASE,
)


def parse_ddl_text(text: str) -> Tuple[List[str], List[str]]:
    """Split DDL text into column lines and constraint lines.

    Blank / whitespace-only lines and ``--`` comments are dropped (#139).
    """
    lines = [line.strip().rstrip(",") for line in text.split("\n")]
    lines = [line for line in lines if line and not line.startswith("--")]
    constraints = [line for line in lines if line.startswith(CONSTRAINT_KEY_WORDS)]
    columns = [line for line in lines if not line.startswith(CONSTRAINT_KEY_WORDS)]
    return columns, constraints


def parse_ddl_file(path: str) -> Tuple[List[str], List[str]]:
    """Read a ``.ddl`` file and return ``(column_lines, constraint_lines)``."""
    with open(path, encoding="utf-8") as fh:
        return parse_ddl_text(fh.read())


def ddl_column_name(line: str) -> str:
    """Extract the column name from a DDL column line (supports backticks)."""
    token = line.strip().split()[0] if line.strip() else ""
    if len(token) >= 2 and token.startswith("`") and token.endswith("`"):
        return token[1:-1]
    return token


def _data_type_from_ddl(type_str: str) -> T.DataType:
    """Map a DDL type token to a Spark ``DataType`` without requiring a session."""
    cleaned = type_str.strip().rstrip(",").strip()
    upper = cleaned.upper()
    if upper in _SIMPLE_TYPES:
        return _SIMPLE_TYPES[upper]
    decimal_match = _DECIMAL_RE.match(cleaned)
    if decimal_match:
        return T.DecimalType(int(decimal_match.group(1)), int(decimal_match.group(2)))
    # Prefer Spark's parser when a session is available (complex / nested types).
    try:
        return T.DataType.fromDDL(cleaned)
    except Exception:
        return T.StringType()


def _struct_from_ddl_column_lines_local(column_lines: List[str]) -> T.StructType:
    """Build a ``StructType`` without an active Spark session (unit-test safe)."""
    fields: List[T.StructField] = []
    for line in column_lines:
        match = _LINE_RE.match(line.strip())
        if not match:
            continue
        name = match.group("qname") or match.group("name")
        fields.append(T.StructField(name, _data_type_from_ddl(match.group("type")), True))
    return T.StructType(fields)


def struct_from_ddl_column_lines(column_lines: List[str]) -> T.StructType | None:
    """Build a ``StructType`` from DDL column lines.

    Prefers ``StructType.fromDDL`` when a Spark session is available; falls back
    to a local parser for unit tests and environments without an active session.
    """
    if not column_lines:
        return None
    joined = ",\n".join(column_lines)
    try:
        return T.StructType.fromDDL(joined)
    except Exception:
        return _struct_from_ddl_column_lines_local(column_lines)
