"""Unit tests for DeltaJoin alias parsing."""

from __future__ import annotations

from lakeflow_framework.dataflow.sources.delta_join import DeltaJoin


class TestDeltaJoin:
    def test_get_table_aliases_extracts_unique_aliases_in_order(self):
        join = DeltaJoin(joinType="inner", condition="left_tbl.id = right_tbl.id AND left_tbl.x = 1")
        assert join.get_table_aliases() == ["left_tbl", "right_tbl"]

    def test_get_table_aliases_deduplicates_repeated_aliases(self):
        join = DeltaJoin(
            joinType="inner",
            condition="a.id = b.id AND a.updated = b.updated",
        )
        assert join.get_table_aliases() == ["a", "b"]

    def test_get_table_aliases_returns_empty_for_no_qualifiers(self):
        join = DeltaJoin(joinType="inner", condition="id = other_id")
        assert join.get_table_aliases() == []
