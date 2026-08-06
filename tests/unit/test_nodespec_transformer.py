"""Unit tests for the nodespec (node-graph) spec transformer.

Focus areas:
- basic source -> target streaming transformation
- the data_quality block with quarantine nested inside it
  (``data_quality.enabled`` / ``data_quality.quarantine.mode`` /
  ``data_quality.quarantine.target``)
- materialized-view expansion
- factory registration of the ``nodespec`` type
"""

from __future__ import annotations

import pytest

from lakeflow_framework.dataflow.enums import FlowType, TableType
from lakeflow_framework.dataflow_spec_builder.transformer.factory import SpecTransformerFactory
from lakeflow_framework.dataflow_spec_builder.transformer.nodespec import NodespecSpecTransformer


def _source(name="v_source_customer", table="customer"):
    return {
        "name": name,
        "node_type": "source",
        "source_type": "delta",
        "config": {"mode": "stream", "database": "db", "table": table, "cdf_enabled": True},
    }


def _spec(*nodes):
    return {
        "dataFlowId": "nodespec_test",
        "dataFlowGroup": "grp",
        "dataFlowType": "nodespec",
        "nodes": list(nodes),
    }


class TestNodespecStreaming:
    def test_source_to_target_produces_streaming_flow(self, pipeline_context):
        spec = _spec(
            _source(),
            {
                "name": "target_customer",
                "node_type": "target",
                "config": {
                    "table": "customer_silver",
                    "sources": [{"view": "v_source_customer", "flow": "f_load"}],
                },
            },
        )
        result = NodespecSpecTransformer().transform(spec)
        assert result["targetDetails"]["table"] == "customer_silver"
        assert result["targetDetails"]["type"] == TableType.STREAMING
        flow = next(iter(result["flowGroups"][0]["flows"].values()))
        assert flow["flowType"] == FlowType.APPEND_VIEW


class TestNodespecSourcesFlowNaming:
    """A bare view name derives the flow name the framework itself would use
    (``f_<view>``), so migrated specs need not restate a name the author never
    wrote. An explicit {view, flow} pins an authored name."""

    def _target(self, sources_value):
        return _spec(
            _source(),
            {
                "name": "target_customer",
                "node_type": "target",
                "config": {"table": "customer_silver", "sources": sources_value},
            },
        )

    def test_bare_view_name_derives_legacy_flow_name(self, pipeline_context):
        result = NodespecSpecTransformer().transform(self._target(["v_source_customer"]))
        assert set(result["flowGroups"][0]["flows"]) == {"f_v_source_customer"}

    def test_explicit_flow_name_is_preserved(self, pipeline_context):
        result = NodespecSpecTransformer().transform(
            self._target([{"view": "v_source_customer", "flow": "f_authored"}]))
        assert set(result["flowGroups"][0]["flows"]) == {"f_authored"}


class TestNodespecDataQuality:
    def _dq_target(self, data_quality):
        return _spec(
            _source(),
            {
                "name": "target_customer",
                "node_type": "target",
                "config": {
                    "table": "customer_silver",
                    "data_quality": data_quality,
                    "sources": [{"view": "v_source_customer", "flow": "f_load"}],
                },
            },
        )

    def test_quarantine_table_nested_under_data_quality(self, pipeline_context):
        spec = self._dq_target({
            "enabled": True,
            "expectations_path": "./customer_dqe.json",
            "quarantine": {
                "mode": "table",
                "target": {"target_format": "delta"},
            },
        })
        result = NodespecSpecTransformer().transform(spec)
        assert result["dataQualityExpectationsEnabled"] is True
        assert result["dataQualityExpectationsPath"] == "./customer_dqe.json"
        assert result["quarantineMode"] == "table"
        assert result["quarantineTargetDetails"] == {"target_format": "delta"}

    def test_enabled_false_is_honoured(self, pipeline_context):
        spec = self._dq_target({
            "enabled": False,
            "expectations_path": "./customer_dqe.json",
        })
        result = NodespecSpecTransformer().transform(spec)
        assert result["dataQualityExpectationsEnabled"] is False

    def test_enabled_defaults_true_when_omitted(self, pipeline_context):
        spec = self._dq_target({"expectations_path": "./customer_dqe.json"})
        result = NodespecSpecTransformer().transform(spec)
        assert result["dataQualityExpectationsEnabled"] is True

    def test_quarantine_flag_mode_has_no_target(self, pipeline_context):
        spec = self._dq_target({
            "enabled": True,
            "expectations_path": "./customer_dqe.json",
            "quarantine": {"mode": "flag"},
        })
        result = NodespecSpecTransformer().transform(spec)
        assert result["quarantineMode"] == "flag"
        assert "quarantineTargetDetails" not in result

    def test_data_quality_not_leaked_into_target(self, pipeline_context):
        spec = self._dq_target({
            "enabled": True,
            "expectations_path": "./customer_dqe.json",
            "quarantine": {"mode": "flag"},
        })
        result = NodespecSpecTransformer().transform(spec)
        assert "dataQuality" not in result["targetDetails"]
        assert "quarantine" not in result["targetDetails"]


