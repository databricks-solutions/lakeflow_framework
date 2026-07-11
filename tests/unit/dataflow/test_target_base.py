"""Unit tests for BaseTargetDelta schema and validation logic."""

from __future__ import annotations

import pyspark.sql.types as T
import pytest

from lakeflow_framework.pipeline_config import initialize_mandatory_table_properties, initialize_operational_metadata_schema
from lakeflow_framework.dataflow.enums import TableType, TargetConfigFlags
from lakeflow_framework.dataflow.targets import TargetDeltaStreamingTable


class TestBaseTargetDeltaValidation:
    def test_rejects_invalid_table_type(self, pipeline_context):
        with pytest.raises(ValueError, match="Invalid table type"):
            TargetDeltaStreamingTable(table="t", type="invalid")

    def test_rejects_partition_and_cluster_columns_together(self, pipeline_context):
        with pytest.raises(ValueError, match="Cannot specify both partitionColumns and clusterByColumns"):
            TargetDeltaStreamingTable(
                table="t",
                type=TableType.STREAMING.value,
                partitionColumns=["d"],
                clusterByColumns=["id"],
            )

    def test_rejects_partition_columns_with_cluster_by_auto(self, pipeline_context):
        with pytest.raises(ValueError, match="Cannot specify partitionColumns and enable clusterByAuto"):
            TargetDeltaStreamingTable(
                table="t",
                type=TableType.STREAMING.value,
                partitionColumns=["d"],
                clusterByAuto=True,
            )

    def test_prefixes_table_with_database(self, pipeline_context):
        target = TargetDeltaStreamingTable(
            table="orders",
            database="silver_db",
            type=TableType.STREAMING.value,
        )
        assert target.table == "silver_db.orders"

    def test_normalizes_table_type_case(self, pipeline_context):
        target = TargetDeltaStreamingTable(table="t", type="ST")
        assert target.type == TableType.STREAMING.value


class TestBaseTargetDeltaSchemaJson:
    def test_loads_json_schema_from_path(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_struct.json"
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=str(schema_path),
        )
        assert target.schema_type == "json"
        assert target.schema_struct.fieldNames() == ["id", "name"]

    def test_rejects_unsupported_schema_extension(self, pipeline_context, tmp_path):
        schema_path = tmp_path / "schema.txt"
        schema_path.write_text("id INT")
        with pytest.raises(ValueError, match="Unsupported schema file extension"):
            TargetDeltaStreamingTable(
                table="t",
                type=TableType.STREAMING.value,
                schemaPath=str(schema_path),
            )

    def test_add_columns_appends_new_json_fields(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_struct.json"
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=str(schema_path),
        )
        target.add_columns([T.StructField("extra", T.StringType())])
        assert "extra" in target.schema_struct.fieldNames()

    def test_add_columns_skips_existing_json_fields(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_struct.json"
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=str(schema_path),
        )
        original_count = len(target.schema_struct.fields)
        target.add_columns([T.StructField("id", T.IntegerType())])
        assert len(target.schema_struct.fields) == original_count

    def test_remove_columns_drops_json_fields(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_struct.json"
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=str(schema_path),
        )
        target.remove_columns(["name"])
        assert target.schema_struct.fieldNames() == ["id"]

    def test_add_columns_requires_initialized_schema(self, pipeline_context):
        target = TargetDeltaStreamingTable(table="t", type=TableType.STREAMING.value)
        with pytest.raises(ValueError, match="schema structure is not initialized"):
            target.add_columns([T.StructField("x", T.StringType())])


class TestBaseTargetDeltaSchemaDdl:
    def test_parses_ddl_schema_and_constraints(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_table.ddl"
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=str(schema_path),
        )
        assert target.schema_type == "ddl"
        assert "id INT" in target.schema_ddl
        assert "CONSTRAINT pk PRIMARY KEY (id)" in target.schema_ddl

    def test_add_columns_appends_ddl_lines(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_table.ddl"
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=str(schema_path),
        )
        target.add_columns([T.StructField("extra", T.StringType())])
        assert "extra string" in target.schema_ddl


class TestBaseTargetDeltaProperties:
    def test_merges_mandatory_table_properties(self, pipeline_context):
        initialize_mandatory_table_properties({"delta.feature": "on"})
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            tableProperties={"custom.prop": "value"},
        )
        assert target.tableProperties["delta.feature"] == "on"
        assert target.tableProperties["custom.prop"] == "value"

    def test_disable_operational_metadata_clears_schema(self, pipeline_context):
        op_schema = T.StructType([T.StructField("meta", T.StringType())])
        initialize_operational_metadata_schema(op_schema)
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=None,
            configFlags=[TargetConfigFlags.DISABLE_OPERATIONAL_METADATA],
        )
        assert target.operational_metadata_schema is None

    def test_add_table_properties_merges_recursively(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_struct.json"
        target = TargetDeltaStreamingTable(
            table="t",
            type=TableType.STREAMING.value,
            schemaPath=str(schema_path),
            tableProperties={"outer": {"a": "1"}},
        )
        target.add_table_properties({"outer": {"b": "2"}, "new": "x"})
        assert target.tableProperties["outer"] == {"a": "1", "b": "2"}
        assert target.tableProperties["new"] == "x"
