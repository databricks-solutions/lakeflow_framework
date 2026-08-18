"""Unit tests for schema-on-read source schema loading (#132)."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from pyspark.sql import DataFrame

from lakeflow_framework.dataflow.sources.base import BaseSourceWithSchemaOnRead, ReadConfig


@dataclass
class _SchemaOnReadStub(BaseSourceWithSchemaOnRead):
    """Minimal concrete source for testing schemaPath loading."""

    def _get_df(self, read_config: ReadConfig) -> DataFrame:
        raise NotImplementedError


class TestBaseSourceWithSchemaOnReadJson:
    def test_loads_json_schema(self, pipeline_context, fixtures_dir):
        source = _SchemaOnReadStub(
            schemaPath=str(fixtures_dir / "schemas" / "minimal_struct.json")
        )
        assert source.schema_type == "json"
        assert source.schema_struct.fieldNames() == ["id", "name"]
        assert source.schema_ddl is None

    def test_schema_json_returns_raw_file_contents(self, pipeline_context, tmp_path):
        """JSON schema paths keep the file contents verbatim, without a struct round-trip."""
        raw = {"type": "struct", "fields": [{"name": "id", "type": "integer"}]}
        schema_path = tmp_path / "no_metadata.json"
        schema_path.write_text(json.dumps(raw))
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        assert source.schema_json == raw
        assert source.schema_struct.fieldNames() == ["id"]


class TestBaseSourceWithSchemaOnReadDdl:
    def test_loads_ddl_schema(self, pipeline_context, tmp_path):
        """Sources must accept .ddl schemaPath like targets (#132)."""
        schema_path = tmp_path / "customers.ddl"
        schema_path.write_text("`customer_id` INT,\n`email` STRING\n")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        assert source.schema_type == "ddl"
        assert source.schema_struct.fieldNames() == ["customer_id", "email"]

    def test_ddl_with_blank_lines(self, pipeline_context, tmp_path):
        schema_path = tmp_path / "blank.ddl"
        schema_path.write_text("`a` STRING,\n\n`b` INT\n")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        assert source.schema_struct.fieldNames() == ["a", "b"]
        assert ",\n," not in source.schema_ddl

    def test_schema_ddl_excludes_constraints(self, pipeline_context, tmp_path):
        """Constraints are not applicable to a read schema."""
        schema_path = tmp_path / "constrained.ddl"
        schema_path.write_text("id INT,\nname STRING,\nCONSTRAINT pk PRIMARY KEY (id)\n")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        assert source.schema_ddl == "id INT,\nname STRING"
        assert source.schema_struct.fieldNames() == ["id", "name"]

    def test_schema_json_derived_from_ddl(self, pipeline_context, tmp_path):
        schema_path = tmp_path / "derived.ddl"
        schema_path.write_text("id INT,\nname STRING\n")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        assert source.schema_json == source.schema_struct.jsonValue()


class TestBaseSourceWithSchemaOnReadEdgeCases:
    def test_no_schema_path(self, pipeline_context):
        source = _SchemaOnReadStub()
        assert source.schema_type is None
        assert source.schema_struct is None
        assert source.schema_ddl is None
        assert source.schema_json == {}

    @pytest.mark.parametrize("prop", ["schema_struct", "schema_json", "schema_ddl", "schema_type"])
    def test_rejects_unsupported_extension(self, pipeline_context, tmp_path, prop):
        schema_path = tmp_path / "schema.txt"
        schema_path.write_text("id INT")
        source = _SchemaOnReadStub(schemaPath=str(schema_path))
        with pytest.raises(ValueError, match="Unsupported schema file extension"):
            getattr(source, prop)
