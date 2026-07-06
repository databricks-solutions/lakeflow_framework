"""Unit tests for dataflow source, target, and flow factories."""

from __future__ import annotations

import pytest

from dataflow.enums import FlowType, SourceType, TableType, TargetType
from dataflow.flows import FlowAppendSql, FlowAppendView, FlowMerge, FlowMaterializedView
from dataflow.flows.factory import FlowFactory
from dataflow.sources import SourceBatchFiles, SourceCloudFiles, SourceDelta, SourceDeltaJoin
from dataflow.sources import SourceKafka, SourcePython, SourceSql
from dataflow.sources.base import BaseSource
from dataflow.sources.factory import SourceFactory
from dataflow.targets import (
    TargetCustomPythonSink,
    TargetDeltaMaterializedView,
    TargetDeltaSink,
    TargetDeltaStreamingTable,
    TargetForEachBatchSink,
    TargetKafkaSink,
)
from dataflow.targets.factory import TargetFactory
from dataflow.targets.sink_foreach_batch import ForEachBatchSinkType


class TestSourceFactory:
    def test_creates_each_registered_source_type(self, pipeline_context):
        cases = [
            (SourceType.BATCH_FILES, {"format": "csv", "path": "/data"}, SourceBatchFiles),
            (SourceType.CLOUD_FILES, {"path": "/cloud"}, SourceCloudFiles),
            (SourceType.DELTA, {"database": "db", "table": "t"}, SourceDelta),
            (
                SourceType.DELTA_JOIN,
                {
                    "sources": [
                        {
                            "database": "db",
                            "table": "left_t",
                            "alias": "l",
                            "joinMode": "stream",
                        }
                    ],
                    "joins": [{"joinType": "inner", "condition": "l.id = r.id"}],
                },
                SourceDeltaJoin,
            ),
            (SourceType.KAFKA, {"topic": "events"}, SourceKafka),
            (SourceType.PYTHON, {"pythonFunction": lambda spark: None}, SourcePython),
            (SourceType.SQL, {"sqlStatement": "SELECT 1"}, SourceSql),
        ]
        for source_type, details, expected_cls in cases:
            source = SourceFactory.create(source_type, details)
            assert isinstance(source, expected_cls)

    def test_normalizes_source_type_case(self, pipeline_context):
        source = SourceFactory.create("DELTA", {"database": "db", "table": "t"})
        assert isinstance(source, SourceDelta)

    def test_raises_for_unsupported_source_type(self, pipeline_context):
        with pytest.raises(ValueError, match='Unsupported source type "unknown"'):
            SourceFactory.create("unknown", {})

    def test_register_source_adds_custom_type(self, pipeline_context):
        class DummySource(BaseSource):
            def _get_df(self, read_config):
                return None

        SourceFactory.register_source("dummy", DummySource)
        try:
            source = SourceFactory.create("dummy", {})
            assert isinstance(source, DummySource)
        finally:
            del SourceFactory._source_registry["dummy"]

    def test_register_source_rejects_duplicate(self, pipeline_context):
        with pytest.raises(ValueError, match='already registered'):
            SourceFactory.register_source(SourceType.DELTA, SourceDelta)


