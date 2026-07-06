"""Unit tests for FlowGroup staging table and flow resolution."""

from __future__ import annotations

import pytest

from dataflow.flow_group import FlowGroup
from dataflow.flows.append_sql import FlowAppendSql
from dataflow.targets.staging_table import StagingTable


class _DuplicateKeyDict(dict):
    """Dict that yields the same key twice (simulates invalid duplicate names)."""

    def __init__(self, key, value):
        super().__init__({key: value})
        self._key = key
        self._value = value

    def items(self):
        yield self._key, self._value
        yield self._key, self._value


class TestFlowGroupGetFlows:
    def test_returns_flow_instances(self, pipeline_context):
        group = FlowGroup(
            flowGroupId="main",
            flows={
                "f_append": {
                    "flowType": "append_sql",
                    "flowDetails": {
                        "targetTable": "tgt",
                        "sqlStatement": "SELECT 1",
                    },
                }
            },
        )
        flows = group.get_flows()
        assert "f_append" in flows
        assert isinstance(flows["f_append"], FlowAppendSql)

    def test_raises_for_duplicate_flow_names(self, pipeline_context):
        flow_payload = {
            "flowType": "append_sql",
            "flowDetails": {"targetTable": "tgt", "sqlStatement": "SELECT 1"},
        }
        group = FlowGroup(flowGroupId="main", flows={})
        group.flows = _DuplicateKeyDict("f_dup", flow_payload)
        with pytest.raises(ValueError, match="Multiple flows found"):
            group.get_flows()


class TestFlowGroupGetStagingTables:
    def test_builds_staging_table_without_database(self, pipeline_context):
        group = FlowGroup(
            flowGroupId="main",
            flows={},
            stagingTables={"stg_orders": {"type": "st"}},
        )
        tables = group.get_staging_tables()
        assert "stg_orders" in tables
        assert isinstance(tables["stg_orders"], StagingTable)
        assert tables["stg_orders"].table == "stg_orders"

    def test_qualifies_staging_table_key_with_database(self, pipeline_context):
        group = FlowGroup(
            flowGroupId="main",
            flows={},
            stagingTables={
                "stg_orders": {
                    "type": "st",
                    "database": "silver_db",
                }
            },
        )
        tables = group.get_staging_tables()
        assert "silver_db.stg_orders" in tables
        assert tables["silver_db.stg_orders"].table == "silver_db.stg_orders"

    def test_raises_for_duplicate_staging_table_names(self, pipeline_context):
        group = FlowGroup(flowGroupId="main", flows={}, stagingTables={})
        group.stagingTables = _DuplicateKeyDict(
            "orders", {"database": "db", "type": "st"}
        )
        with pytest.raises(ValueError, match="Multiple staging tables found"):
            group.get_staging_tables()


class TestBaseFlowWithViews:
    def test_get_views_returns_view_objects(self, pipeline_context):
        from dataflow.flows.append_view import FlowAppendView

        flow = FlowAppendView(
            flowName="f1",
            flowType="append_view",
            flowDetails={"targetTable": "t", "sourceView": "v_src"},
            views={
                "v_src": {
                    "mode": "stream",
                    "sourceType": "delta",
                    "sourceDetails": {"database": "db", "table": "src"},
                }
            },
        )
        views = flow.get_views()
        assert list(views) == ["v_src"]
        assert views["v_src"].viewName == "v_src"
