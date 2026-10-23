"""Unit tests for native AUTO CDC partial-update pass-through."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lakeflow_framework.dataflow import cdc as cdc_module
from lakeflow_framework.dataflow.cdc import CDCFlow, CDCSettings


class TestCDCSettingsValidation:
    def test_rejects_columns_to_update_with_ignore_null_updates(self):
        with pytest.raises(ValueError, match="cannot be combined"):
            CDCSettings(
                keys=["id"],
                sequence_by="ts",
                scd_type="2",
                columns_to_update="COLUMNS_TO_UPDATE",
                ignore_null_updates=True,
            )

    def test_rejects_columns_to_update_with_ignore_null_column_list(self):
        with pytest.raises(ValueError, match="cannot be combined"):
            CDCSettings(
                keys=["id"],
                sequence_by="ts",
                scd_type="1",
                columns_to_update="COLUMNS_TO_UPDATE",
                ignore_null_updates_column_list=["city"],
            )

    def test_rejects_both_ignore_null_list_variants(self):
        with pytest.raises(ValueError, match="not both"):
            CDCSettings(
                keys=["id"],
                sequence_by="ts",
                scd_type="1",
                ignore_null_updates_column_list=["city"],
                ignore_null_updates_except_column_list=["name"],
            )

    def test_empty_columns_to_update_is_none(self):
        settings = CDCSettings(
            keys=["id"],
            sequence_by="ts",
            scd_type="1",
            columns_to_update="  ",
        )
        assert settings.columns_to_update is None


def _settings(**overrides):
    values = dict(keys=["id"], sequence_by="ts", scd_type="2")
    values.update(overrides)
    return CDCSettings(**values)


def _patch_cdc_dp(monkeypatch, captured):
    monkeypatch.setattr(
        cdc_module,
        "dp",
        SimpleNamespace(create_auto_cdc_flow=lambda **kwargs: captured.update(kwargs)),
    )


class TestCDCFlowCreate:
    def test_passthrough_columns_to_update(self, pipeline_context, monkeypatch):
        captured = {}
        _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(_settings(columns_to_update="COLUMNS_TO_UPDATE")).create(
            target_table="tgt",
            source_view_name="v_src",
        )

        assert captured["columns_to_update"] == "COLUMNS_TO_UPDATE"
        assert captured["source"] == "v_src"
        assert captured["except_column_list"] == ["COLUMNS_TO_UPDATE"]
        assert "ignore_null_updates_column_list" not in captured

    def test_appends_columns_to_update_to_existing_except(self, pipeline_context, monkeypatch):
        captured = {}
        _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(
            _settings(
                except_column_list=["is_delete", "ts"],
                columns_to_update="COLUMNS_TO_UPDATE",
            )
        ).create(target_table="tgt", source_view_name="v_src")

        assert captured["except_column_list"] == [
            "is_delete",
            "ts",
            "COLUMNS_TO_UPDATE",
        ]

    def test_passthrough_ignore_null_updates_column_list(self, pipeline_context, monkeypatch):
        captured = {}
        _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(_settings(scd_type="1", ignore_null_updates_column_list=["city"])).create(
            target_table="tgt",
            source_view_name="v_src",
        )

        assert captured["ignore_null_updates_column_list"] == ["city"]
        assert "columns_to_update" not in captured

    def test_passthrough_ignore_null_updates_except_column_list(
        self, pipeline_context, monkeypatch
    ):
        captured = {}
        _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(
            _settings(scd_type="1", ignore_null_updates_except_column_list=["name"])
        ).create(target_table="tgt", source_view_name="v_src")

        assert captured["ignore_null_updates_except_column_list"] == ["name"]
        assert "columns_to_update" not in captured

    def test_omits_newer_kwargs_when_unset(self, pipeline_context, monkeypatch):
        captured = {}
        _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(_settings()).create(target_table="tgt", source_view_name="v_src")

        assert "columns_to_update" not in captured
        assert "ignore_null_updates_column_list" not in captured
        assert "ignore_null_updates_except_column_list" not in captured
