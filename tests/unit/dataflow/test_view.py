"""Unit tests for View properties and reader option helpers."""

from __future__ import annotations

import pytest

from dataflow.enums import SourceType
from dataflow.sources import SourceDelta
from dataflow.view import View


class TestView:
    def test_is_cdf_enabled_false_for_non_delta(self, pipeline_context):
        view = View(
            viewName="v_sql",
            mode="stream",
            sourceType=SourceType.SQL,
            sourceDetails={"sqlStatement": "SELECT 1"},
        )
        assert view.isCdfEnabled is False

    def test_is_cdf_enabled_true_when_flag_set(self, pipeline_context):
        view = View(
            viewName="v_delta",
            mode="stream",
            sourceType=SourceType.DELTA,
            sourceDetails={"database": "db", "table": "t", "cdfEnabled": True},
        )
        assert view.isCdfEnabled is True

    def test_is_cdf_enabled_defaults_false(self, pipeline_context):
        view = View(
            viewName="v_delta",
            mode="stream",
            sourceType=SourceType.DELTA,
            sourceDetails={"database": "db", "table": "t"},
        )
        assert view.isCdfEnabled is False

    def test_normalizes_mode_and_source_type(self, pipeline_context):
        view = View(
            viewName="v_delta",
            mode="STREAM",
            sourceType="DELTA",
            sourceDetails={"database": "db", "table": "t"},
        )
        assert view.mode == "stream"
        assert view.sourceType == SourceType.DELTA

    def test_add_reader_options_creates_dict_when_missing(self, pipeline_context):
        view = View(
            viewName="v_delta",
            mode="stream",
            sourceType=SourceType.DELTA,
            sourceDetails={"database": "db", "table": "t"},
        )
        view.add_reader_options({"startingVersion": "0"})
        assert view.sourceDetails["readerOptions"] == {"startingVersion": "0"}

    def test_add_reader_options_merges_existing(self, pipeline_context):
        view = View(
            viewName="v_delta",
            mode="stream",
            sourceType=SourceType.DELTA,
            sourceDetails={
                "database": "db",
                "table": "t",
                "readerOptions": {"startingVersion": "0"},
            },
        )
        view.add_reader_options({"maxBytesPerTrigger": "1g"})
        assert view.sourceDetails["readerOptions"] == {
            "startingVersion": "0",
            "maxBytesPerTrigger": "1g",
        }

    def test_get_source_details_returns_source_instance(self, pipeline_context):
        view = View(
            viewName="v_delta",
            mode="stream",
            sourceType=SourceType.DELTA,
            sourceDetails={"database": "db", "table": "t"},
        )
        source = view.get_source_details()
        assert isinstance(source, SourceDelta)
        assert source.database == "db"
        assert source.table == "t"
