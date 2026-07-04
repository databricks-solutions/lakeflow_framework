"""
Integration tests for ``scripts/validate_dataflows.py``.
"""
import json
import sys
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validate_dataflows.py"
SAMPLES_DIR = PROJECT_ROOT / "samples"

_spec = importlib.util.spec_from_file_location("validate_dataflows", SCRIPT_PATH)
vd = importlib.util.module_from_spec(_spec)
sys.modules["validate_dataflows"] = vd
_spec.loader.exec_module(vd)


class TestDetectSpecForm:
    def test_template_form_when_both_keys_present(self):
        data = {"template": "my_template", "parameterSets": [{"dataFlowId": "x"}]}
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_TEMPLATE

    def test_expanded_form_when_dataflow_keys_present(self):
        data = {"dataFlowId": "x", "dataFlowGroup": "g", "dataFlowType": "flow"}
        assert vd.detect_spec_form(data) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_only_template_key(self):
        assert vd.detect_spec_form({"template": "t"}) == vd.SPEC_FORM_EXPANDED

    def test_expanded_form_when_empty(self):
        assert vd.detect_spec_form({}) == vd.SPEC_FORM_EXPANDED


class TestGetSchemaPath:
    def test_template_form_returns_spec_template_schema(self, tmp_path):
        result = vd.get_schema_path(tmp_path, vd.SPEC_FORM_TEMPLATE)
        assert result == tmp_path / "src" / "schemas" / "spec_template.json"


class TestFindDataflowFiles:
    def test_single_file_main_json_returns_itself(self, tmp_path):
        f = tmp_path / "customer_main.json"
        f.write_text("{}")
        assert vd.find_dataflow_files(f) == [f]

    def test_finds_files_in_dataflowspec_subdir_layout(self, tmp_path):
        spec_dir = tmp_path / "src" / "dataflows" / "base_samples" / "dataflowspec"
        spec_dir.mkdir(parents=True)
        f1 = spec_dir / "customer_main.json"
        f1.write_text("{}")
        result = vd.find_dataflow_files(tmp_path)
        assert result == [f1]


@pytest.mark.skipif(
    not (SAMPLES_DIR / "bronze_sample").exists(),
    reason="upstream samples not present in this checkout",
)
class TestEndToEndAgainstSamples:
    def test_template_form_sample_validates_with_template_schema(self):
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
