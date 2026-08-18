"""Unit tests for quarantine table naming and mode selection (pure logic paths)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import lakeflow_framework.dataflow.quarantine as quarantine_module
from lakeflow_framework.dataflow.enums import Mode, QuarantineMode, TableType, TargetType
from lakeflow_framework.dataflow.quarantine import QuarantineManager
from lakeflow_framework.dataflow.targets import TargetDeltaMaterializedView, TargetDeltaStreamingTable

# Captured before any test patches the class, so the ANSI filter tests can call the real method.
_REAL_CREATE_VIEW_MV = QuarantineManager._create_quarantine_view_mv


def _streaming_target(table: str) -> TargetDeltaStreamingTable:
    return TargetDeltaStreamingTable(table=table, type=TableType.STREAMING.value)


def _materialized_view_target(table: str, source_view: str = "v_target") -> TargetDeltaMaterializedView:
    return TargetDeltaMaterializedView(
        table=table,
        type=TableType.MATERIALIZED_VIEW.value,
        sourceView=source_view,
    )


def _build_quarantine_manager(monkeypatch, pipeline_context, **kwargs):
    captured = {"table_details": None, "view_mv_calls": []}

    def fake_create_table(self, quarantine_details):
        captured["table_details"] = quarantine_details
        self.quarantine_table = MagicMock()
        self.quarantine_table.table = quarantine_details["table"]
        self.quarantine_table.partitionColumns = quarantine_details.get("partitionColumns")
        self.quarantine_table.clusterByColumns = quarantine_details.get("clusterByColumns")
        self.quarantine_table.clusterByAuto = quarantine_details.get("clusterByAuto")

    def fake_create_view_mv(self, quarantine_view_name, target_details):
        captured["view_mv_calls"].append((quarantine_view_name, target_details))

    monkeypatch.setattr(QuarantineManager, "_create_quarantine_table", fake_create_table)
    monkeypatch.setattr(QuarantineManager, "_create_quarantine_view_mv", fake_create_view_mv)

    params = {
        "quarantine_mode": QuarantineMode.TABLE,
        "data_quality_rules": {"valid_id": "id IS NOT NULL"},
        "target_format": TargetType.DELTA,
        "target_details": _streaming_target("catalog.schema.orders"),
        "quarantine_target_details": {},
    }
    params.update(kwargs)
    manager = QuarantineManager(**params)
    return manager, captured


class TestQuarantineLogic:
    def test_builds_not_and_expression_from_data_quality_rules(
        self, pipeline_context, monkeypatch
    ):
        manager, _ = _build_quarantine_manager(monkeypatch, pipeline_context)
        assert manager.quarantine_rules == "NOT((id IS NOT NULL))"

    def test_parenthesises_each_rule_when_combining(
        self, pipeline_context, monkeypatch
    ):
        """A rule containing OR must not change the combined predicate (#134)."""
        manager, _ = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            data_quality_rules={
                "present": "a IS NULL OR b > 0",
                "positive": "c > 0",
            },
        )
        assert manager.quarantine_rules == "NOT((a IS NULL OR b > 0) AND (c > 0))"

    def test_missing_quarantine_target_details_falls_back_to_target_name(
        self, pipeline_context, monkeypatch
    ):
        """quarantineMode: table without quarantineTargetDetails must not raise (#134)."""
        _, captured = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_streaming_target("catalog.schema.orders"),
            quarantine_target_details=None,
        )
        assert captured["table_details"]["table"] == "catalog.schema.orders_quarantine"
        assert captured["table_details"]["database"] is None

    def test_stream_mode_uses_streaming_quarantine_table_type(
        self, pipeline_context, monkeypatch
    ):
        _, captured = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_streaming_target("catalog.schema.orders"),
        )
        assert captured["table_details"]["type"] == TableType.STREAMING.value
        assert captured["view_mv_calls"] == []

    def test_batch_mode_creates_materialized_view_quarantine_path(
        self, pipeline_context, monkeypatch
    ):
        manager, captured = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_materialized_view_target("catalog.schema.orders"),
        )
        assert manager.mode == Mode.BATCH
        assert captured["table_details"]["type"] == TableType.MATERIALIZED_VIEW.value
        assert captured["table_details"]["sourceView"] == "v_catalog.schema.orders_quarantine"
        assert captured["view_mv_calls"][0][0] == "v_catalog.schema.orders_quarantine"

    def test_derives_quarantine_table_from_qualified_target_when_no_database(
        self, pipeline_context, monkeypatch
    ):
        _, captured = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_streaming_target("catalog.schema.orders"),
            quarantine_target_details={},
        )
        assert captured["table_details"]["table"] == "catalog.schema.orders_quarantine"
        assert captured["table_details"]["database"] is None

    def test_derives_unqualified_quarantine_name_when_database_supplied(
        self, pipeline_context, monkeypatch
    ):
        _, captured = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_streaming_target("catalog.schema.orders"),
            quarantine_target_details={"database": "quarantine_db"},
        )
        assert captured["table_details"]["table"] == "orders_quarantine"
        assert captured["table_details"]["database"] == "quarantine_db"

    def test_honors_explicit_quarantine_table_and_clears_database(
        self, pipeline_context, monkeypatch
    ):
        _, captured = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            quarantine_target_details={
                "database": "quarantine_db",
                "table": "custom_quarantine",
            },
        )
        assert captured["table_details"]["table"] == "custom_quarantine"
        assert captured["table_details"]["database"] is None

    def test_flag_mode_adds_quarantine_column_when_schema_present(
        self, pipeline_context, monkeypatch
    ):
        monkeypatch.setattr(QuarantineManager, "_create_quarantine_table", lambda self, _: None)
        monkeypatch.setattr(QuarantineManager, "_create_quarantine_view_mv", lambda *args, **kwargs: None)
        target = MagicMock()
        target.schema = {"fields": []}
        target.add_columns.return_value = target
        manager = QuarantineManager(
            quarantine_mode=QuarantineMode.FLAG,
            data_quality_rules={"valid_id": "id IS NOT NULL"},
            target_format=TargetType.DELTA,
            target_details=target,
        )
        result = manager.add_quarantine_columns_delta(target)
        target.add_columns.assert_called_once()
        assert result is target

    def test_create_quarantine_flow_rejects_batch_mode(
        self, pipeline_context, monkeypatch
    ):
        manager, _ = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_materialized_view_target("catalog.schema.orders"),
        )
        with pytest.raises(ValueError, match="Cannot create quarantine flow for batch mode"):
            manager.create_quarantine_flow("v_orders")


