"""Unit tests for AUTO CDC columns_to_update pass-through and lineage-except."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lakeflow_framework.constants import SystemColumns

COLUMNS_TO_UPDATE_COLUMN = SystemColumns.CDCColumns.COLUMNS_TO_UPDATE.value
from lakeflow_framework.dataflow import cdc as cdc_module
from lakeflow_framework.dataflow.cdc import CDCFlow, CDCSettings
from lakeflow_framework.dataflow.cdc_columns_to_update import (
    change_type_column,
    columns_to_update_for_event,
    commit_version_column,
    has_cdf_preimage_columns,
    payload_columns,
)

class TestPayloadColumns:
    def test_excludes_keys_lineage_and_system_columns(self):
        columns = [
            "id",
            "name",
            "city",
            "meta_file_metadata",
            "Load_Datetime",
            "_change_type",
            "_commit_version",
            "_commit_timestamp",
            "__START_AT",
            "is_delete",
        ]
        assert payload_columns(
            columns,
            keys=["id"],
            lineage_cols=["meta_file_metadata"],
            extra_ignore=["Load_Datetime"],
        ) == ["name", "city"]

    def test_lineage_only_frame_has_empty_payload(self):
        assert payload_columns(
            ["id", "meta_file_metadata", "_change_type"],
            keys=["id"],
            lineage_cols=["meta_file_metadata"],
        ) == []


class TestCdfHelpers:
    def test_prefers_framework_change_type_column(self):
        assert change_type_column(["id", "_change_type", "meta_cdc_change_type"]) == "_change_type"

    def test_accepts_workday_change_type_alias(self):
        assert change_type_column(["id", "meta_cdc_change_type"]) == "meta_cdc_change_type"

    def test_has_cdf_preimage_columns_requires_version(self):
        assert has_cdf_preimage_columns(["_change_type", "_commit_version"]) is True
        assert has_cdf_preimage_columns(["meta_cdc_change_type", "meta_cdc_commit_version"]) is True
        assert has_cdf_preimage_columns(["_change_type"]) is False

    def test_commit_version_column_accepts_alias(self):
        assert commit_version_column(["_commit_version"]) == "_commit_version"
        assert commit_version_column(["meta_cdc_commit_version"]) == "meta_cdc_commit_version"


class TestColumnsToUpdateForEvent:
    def test_insert_writes_payload_and_lineage(self):
        assert columns_to_update_for_event(
            is_insert=True,
            is_delete=False,
            payload_changed=False,
            payload_cols=["name", "city"],
            lineage_cols=["meta_file_metadata"],
        ) == ["name", "city", "meta_file_metadata"]

    def test_payload_change_includes_lineage(self):
        assert columns_to_update_for_event(
            is_insert=False,
            is_delete=False,
            payload_changed=True,
            payload_cols=["name"],
            lineage_cols=["meta_file_metadata"],
        ) == ["name", "meta_file_metadata"]

    def test_metadata_only_update_writes_nothing(self):
        assert columns_to_update_for_event(
            is_insert=False,
            is_delete=False,
            payload_changed=False,
            payload_cols=["name"],
            lineage_cols=["meta_file_metadata"],
        ) == []

    def test_delete_writes_payload_and_lineage(self):
        assert columns_to_update_for_event(
            is_insert=False,
            is_delete=True,
            payload_changed=False,
            payload_cols=["name"],
            lineage_cols=["meta_file_metadata"],
        ) == ["name", "meta_file_metadata"]


class TestCDCSettingsValidation:
    def test_rejects_columns_to_update_with_ignore_null_updates(self):
        with pytest.raises(ValueError, match="cannot be combined"):
            CDCSettings(
                keys=["id"],
                sequence_by="ts",
                scd_type="2",
                columns_to_update="__columns_to_update",
                ignore_null_updates=True,
            )

    def test_rejects_except_list_with_ignore_null_column_list(self):
        with pytest.raises(ValueError, match="cannot be combined"):
            CDCSettings(
                keys=["id"],
                sequence_by="ts",
                scd_type="1",
                columns_to_update_except_column_list=["meta_file_metadata"],
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
            columns_to_update_except_column_list=[],
        )
        assert settings.columns_to_update is None
        assert settings.columns_to_update_except_column_list == []


def _settings(**overrides):
    values = dict(keys=["id"], sequence_by="ts", scd_type="2")
    values.update(overrides)
    return CDCSettings(**values)


def _patch_cdc_dp(monkeypatch, captured, views=None):
    views = views if views is not None else []
    monkeypatch.setattr(
        cdc_module,
        "dp",
        SimpleNamespace(
            create_auto_cdc_flow=lambda **kwargs: captured.update(kwargs),
            view=lambda **kwargs: views.append(kwargs) or (lambda fn: fn),
        ),
    )
    return views


class TestCDCFlowCreate:
    def test_passthrough_columns_to_update(self, pipeline_context, monkeypatch):
        captured = {}
        _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(_settings(columns_to_update="my_update_cols")).create(
            target_table="tgt",
            source_view_name="v_src",
        )

        assert captured["columns_to_update"] == "my_update_cols"
        assert captured["source"] == "v_src"
        assert captured["except_column_list"] == ["my_update_cols"]
        assert "ignore_null_updates_column_list" not in captured

    def test_except_list_wraps_source_and_excludes_generated_column(
        self, pipeline_context, monkeypatch
    ):
        captured = {}
        views = _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(
            _settings(columns_to_update_except_column_list=["meta_file_metadata"])
        ).create(target_table="tgt", source_view_name="v_src")

        assert views == [{"name": "v_src__columns_to_update"}]
        assert captured["source"] == "v_src__columns_to_update"
        assert captured["columns_to_update"] == COLUMNS_TO_UPDATE_COLUMN
        assert captured["except_column_list"] == [COLUMNS_TO_UPDATE_COLUMN]

    def test_except_list_appends_generated_column_to_existing_except(
        self, pipeline_context, monkeypatch
    ):
        captured = {}
        _patch_cdc_dp(monkeypatch, captured)

        CDCFlow(
            _settings(
                except_column_list=["is_delete", "ts"],
                columns_to_update_except_column_list=["meta_file_metadata"],
            )
        ).create(target_table="tgt", source_view_name="v_src")

        assert captured["except_column_list"] == [
            "is_delete",
            "ts",
            COLUMNS_TO_UPDATE_COLUMN,
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
