"""
Unit tests for ``scripts/validate_dataflows.py`` helper functions.

Pure logic only — no sample bundles or subprocess CLI invocation.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validate_dataflows.py"

_spec = importlib.util.spec_from_file_location("validate_dataflows", SCRIPT_PATH)
vd = importlib.util.module_from_spec(_spec)
sys.modules["validate_dataflows"] = vd
_spec.loader.exec_module(vd)

_SCHEMA_ROOT = Path("src") / "lakeflow_framework" / "schemas"


class TestDetectSpecForm:
    def test_template_form_when_both_keys_present(self):
        data = {"template": "my_template", "parameterSets": [{"dataFlowId": "x"}]}
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_TEMPLATE

    def test_expanded_form_when_dataflow_keys_present(self):
        data = {"dataFlowId": "x", "dataFlowGroup": "g", "dataFlowType": "flow"}
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_only_template_key(self):
        assert vd.detect_spec_form({"template": "t"}) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_only_parametersets_key(self):
        assert vd.detect_spec_form({"parameterSets": []}) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_empty(self):
        assert vd.detect_spec_form({}) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_not_a_dict(self):
        assert vd.detect_spec_form([]) == vd.SPEC_FORM_EXPANDED
        assert vd.detect_spec_form("not a dict") == vd.SPEC_FORM_EXPANDED
        assert vd.detect_spec_form(None) == vd.SPEC_FORM_EXPANDED


class TestGetSchemaPath:
    def test_template_form_returns_spec_template_schema(self, tmp_path):
        result = vd.get_schema_path(tmp_path, vd.SPEC_FORM_TEMPLATE)
        assert result == tmp_path / _SCHEMA_ROOT / "spec_template.json"

    def test_expanded_form_returns_main_schema(self, tmp_path):
        result = vd.get_schema_path(tmp_path, vd.SPEC_FORM_EXPANDED)
        assert result == tmp_path / _SCHEMA_ROOT / "main.json"

    def test_unknown_form_falls_back_to_main_schema(self, tmp_path):
        result = vd.get_schema_path(tmp_path, "some_other_form")
        assert result == tmp_path / _SCHEMA_ROOT / "main.json"


class TestFindDataflowFiles:
    def test_single_file_main_json_returns_itself(self, tmp_path):
        f = tmp_path / "customer_main.json"
        f.write_text("{}")
        assert vd.find_dataflow_files(f) == [f]

    def test_single_file_non_main_returns_empty(self, tmp_path):
        f = tmp_path / "customer.json"
        f.write_text("{}")
        assert vd.find_dataflow_files(f) == []

    def test_finds_files_in_dataflowspec_subdir_layout(self, tmp_path):
        spec_dir = tmp_path / "src" / "dataflows" / "base_samples" / "dataflowspec"
        spec_dir.mkdir(parents=True)
        f1 = spec_dir / "customer_main.json"
        f2 = spec_dir / "orders_main.json"
        f1.write_text("{}")
        f2.write_text("{}")
        result = vd.find_dataflow_files(tmp_path)
        assert sorted(result) == sorted([f1, f2])

    def test_finds_files_in_flat_dataflows_layout(self, tmp_path):
        df_dir = tmp_path / "src" / "dataflows"
        df_dir.mkdir(parents=True)
        f1 = df_dir / "raw_main.json"
        f2 = df_dir / "structured_main.json"
        f1.write_text("{}")
        f2.write_text("{}")
        result = vd.find_dataflow_files(tmp_path)
        assert sorted(result) == sorted([f1, f2])

    def test_finds_files_when_search_path_is_dataflows_dir_itself(self, tmp_path):
        df_dir = tmp_path / "dataflows"
        df_dir.mkdir()
        f = df_dir / "raw_main.json"
        f.write_text("{}")
        result = vd.find_dataflow_files(df_dir)
        assert result == [f]

    def test_skips_main_json_files_outside_dataflows_directories(self, tmp_path):
        df_dir = tmp_path / "src" / "dataflows"
        df_dir.mkdir(parents=True)
        in_dataflows = df_dir / "good_main.json"
        in_dataflows.write_text("{}")

        unrelated_dir = tmp_path / "src" / "lakeflow_framework" / "schemas"
        unrelated_dir.mkdir(parents=True)
        unrelated = unrelated_dir / "definitions_main.json"
        unrelated.write_text("{}")

        result = vd.find_dataflow_files(tmp_path)
        assert result == [in_dataflows]
        assert unrelated not in result