class _RecordingDataFrame:
    """DataFrame stand-in that records the arguments it is filtered with."""

    def __init__(self, recorder: dict, columns: list[str] | None = None):
        self._recorder = recorder
        self.columns = columns if columns is not None else ["id", "_quarantine_flag"]

    def withColumn(self, name, expression):
        self._recorder["with_column"] = (name, expression)
        return self

    def where(self, condition):
        self._recorder["where"] = condition
        return self

    def drop(self, *columns):
        self._recorder["drop"] = columns
        return self


class TestQuarantineFilterIsAnsiSafe:
    """The quarantine flag is boolean, so it must not be compared to 1 (#134)."""

    def test_materialized_view_filters_on_boolean_column(
        self, pipeline_context, monkeypatch
    ):
        recorder: dict = {}
        captured_views: dict = {}

        def fake_view(function, name=None, comment=None):
            captured_views[name] = function

        manager, _ = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_materialized_view_target("catalog.schema.orders"),
        )
        # raising=False: the installed pyspark exposes temporary_view, not view.
        monkeypatch.setattr(quarantine_module.dp, "view", fake_view, raising=False)
        manager.spark = MagicMock()
        manager.spark.read.table.return_value = _RecordingDataFrame(recorder)

        # The builder helper stubs out view creation, so invoke the real implementation.
        _REAL_CREATE_VIEW_MV(manager, "v_q", manager.target_details)
        captured_views["v_q"]()

        condition = recorder["where"]
        assert not isinstance(condition, str)
        assert "= 1" not in str(condition)

    def test_append_flow_filters_on_boolean_column(
        self, pipeline_context, monkeypatch
    ):
        recorder: dict = {}
        captured_flows: dict = {}

        def fake_append_flow(name=None, target=None):
            def decorator(function):
                captured_flows[name] = function
                return function
            return decorator

        manager, _ = _build_quarantine_manager(
            monkeypatch,
            pipeline_context,
            target_details=_streaming_target("catalog.schema.orders"),
        )
        monkeypatch.setattr(quarantine_module.dp, "append_flow", fake_append_flow)
        manager.spark = MagicMock()
        manager.spark.readStream.table.return_value = _RecordingDataFrame(recorder)

        manager._create_quarantine_flow("v_q", "catalog.schema.orders_quarantine")
        captured_flows["f_quarantine_v_q"]()

        condition = recorder["where"]
        assert not isinstance(condition, str)
        assert "= 1" not in str(condition)
