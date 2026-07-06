"""Unit tests for DataflowSpec view graph queries and normalization."""

from __future__ import annotations

import json

import pytest

from dataflow.dataflow_spec import DataflowSpec
from dataflow.enums import SourceType
from dataflow.expectations import DataQualityExpectations
from dataflow.features import Features
from dataflow.targets import TargetDeltaStreamingTable
from dataflow.view import View


def _minimal_spec(**overrides) -> DataflowSpec:
    base = {
        "dataFlowId": "flow_1",
        "dataFlowGroup": "grp",
        "dataFlowType": "STANDARD",
        "targetFormat": "DELTA",
        "targetDetails": {"table": "catalog.schema.target_table", "type": "st"},
        "flowGroups": [],
    }
    base.update(overrides)
    return DataflowSpec(**base)


class TestDataflowSpecNormalization:
    def test_lowercases_type_fields(self, pipeline_context):
        spec = _minimal_spec(
            dataFlowType="FLOW",
            targetFormat="DELTA",
            quarantineMode="TABLE",
        )
        assert spec.dataFlowType == "flow"
        assert spec.targetFormat == "delta"
        assert spec.quarantineMode == "table"

    def test_quarantine_mode_none_when_unset(self, pipeline_context):
        spec = _minimal_spec()
        assert spec.quarantineMode is None


class TestDataflowSpecViewGraph:
    @pytest.fixture
    def views_spec(self, fixtures_dir) -> DataflowSpec:
        payload = json.loads(
            (fixtures_dir / "specs" / "dataflow_with_views.json").read_text()
        )
        return DataflowSpec(**payload)

    def test_get_all_views_collects_views_from_flows(self, pipeline_context, views_spec):
        views = views_spec.get_all_views()
        assert set(views) == {
            "v_cdf_source",
            "v_live_source",
            "v_staging_target",
            "v_external",
        }
        assert all(isinstance(v, View) for v in views.values())

    def test_get_all_cdf_delta_views_filters_cdf_enabled_delta(self, pipeline_context, views_spec):
        cdf_views = views_spec.get_all_cdf_delta_views()
        assert list(cdf_views) == ["v_cdf_source"]
        assert cdf_views["v_cdf_source"].isCdfEnabled is True

    def test_get_all_delta_source_views_excludes_live_and_target_tables(
        self, pipeline_context, views_spec
    ):
        source_views = views_spec.get_all_delta_source_views()
        assert "v_cdf_source" in source_views
        assert "v_external" in source_views
        assert "v_live_source" not in source_views
        assert "v_staging_target" not in source_views


class TestDataflowSpecAccessors:
    def test_get_cdc_settings_returns_none_when_unset(self, pipeline_context):
        spec = _minimal_spec()
        assert spec.get_cdc_settings() is None

    def test_get_cdc_settings_builds_cdc_settings(self, pipeline_context):
        spec = _minimal_spec(
            cdcSettings={
                "keys": ["id"],
                "sequence_by": "ts",
                "scd_type": "1",
            }
        )
        settings = spec.get_cdc_settings()
        assert settings.keys == ["id"]
        assert settings.sequence_by == "ts"

    def test_get_data_quality_expectations_when_disabled(self, pipeline_context):
        spec = _minimal_spec(dataQualityExpectationsEnabled=False)
        assert spec.get_data_quality_expectations() is None

    def test_get_data_quality_expectations_when_enabled(self, pipeline_context):
        spec = _minimal_spec(
            dataQualityExpectationsEnabled=True,
            dataQualityExpectations={
                "expectationsJson": {},
                "expectRules": {"id_ok": "id IS NOT NULL"},
            },
        )
        expectations = spec.get_data_quality_expectations()
        assert isinstance(expectations, DataQualityExpectations)
        assert expectations.expectRules == {"id_ok": "id IS NOT NULL"}

    def test_get_features_returns_features_dataclass(self, pipeline_context):
        spec = _minimal_spec(features={"operationalMetadataEnabled": False})
        features = spec.get_features()
        assert isinstance(features, Features)
        assert features.operationalMetadataEnabled is False

    def test_get_target_details_uses_factory(self, pipeline_context):
        spec = _minimal_spec(
            targetDetails={"table": "catalog.schema.orders", "type": "st"}
        )
        target = spec.get_target_details()
        assert isinstance(target, TargetDeltaStreamingTable)
        assert target.table == "catalog.schema.orders"
