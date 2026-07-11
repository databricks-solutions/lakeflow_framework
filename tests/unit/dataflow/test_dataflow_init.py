"""Unit tests for DataFlow initialization wiring (no SDP decorator execution)."""

from __future__ import annotations

import pyspark.sql.types as T
import pytest

from lakeflow_framework.constants import SystemColumns
from lakeflow_framework.dataflow.dataflow import DataFlow
from lakeflow_framework.dataflow.dataflow_spec import DataflowSpec
from lakeflow_framework.dataflow.enums import QuarantineMode, SinkType, TargetType
from lakeflow_framework.dataflow.flow_group import FlowGroup
from lakeflow_framework.dataflow.flows.append_sql import FlowAppendSql
from lakeflow_framework.dataflow.targets.staging_table import StagingTable


def _streaming_spec(**overrides) -> DataflowSpec:
    base = {
        "dataFlowId": "init_flow",
        "dataFlowGroup": "grp",
        "dataFlowType": "standard",
        "targetFormat": TargetType.DELTA,
        "targetDetails": {"table": "catalog.schema.orders", "type": "st"},
        "flowGroups": [],
    }
    base.update(overrides)
    return DataflowSpec(**base)


class TestDataFlowInitQuarantine:
    def test_enables_quarantine_when_expectations_and_rules_present(
        self, pipeline_context, monkeypatch
    ):
        captured = {}

        class FakeQuarantineManager:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def add_quarantine_columns_delta(self, target_details):
                return target_details

        monkeypatch.setattr(
            "lakeflow_framework.dataflow.dataflow.QuarantineManager", FakeQuarantineManager
        )
        spec = _streaming_spec(
            dataQualityExpectationsEnabled=True,
            dataQualityExpectations={
                "expectationsJson": {},
                "expectRules": {"id_ok": "id IS NOT NULL"},
            },
            quarantineMode=QuarantineMode.TABLE,
        )
        dataflow = DataFlow(spec)
        assert dataflow.quarantine_enabled is True
        assert captured["quarantine_mode"] == QuarantineMode.TABLE
        assert captured["data_quality_rules"] == {"id_ok": "id IS NOT NULL"}

    def test_disables_quarantine_when_mode_off(self, pipeline_context):
        spec = _streaming_spec(
            dataQualityExpectationsEnabled=True,
            dataQualityExpectations={
                "expectationsJson": {},
                "expectRules": {"id_ok": "id IS NOT NULL"},
            },
            quarantineMode=QuarantineMode.OFF,
        )
        dataflow = DataFlow(spec)
        assert dataflow.quarantine_enabled is False

    def test_disables_quarantine_without_expectations(self, pipeline_context):
        spec = _streaming_spec(quarantineMode=QuarantineMode.TABLE)
        dataflow = DataFlow(spec)
        assert dataflow.quarantine_enabled is False


class TestDataFlowInitExpectations:
    def test_raises_when_expectations_enabled_but_missing_object(self, pipeline_context):
        spec = _streaming_spec(dataQualityExpectationsEnabled=True)
        with pytest.raises(RuntimeError, match="Expectations object is None"):
            DataFlow(spec)

    def test_loads_expectations_clause_when_enabled(self, pipeline_context):
        spec = _streaming_spec(
            dataQualityExpectationsEnabled=True,
            dataQualityExpectations={
                "expectationsJson": {},
                "expectRules": {"id_ok": "id IS NOT NULL"},
                "expectOrDropRules": {"qty_ok": "qty > 0"},
            },
        )
        dataflow = DataFlow(spec)
        assert dataflow.expectations_clause == {
            "expect_all": {"id_ok": "id IS NOT NULL"},
            "expect_all_or_drop": {"qty_ok": "qty > 0"},
            "expect_all_or_fail": {},
        }


class TestDataFlowInitCdc:
    def test_adds_scd2_columns_for_cdc_settings(self, pipeline_context, fixtures_dir):
        schema_path = fixtures_dir / "schemas" / "minimal_struct.json"
        spec = _streaming_spec(
            targetDetails={
                "table": "catalog.schema.orders",
                "type": "st",
                "schemaPath": str(schema_path),
            },
            cdcSettings={
                "keys": ["id"],
                "sequence_by": "updated_at",
                "scd_type": "2",
            },
        )
        dataflow = DataFlow(spec)
        field_names = dataflow.target_details.schema_struct.fieldNames()
        assert SystemColumns.SCD2Columns.SCD2_START_AT.value in field_names
        assert SystemColumns.SCD2Columns.SCD2_END_AT.value in field_names

    def test_skips_scd2_columns_without_target_schema(self, pipeline_context):
        spec = _streaming_spec(
            cdcSettings={
                "keys": ["id"],
                "sequence_by": "updated_at",
                "scd_type": "2",
            },
        )
        dataflow = DataFlow(spec)
        assert not hasattr(dataflow.target_details, "schema_struct") or (
            dataflow.target_details.schema_struct is None
        )