class TestTargetFactory:
    def test_creates_delta_streaming_table(self, pipeline_context):
        target = TargetFactory.create(
            TargetType.DELTA,
            {"table": "catalog.schema.orders", "type": TableType.STREAMING.value},
        )
        assert isinstance(target, TargetDeltaStreamingTable)

    def test_creates_delta_materialized_view(self, pipeline_context):
        target = TargetFactory.create(
            TargetType.DELTA,
            {
                "table": "catalog.schema.orders_mv",
                "type": TableType.MATERIALIZED_VIEW.value,
                "sourceView": "v_orders",
            },
        )
        assert isinstance(target, TargetDeltaMaterializedView)

    def test_creates_sink_targets(self, pipeline_context):
        assert isinstance(
            TargetFactory.create(TargetType.DELTA_SINK, {"name": "delta_out"}),
            TargetDeltaSink,
        )
        assert isinstance(
            TargetFactory.create(TargetType.KAFKA_SINK, {"name": "kafka_out"}),
            TargetKafkaSink,
        )
        assert isinstance(
            TargetFactory.create(
                TargetType.FOREACH_BATCH_SINK,
                {
                    "name": "batch_out",
                    "type": ForEachBatchSinkType.BASIC_SQL,
                    "config": {"sqlStatement": "SELECT 1"},
                },
            ),
            TargetForEachBatchSink,
        )
        assert isinstance(
            TargetFactory.create(TargetType.CUSTOM_PYTHON_SINK, {"name": "py_out"}),
            TargetCustomPythonSink,
        )

    def test_foreach_batch_sink_wires_sql_from_config(self, pipeline_context):
        target = TargetFactory.create(
            TargetType.FOREACH_BATCH_SINK,
            {
                "name": "batch_out",
                "type": ForEachBatchSinkType.BASIC_SQL,
                "config": {"sqlStatement": "SELECT * FROM micro_batch_view"},
            },
        )
        assert target.sqlStatement == "SELECT * FROM micro_batch_view"

    def test_delta_target_requires_table_type(self, pipeline_context):
        with pytest.raises(ValueError, match="Table type must be specified"):
            TargetFactory.create(TargetType.DELTA, {"table": "t"})

    def test_raises_for_unsupported_delta_table_type(self, pipeline_context):
        with pytest.raises(ValueError, match='Unsupported table type "invalid"'):
            TargetFactory.create(
                TargetType.DELTA,
                {"table": "t", "type": "invalid"},
            )

    def test_raises_for_unsupported_target_type(self, pipeline_context):
        with pytest.raises(ValueError, match='Unsupported target type "unknown"'):
            TargetFactory.create("unknown", {"name": "x"})


class TestFlowFactory:
    def test_creates_each_registered_flow_type(self, pipeline_context):
        base_details = {"targetTable": "t", "sqlStatement": "SELECT 1"}
        cases = [
            (FlowType.APPEND_SQL, FlowAppendSql),
            (
                FlowType.APPEND_VIEW,
                FlowAppendView,
                {
                    "targetTable": "t",
                    "sourceView": "v_src",
                    "views": {
                        "v_src": {
                            "mode": "stream",
                            "sourceType": "delta",
                            "sourceDetails": {"database": "db", "table": "src"},
                        }
                    },
                },
            ),
            (
                FlowType.MERGE,
                FlowMerge,
                {
                    "targetTable": "t",
                    "sourceView": "v_src",
                    "views": {
                        "v_src": {
                            "mode": "stream",
                            "sourceType": "delta",
                            "sourceDetails": {"database": "db", "table": "src"},
                        }
                    },
                },
            ),
            (FlowType.MATERIALIZED_VIEW, FlowMaterializedView, {"targetTable": "t"}),
        ]
        for entry in cases:
            flow_type, expected_cls = entry[0], entry[1]
            flow_details = entry[2] if len(entry) > 2 else base_details
            payload = {"flowType": flow_type, "flowDetails": flow_details}
            flow = FlowFactory.create("f_test", payload)
            assert isinstance(flow, expected_cls)
            assert flow.flowName == "f_test"

    def test_normalizes_flow_type_case(self, pipeline_context):
        flow = FlowFactory.create(
            "f_sql",
            {
                "flowType": "APPEND_SQL",
                "flowDetails": {"targetTable": "t", "sqlStatement": "SELECT 1"},
            },
        )
        assert isinstance(flow, FlowAppendSql)

    def test_raises_for_unsupported_flow_type(self, pipeline_context):
        with pytest.raises(ValueError, match='Unsupported flow type "unknown"'):
            FlowFactory.create("f_bad", {"flowType": "unknown", "flowDetails": {}})
