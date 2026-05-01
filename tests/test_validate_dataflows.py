"""
Tests for ``scripts/validate_dataflows.py``.

Cover the form-detection / schema-routing / file-discovery improvements that
let the validator handle both expanded-form (``main.json``) and
template+parameterSets-form (``spec_template.json``) ``*_main.json`` files.
"""

import json
import sys
import importlib.util
from pathlib import Path

import pytest


# Load scripts/validate_dataflows.py as a module (it's not on pythonpath
# because it lives in scripts/, not src/, and is invoked as a script).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validate_dataflows.py"
SAMPLES_DIR = PROJECT_ROOT / "samples"

_spec = importlib.util.spec_from_file_location("validate_dataflows", SCRIPT_PATH)
vd = importlib.util.module_from_spec(_spec)
sys.modules["validate_dataflows"] = vd
_spec.loader.exec_module(vd)


# -----------------------------------------------------------------------------
# detect_spec_form
# -----------------------------------------------------------------------------

class TestDetectSpecForm:
    def test_template_form_when_both_keys_present(self):
        data = {"template": "my_template", "parameterSets": [{"dataFlowId": "x"}]}
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_TEMPLATE

    def test_expanded_form_when_dataflow_keys_present(self):
        data = {"dataFlowId": "x", "dataFlowGroup": "g", "dataFlowType": "flow"}
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_only_template_key(self):
        # `template` alone (no parameterSets) is not the documented template form
        assert vd.detect_spec_form({"template": "t"}) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_only_parametersets_key(self):
        # `parameterSets` alone is not the documented template form
        assert vd.detect_spec_form({"parameterSets": []}) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_empty(self):
        assert vd.detect_spec_form({}) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_not_a_dict(self):
        # Defensive: should not crash on lists / strings / None
        assert vd.detect_spec_form([]) == vd.SPEC_FORM_EXPANDED
        assert vd.detect_spec_form("not a dict") == vd.SPEC_FORM_EXPANDED
        assert vd.detect_spec_form(None) == vd.SPEC_FORM_EXPANDED


# -----------------------------------------------------------------------------
# get_schema_path
# -----------------------------------------------------------------------------

class TestGetSchemaPath:
    def test_template_form_returns_spec_template_schema(self, tmp_path):
        result = vd.get_schema_path(tmp_path, vd.SPEC_FORM_TEMPLATE)
        assert result == tmp_path / "src" / "schemas" / "spec_template.json"

    def test_expanded_form_returns_main_schema(self, tmp_path):
        result = vd.get_schema_path(tmp_path, vd.SPEC_FORM_EXPANDED)
        assert result == tmp_path / "src" / "schemas" / "main.json"

    def test_unknown_form_falls_back_to_main_schema(self, tmp_path):
        # Defensive: unknown form string should not crash; defaults to main.json
        result = vd.get_schema_path(tmp_path, "some_other_form")
        assert result == tmp_path / "src" / "schemas" / "main.json"


# -----------------------------------------------------------------------------
# find_dataflow_files
# -----------------------------------------------------------------------------

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
        """Upstream sample layout: project/src/dataflows/<sample>/dataflowspec/*_main.json"""
        spec_dir = tmp_path / "src" / "dataflows" / "base_samples" / "dataflowspec"
        spec_dir.mkdir(parents=True)
        f1 = spec_dir / "customer_main.json"
        f2 = spec_dir / "orders_main.json"
        f1.write_text("{}")
        f2.write_text("{}")
        result = vd.find_dataflow_files(tmp_path)
        assert sorted(result) == sorted([f1, f2])

    def test_finds_files_in_flat_dataflows_layout(self, tmp_path):
        """Consumer-bundle layout: dataflows/*_main.json (no dataflowspec/ subdir)"""
        df_dir = tmp_path / "src" / "dataflows"
        df_dir.mkdir(parents=True)
        f1 = df_dir / "raw_main.json"
        f2 = df_dir / "structured_main.json"
        f1.write_text("{}")
        f2.write_text("{}")
        result = vd.find_dataflow_files(tmp_path)
        assert sorted(result) == sorted([f1, f2])

    def test_finds_files_when_search_path_is_dataflows_dir_itself(self, tmp_path):
        """User points the validator directly at a dataflows/ dir."""
        df_dir = tmp_path / "dataflows"
        df_dir.mkdir()
        f = df_dir / "raw_main.json"
        f.write_text("{}")
        result = vd.find_dataflow_files(df_dir)
        assert result == [f]

    def test_skips_main_json_files_outside_dataflows_directories(self, tmp_path):
        """Random *_main.json files unrelated to dataflows must NOT be picked up."""
        df_dir = tmp_path / "src" / "dataflows"
        df_dir.mkdir(parents=True)
        in_dataflows = df_dir / "good_main.json"
        in_dataflows.write_text("{}")

        # Unrelated _main.json file outside any dataflows dir
        unrelated_dir = tmp_path / "src" / "schemas"
        unrelated_dir.mkdir(parents=True)
        unrelated = unrelated_dir / "definitions_main.json"
        unrelated.write_text("{}")

        result = vd.find_dataflow_files(tmp_path)
        assert result == [in_dataflows]
        assert unrelated not in result


# -----------------------------------------------------------------------------
# End-to-end against existing upstream sample fixtures
# -----------------------------------------------------------------------------

@pytest.mark.skipif(
    not (SAMPLES_DIR / "bronze_sample").exists(),
    reason="upstream samples not present in this checkout",
)
class TestEndToEndAgainstSamples:
    """
    Validate against fixtures that already exist in upstream `samples/`.
    These exercise the full validator path (form detection -> schema routing
    -> jsonschema validation) without us having to ship our own JSON fixtures.
    """

    def test_template_form_sample_validates_with_template_schema(self):
        """
        ``template_samples_main.json`` has top-level ``template`` + ``parameterSets``.
        Before this change it failed validation against ``main.json`` schema with
        14 errors (``parameterSets`` / ``template`` were unexpected); after the
        fix it routes to ``spec_template.json`` and passes.
        """
        path = (
            SAMPLES_DIR / "bronze_sample" / "src" / "dataflows"
            / "template_samples" / "dataflowspec" / "template_samples_main.json"
        )
        with open(path) as f:
            data = json.load(f)
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_TEMPLATE

        is_valid, errors, _ = vd.validate_file(
            path,
            vd.get_schema_path(PROJECT_ROOT, vd.SPEC_FORM_TEMPLATE),
            apply_mapping=False,
        )
        assert is_valid, f"template_samples_main.json should validate: {errors}"

    def test_expanded_form_sample_validates_with_main_schema(self):
        """
        Pick any expanded-form sample. ``customer_address_main.json`` has
        top-level ``dataFlowId`` etc. so it should still route to ``main.json``.
        """
        path = (
            SAMPLES_DIR / "silver_sample" / "src" / "dataflows" / "base_samples"
            / "dataflowspec" / "customer_address_main.json"
        )
        with open(path) as f:
            data = json.load(f)
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_EXPANDED

        is_valid, errors, _ = vd.validate_file(
            path,
            vd.get_schema_path(PROJECT_ROOT, vd.SPEC_FORM_EXPANDED),
            apply_mapping=True,
            project_root=PROJECT_ROOT,
        )
        assert is_valid, f"customer_address_main.json should validate: {errors}"

    def test_find_dataflow_files_picks_up_template_sample(self):
        """The relaxed file-discovery still finds the template-form sample."""
        files = vd.find_dataflow_files(SAMPLES_DIR / "bronze_sample")
        names = {f.name for f in files}
        assert "template_samples_main.json" in names
