"""Unit tests for excluding operational metadata from SCD2 history tracking (dataflow/cdc.py, cdc_snapshot.py)."""

from __future__ import annotations

from types import SimpleNamespace

import pyspark.sql.types as T
import pytest

from lakeflow_framework.dataflow import cdc, cdc_snapshot
from lakeflow_framework.dataflow.cdc import (
    CDCFlow,
    CDCSettings,
    exclude_from_scd2_history,
    get_operational_metadata_columns,
)
from lakeflow_framework.dataflow.cdc_snapshot import CDCSnapshotFlow, CDCSnapshotSettings, CDCSnapshotTypes
from lakeflow_framework.dataflow.enums import TargetConfigFlags
from lakeflow_framework.dataflow.features import Features
from lakeflow_framework.dataflow.flows.merge import FlowMerge


METADATA_SCHEMA = T.StructType([
    T.StructField("meta_load_details", T.StructType([T.StructField("record_insert_timestamp", T.TimestampType())])),
])
_LOGGER = SimpleNamespace(debug=lambda *a, **k: None, info=lambda *a, **k: None, error=lambda *a, **k: None)


@pytest.fixture
def metadata_schema(monkeypatch):
    monkeypatch.setattr(cdc.pipeline_config, "get_operational_metadata_schema", lambda: METADATA_SCHEMA)
    monkeypatch.setattr(cdc.pipeline_config, "get_logger", lambda: _LOGGER)


@pytest.fixture
def captured_auto_cdc(monkeypatch, metadata_schema):
    calls = []
    monkeypatch.setattr(cdc, "dp", SimpleNamespace(create_auto_cdc_flow=lambda **kwargs: calls.append(kwargs)))
    return calls


class TestGetOperationalMetadataColumns:
    def test_returns_schema_columns_when_enabled(self, metadata_schema):
        assert get_operational_metadata_columns(Features(operationalMetadataEnabled=True)) == ["meta_load_details"]

    def test_empty_when_feature_disabled(self, metadata_schema):
        assert get_operational_metadata_columns(Features(operationalMetadataEnabled=False)) == []

    def test_empty_when_target_disables_it(self, metadata_schema):
        flags = [TargetConfigFlags.DISABLE_OPERATIONAL_METADATA]
        assert get_operational_metadata_columns(Features(), flags) == []

    def test_empty_without_features_or_schema(self, monkeypatch, metadata_schema):
        assert get_operational_metadata_columns(None) == []
        monkeypatch.setattr(cdc.pipeline_config, "get_operational_metadata_schema", lambda: None)
        assert get_operational_metadata_columns(Features()) == []


class TestExcludeFromSCD2History:
    def test_scd2_adds_columns(self):
        assert exclude_from_scd2_history("2", None, None, ["meta_load_details"]) == ["meta_load_details"]

    def test_scd2_keeps_spec_exclusions_without_duplicates(self):
        result = exclude_from_scd2_history("2", [], ["updated_by", "meta_load_details"], ["meta_load_details"])
        assert result == ["updated_by", "meta_load_details"]

    def test_scd1_is_unchanged(self):
        assert exclude_from_scd2_history("1", None, None, ["meta_load_details"]) is None

    def test_explicit_track_history_column_list_is_unchanged(self):
        assert exclude_from_scd2_history("2", ["status"], None, ["meta_load_details"]) is None

    def test_columns_not_written_to_target_are_not_added(self):
        assert exclude_from_scd2_history("2", None, None, ["meta_load_details"], ["meta_load_details"]) == []

    def test_nothing_to_add_is_unchanged(self):
        assert exclude_from_scd2_history("2", None, ["a"], []) == ["a"]


class TestCDCFlowHistory:
    def test_scd2_flow_excludes_operational_metadata(self, captured_auto_cdc):
        # Regression: meta_load_details changes on every load, so tracking it made SCD2 open a new
        # version for every re-delivered row even when no business column changed.
        settings = CDCSettings(keys=["id"], sequence_by="ts", scd_type="2")
        CDCFlow(settings).create(target_table="t", source_view_name="v", features=Features())
        assert captured_auto_cdc[0]["track_history_except_column_list"] == ["meta_load_details"]

    def test_scd1_flow_is_unchanged(self, captured_auto_cdc):
        settings = CDCSettings(keys=["id"], sequence_by="ts", scd_type="1")
        CDCFlow(settings).create(target_table="t", source_view_name="v", features=Features())
        assert captured_auto_cdc[0]["track_history_except_column_list"] == []

    def test_flow_without_features_is_unchanged(self, captured_auto_cdc):
        settings = CDCSettings(keys=["id"], sequence_by="ts", scd_type="2")
        CDCFlow(settings).create(target_table="t", source_view_name="v")
        assert captured_auto_cdc[0]["track_history_except_column_list"] == []

    def test_merge_flow_passes_features_and_flags(self, monkeypatch):
        received = {}

        class _FakeCDCFlow:
            def __init__(self, settings):
                pass

            def create(self, **kwargs):
                received.update(kwargs)

        monkeypatch.setattr("lakeflow_framework.dataflow.flows.merge.CDCFlow", _FakeCDCFlow)
        flow = SimpleNamespace(targetTable="t", sourceView="v", flowName="f")
        features = Features()
        flow_config = SimpleNamespace(cdc_settings=object(), cdc_snapshot_settings=None, target_config_flags=["x"])
        FlowMerge.create_flow(flow, SimpleNamespace(features=features), flow_config)
        assert received["features"] is features
        assert received["target_config_flags"] == ["x"]


class TestCDCSnapshotFlowHistory:
    def test_periodic_scd2_snapshot_excludes_operational_metadata(self, monkeypatch, metadata_schema):
        calls = []
        monkeypatch.setattr(cdc_snapshot.pipeline_config, "get_logger", lambda: _LOGGER)
        monkeypatch.setattr(
            cdc_snapshot, "dp", SimpleNamespace(create_auto_cdc_from_snapshot_flow=lambda **kwargs: calls.append(kwargs))
        )
        settings = CDCSnapshotSettings(keys=["id"], scd_type="2", snapshotType=CDCSnapshotTypes.PERIODIC)
        CDCSnapshotFlow(settings).create(
            dataflow_config=SimpleNamespace(features=Features()), target_table="t", source_view_name="v"
        )
        assert calls[0]["track_history_except_column_list"] == ["meta_load_details"]
