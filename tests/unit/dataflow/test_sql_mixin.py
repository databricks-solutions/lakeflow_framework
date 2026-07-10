"""Unit tests for SqlMixin SQL loading."""

from __future__ import annotations

import pytest
from dataclasses import dataclass

from lakeflow_framework.dataflow.sql import SqlMixin


@dataclass
class _SqlHolder(SqlMixin):
    pass


class TestSqlMixin:
    def test_prefers_sql_statement_over_file(self, tmp_path):
        sql_file = tmp_path / "query.sql"
        sql_file.write_text("SELECT from_file")
        holder = _SqlHolder(sqlPath=str(sql_file), sqlStatement="SELECT from_statement")
        assert holder.rawSql == "SELECT from_statement"

    def test_loads_sql_from_file(self, tmp_path):
        sql_file = tmp_path / "query.sql"
        sql_file.write_text("SELECT 1")
        holder = _SqlHolder(sqlPath=str(sql_file))
        assert holder.rawSql == "SELECT 1"
        assert holder.rawSql == "SELECT 1"

    def test_raises_when_sql_file_missing(self, tmp_path):
        holder = _SqlHolder(sqlPath=str(tmp_path / "missing.sql"))
        with pytest.raises(FileNotFoundError, match="Error loading sql file"):
            _ = holder.rawSql

    def test_raises_when_sql_file_empty(self, tmp_path):
        sql_file = tmp_path / "empty.sql"
        sql_file.write_text("   ")
        holder = _SqlHolder(sqlPath=str(sql_file))
        with pytest.raises(RuntimeError, match="Sql file empty or error"):
            _ = holder.rawSql

    def test_raises_when_no_sql_path_or_statement(self):
        holder = _SqlHolder()
        with pytest.raises(ValueError, match="Sql path and sql statement are None or empty"):
            _ = holder.rawSql
