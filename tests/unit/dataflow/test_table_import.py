"""Unit tests for dataflow/table_import.py - CDC settings assembly."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lakeflow_framework.constants import SystemColumns
from lakeflow_framework.dataflow import table_import
from lakeflow_framework.dataflow.cdc import CDCSettings


class _FakeCDCFlow:
    """Capture the CDCSettings handed to CDCFlow instead of registering a flow."""

    captured: list = []

    def __init__(self, settings):
        self.settings = settings
        _FakeCDCFlow.captured.append(settings)

    def create(self, **kwargs):
        return None


@pytest.fixture
def patched_table_import(monkeypatch):
    _FakeCDCFlow.captured.clear()
    monkeypatch.setattr(table_import.pipeline_config, "get_spark", lambda: SimpleNamespace())
    monkeypatch.setattr(table_import.pipeline_config, "get_logger", lambda: SimpleNamespace(
        info=lambda *a, **k: None, debug=lambda *a, **k: None
    ))
    monkeypatch.setattr(
        table_import.SourceFactory, "create",
        staticmethod(lambda _type, details: SimpleNamespace(table=details["table"])),
    )
    monkeypatch.setattr(table_import.View, "create_view", lambda self, **kwargs: None)
    monkeypatch.setattr(table_import, "dp", SimpleNamespace(
        view=lambda **kwargs: (lambda fn: fn),
        append_flow=lambda **kwargs: (lambda fn: fn),
    ))
    monkeypatch.setattr(table_import, "CDCFlow", _FakeCDCFlow)
    return _FakeCDCFlow


def _run(cdc_settings):
    table_import.create_table_import_flow(
        source_details={"table": "src_tbl", "database": "db"},
        target_table_name="tgt",
        cdc_settings=cdc_settings,
    )


class TestSCD2ExceptColumnList:
    def test_spec_except_columns_are_unioned_with_internal_columns(self, patched_table_import):
        # Regression for #137: previously list.extend() (returns None) was fed to
        # list(set(...)) and raised TypeError whenever except_column_list was set.
        _run(CDCSettings(scd_type="2", keys=["id"], sequence_by="ts",
                         except_column_list=["op", "is_deleted"]))

        settings = patched_table_import.captured[0]
        scd2_columns = [c.value for c in SystemColumns.SCD2Columns]
        expected = ["op", "is_deleted", "WATERMARK_COLUMN", *scd2_columns]
        assert settings.except_column_list == expected  # order preserved, no duplicates
        assert len(settings.except_column_list) == len(set(settings.except_column_list))

    def test_default_except_columns_when_spec_omits_them(self, patched_table_import):
        _run(CDCSettings(scd_type="2", keys=["id"], sequence_by="ts"))

        settings = patched_table_import.captured[0]
        scd2_columns = [c.value for c in SystemColumns.SCD2Columns]
        assert settings.except_column_list == ["is_deleted", *scd2_columns]
