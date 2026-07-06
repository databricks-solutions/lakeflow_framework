"""Unit tests for quarantine table naming and mode selection (pure logic paths)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dataflow.enums import Mode, QuarantineMode, TableType, TargetType
from dataflow.quarantine import QuarantineManager
from dataflow.targets import TargetDeltaMaterializedView, TargetDeltaStreamingTable


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
        assert manager.quarantine_rules == "NOT(id IS NOT NULL)"

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
