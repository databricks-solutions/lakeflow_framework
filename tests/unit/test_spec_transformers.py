"""Unit tests for dataflow_spec_builder transformers."""

from __future__ import annotations

import pytest

from dataflow.enums import FlowType, Mode, SourceType, TableType
from dataflow_spec_builder.transformer.factory import SpecTransformerFactory
from dataflow_spec_builder.transformer.flow import FlowSpecTransformer
from dataflow_spec_builder.transformer.materialized_views import MaterializedViewSpecTransformer
from dataflow_spec_builder.transformer.standard import StandardSpecTransformer


class TestStandardSpecTransformer:
    def test_creates_main_flow_group_for_streaming_delta_target(self, pipeline_context):
        transformer = StandardSpecTransformer()
        spec = {
            "dataFlowId": "flow1",
            "dataFlowGroup": "grp",
            "dataFlowType": "standard",
            "sourceViewName": "v_source",
            "sourceType": "delta",
            "sourceDetails": {"database": "db", "table": "src"},
            "mode": Mode.STREAM,
            "targetFormat": "delta",
            "targetDetails": {"database": "db", "table": "tgt"},
        }
        result = transformer.transform(spec)
        assert result["targetDetails"]["type"] == "st"
        flow_group = result["flowGroups"][0]
        assert flow_group["flowGroupId"] == "main"
        flow = next(iter(flow_group["flows"].values()))
        assert flow["flowType"] == FlowType.APPEND_VIEW

    def test_uses_merge_flow_when_cdc_settings_present(self, pipeline_context):
        transformer = StandardSpecTransformer()
        spec = {
            "dataFlowId": "flow1",
            "dataFlowGroup": "grp",
            "dataFlowType": "standard",
            "sourceViewName": "v_source",
            "sourceType": "delta",
            "sourceDetails": {},
            "mode": Mode.STREAM,
            "targetFormat": "delta",
            "targetDetails": {"database": "db", "table": "tgt"},
            "cdcSettings": {"keys": ["id"]},
        }
        result = transformer.transform(spec)
        flow = next(iter(result["flowGroups"][0]["flows"].values()))
        assert flow["flowType"] == FlowType.MERGE


class TestFlowSpecTransformer:
    def test_sets_streaming_table_type_for_delta_flow(self, pipeline_context):
        transformer = FlowSpecTransformer()
        spec = {
            "dataFlowType": "flow",
            "targetFormat": "delta",
            "targetDetails": {"database": "db", "table": "tgt"},
        }
        result = transformer.transform(spec)
        assert result["targetDetails"]["type"] == "st"


class TestMaterializedViewSpecTransformer:
    def test_expands_materialized_views_into_flow_specs(self, pipeline_context):
        transformer = MaterializedViewSpecTransformer()
        spec = {
            "dataFlowId": "mv_flow",
            "dataFlowGroup": "grp",
            "dataFlowType": "materialized_view",
            "materializedViews": {
                "mv_orders": {
                    "tableDetails": {"database": "db"},
                    "sqlPath": "mv_orders.sql",
                    "sourceView": {
                        "sourceViewName": "v_orders",
                        "sourceType": SourceType.DELTA,
                        "sourceDetails": {"database": "db", "table": "orders"},
                    },
                }
            },
        }
        results = transformer.transform(spec)
        assert len(results) == 1
        mv_spec = results[0]
        assert mv_spec["targetDetails"]["table"] == "mv_orders"
        assert mv_spec["targetDetails"]["type"] == TableType.MATERIALIZED_VIEW
        flow = next(iter(mv_spec["flowGroups"][0]["flows"].values()))
        assert flow["flowType"] == FlowType.MATERIALIZED_VIEW


class TestSpecTransformerFactory:
    def test_create_transformer_for_each_supported_type(self, pipeline_context):
        assert isinstance(SpecTransformerFactory.create_transformer("standard"), StandardSpecTransformer)
        assert isinstance(SpecTransformerFactory.create_transformer("flow"), FlowSpecTransformer)
        assert isinstance(
            SpecTransformerFactory.create_transformer("materialized_view"),
            MaterializedViewSpecTransformer,
        )

    def test_raises_for_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown dataflow type"):
            SpecTransformerFactory.create_transformer("unknown")
