"""Unit tests for schema-on-read source schema loading (#132)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pyspark.sql import DataFrame

from lakeflow_framework.dataflow.sources.base import BaseSourceWithSchemaOnRead, ReadConfig


@dataclass
class _SchemaOnReadStub(BaseSourceWithSchemaOnRead):
    """Minimal concrete source for testing schemaPath loading."""

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        raise NotImplementedError


class TestBaseSourceWithSchemaOnRead:
    def test_loads_json_schema(self, pipeline_context, fixtures_dir):
        source = _SchemaOnReadStub(
            schemaPath=str(fixtures_dir / "schemas" / "minimal_struct.json")
        )
        assert source.schema_struct.fieldNames() == ["id", "name"]

    def test_loads_ddl_schema(self, pipeline_context, tmp_path):
        """Sources must accept .ddl schemaPath like targets (#132)."""
        schema_path = tmp_path / "customers.ddl"
        schema_path.write_text("`customer_id` INT,\n`email` STRING\n")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        assert source.schema_struct.fieldNames() == ["customer_id", "email"]

    def test_ddl_with_blank_lines(self, pipeline_context, tmp_path):
        schema_path = tmp_path / "blank.ddl"
        schema_path.write_text("`a` STRING,\n\n`b` INT\n")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        assert source.schema_struct.fieldNames() == ["a", "b"]

    def test_rejects_unsupported_extension(self, pipeline_context, tmp_path):
        schema_path = tmp_path / "schema.txt"
        schema_path.write_text("id INT")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        with pytest.raises(ValueError, match="Unsupported schema file extension"):
            _ = source.schema_struct