class TestDataFlowInitTableMigration:
    def test_skips_migration_for_non_delta_target(self, pipeline_context):
        spec = DataflowSpec(
            dataFlowId="sink_flow",
            dataFlowGroup="grp",
            dataFlowType="standard",
            targetFormat=TargetType.DELTA_SINK,
            targetDetails={"name": "out_sink"},
            flowGroups=[],
            tableMigrationDetails={
                "enabled": True,
                "catalogType": "uc",
                "sourceDetails": {"database": "db", "table": "src"},
            },
        )
        dataflow = DataFlow(spec)
        assert dataflow.table_migration_manager is None

    def test_skips_migration_when_details_empty(self, pipeline_context):
        dataflow = DataFlow(_streaming_spec(tableMigrationDetails={}))
        assert dataflow.table_migration_manager is None

    def test_creates_migration_manager_when_configured(self, pipeline_context):
        spec = _streaming_spec(
            tableMigrationDetails={
                "enabled": False,
                "catalogType": "uc",
                "sourceDetails": {"database": "db", "table": "src"},
            },
        )
        dataflow = DataFlow(spec)
        assert dataflow.table_migration_manager is not None


class TestDataFlowHelpers:
    def test_is_target_matches_main_delta_table(self, pipeline_context):
        dataflow = DataFlow(_streaming_spec())
        assert dataflow.is_target("catalog.schema.orders") is True
        assert dataflow.is_target("other_table") is False

    def test_is_target_matches_sink_name(self, pipeline_context):
        spec = DataflowSpec(
            dataFlowId="sink_flow",
            dataFlowGroup="grp",
            dataFlowType="standard",
            targetFormat=TargetType.KAFKA_SINK,
            targetDetails={"name": "kafka_out"},
            flowGroups=[],
        )
        dataflow = DataFlow(spec)
        assert dataflow.is_target("kafka_out") is True
        assert dataflow.is_target("other") is False

    def test_get_column_prefix_exceptions_includes_scd2_columns(self, pipeline_context):
        dataflow = DataFlow(_streaming_spec())
        exceptions = dataflow._get_column_prefix_exceptions()
        assert SystemColumns.SCD2Columns.SCD2_START_AT.value in exceptions
        assert SystemColumns.SCD2Columns.SCD2_END_AT.value in exceptions

    def test_get_cdc_settings_uses_target_level_settings(self, pipeline_context):
        spec = _streaming_spec(
            cdcSettings={
                "keys": ["id"],
                "sequence_by": "updated_at",
                "scd_type": "1",
            },
        )
        dataflow = DataFlow(spec)
        flow = FlowAppendSql(
            flowName="f_target",
            flowType="append_sql",
            flowDetails={
                "targetTable": "catalog.schema.orders",
                "sqlStatement": "SELECT 1",
            },
        )
        result = dataflow._get_cdc_settings(flow, {})
        assert result["cdc_settings"].keys == ["id"]
        assert result["cdc_snapshot_settings"] is None

    def test_get_cdc_settings_uses_staging_table_settings(self, pipeline_context):
        dataflow = DataFlow(_streaming_spec())
        flow = FlowAppendSql(
            flowName="f_staging",
            flowType="append_sql",
            flowDetails={"targetTable": "stg_orders", "sqlStatement": "SELECT 1"},
        )
        staging = StagingTable(
            table="stg_orders",
            type="st",
            cdcSettings={
                "keys": ["id"],
                "sequence_by": "updated_at",
                "scd_type": "1",
            },
        )
        result = dataflow._get_cdc_settings(flow, {"stg_orders": staging})
        assert result["cdc_settings"].sequence_by == "updated_at"

    def test_get_cdc_settings_raises_when_staging_table_missing(self, pipeline_context):
        dataflow = DataFlow(_streaming_spec())
        flow = FlowAppendSql(
            flowName="f_staging",
            flowType="append_sql",
            flowDetails={"targetTable": "missing_stg", "sqlStatement": "SELECT 1"},
        )
        with pytest.raises(ValueError, match="Staging table not found"):
            dataflow._get_cdc_settings(flow, {})

    def test_prepare_flow_config_uses_target_config_flags_for_target_flow(
        self, pipeline_context,
    ):
        spec = _streaming_spec(
            targetDetails={
                "table": "catalog.schema.orders",
                "type": "st",
                "configFlags": ["disableOperationalMetadata"],
            }
        )
        dataflow = DataFlow(spec)
        flow = FlowAppendSql(
            flowName="f_target",
            flowType="append_sql",
            flowDetails={
                "targetTable": "catalog.schema.orders",
                "sqlStatement": "SELECT 1",
            },
        )
        config = dataflow._prepare_flow_config(flow, {})
        assert config.target_config_flags == ["disableOperationalMetadata"]

    def test_prepare_flow_config_uses_staging_flags_for_non_target_flow(
        self, pipeline_context,
    ):
        dataflow = DataFlow(_streaming_spec())
        flow = FlowAppendSql(
            flowName="f_staging",
            flowType="append_sql",
            flowDetails={"targetTable": "stg_orders", "sqlStatement": "SELECT 1"},
        )
        staging = StagingTable(
            table="stg_orders",
            type="st",
            configFlags=["disableOperationalMetadata"],
        )
        config = dataflow._prepare_flow_config(flow, {"stg_orders": staging})
        assert config.target_config_flags == ["disableOperationalMetadata"]