class TestNodespecMaterializedView:
    def test_mv_target_expands_to_mv_spec(self, pipeline_context):
        spec = _spec(
            _source(name="v_mv_source", table="customer"),
            {
                "name": "target_customer_summary_mv",
                "node_type": "target",
                "config": {
                    "table": "customer_summary_mv",
                    "table_type": "mv",
                    "sources": [{"view": "v_mv_source", "flow": "f_mv_load"}],
                },
            },
        )
        results = NodespecSpecTransformer().transform(spec)
        mv_specs = [
            s for s in (results if isinstance(results, list) else [results])
            if s["targetDetails"].get("type") == TableType.MATERIALIZED_VIEW
        ]
        assert len(mv_specs) == 1
        assert mv_specs[0]["targetDetails"]["table"] == "customer_summary_mv"


class TestNodespecSnapshotFlows:
    """Snapshot targets read their source directly; the SDP snapshot API takes no
    flow name, so we must not synthesize a differently-named flow for a *staging*
    snapshot (the runtime builds it from the staging table's own settings)."""

    _SNAP = {
        "keys": ["id"], "scd_type": "1", "snapshot_type": "historical",
        "source_type": "file", "source": {"format": "csv", "path": "/data/s_{version}.csv"},
    }

    def test_terminal_historical_snapshot_keeps_its_flow(self, pipeline_context):
        spec = _spec({
            "name": "target_dim",
            "node_type": "target",
            "config": {"database": "db", "table": "dim", "cdc_snapshot_settings": self._SNAP},
        })
        result = NodespecSpecTransformer().transform(spec)
        flows = result["flowGroups"][0]["flows"]
        # terminal snapshot target needs a flow entry to drive the runtime
        assert len(flows) == 1
        assert next(iter(flows.values()))["flowDetails"]["targetTable"] == "db.dim"

    def test_staging_snapshot_emits_no_synthetic_flow(self, pipeline_context):
        # staging snapshot target (feeds the terminal target) + an append into the
        # terminal target. The staging snapshot must NOT get its own synthesized
        # flow — only the authored append flow should appear.
        spec = _spec(
            {
                "name": "target_stg",
                "node_type": "target",
                "config": {"table": "stg", "cdc_snapshot_settings": self._SNAP},
            },
            {
                "name": "v_stg_read",
                "node_type": "source",
                "source_type": "delta",
                "config": {"mode": "stream", "table": "stg", "as_view": False},
            },
            {
                "name": "target_final",
                "node_type": "target",
                "config": {
                    "database": "db", "table": "final",
                    "sources": [{"view": "v_stg_read", "flow": "f_stg_append"}],
                },
            },
        )
        result = NodespecSpecTransformer().transform(spec)
        fg = result["flowGroups"][0]
        # staging table is still registered (runtime drives its snapshot flow)
        assert "stg" in (fg.get("stagingTables") or {})
        # only the authored append flow — no f_historical_snapshot_for_stg
        assert set(fg["flows"]) == {"f_stg_append"}


class TestNodespecFactory:
    def test_factory_creates_nodespec_transformer(self, pipeline_context):
        assert isinstance(
            SpecTransformerFactory.create_transformer("nodespec"),
            NodespecSpecTransformer,
        )
