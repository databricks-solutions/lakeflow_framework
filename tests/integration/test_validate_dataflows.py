"""
Integration tests for ``scripts/validate_dataflows.py`` helpers and sample specs.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from integration.conftest import (
    JSON_SAMPLE_BUNDLES,
    PROJECT_ROOT,
    SAMPLES_DIR,
    VALIDATE_SCRIPT_PATH,
    validate_bundle,
    vd,
)

pytestmark = pytest.mark.integration


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


@pytest.mark.skipif(not SAMPLES_DIR.is_dir(), reason="samples/ not present")
@pytest.mark.parametrize("bundle_name", JSON_SAMPLE_BUNDLES)
class TestValidateAllSpecsInBundle:
    """Validate every ``*_main.json`` under each sample bundle."""

    def test_all_main_json_specs_validate(self, bundle_name: str):
        bundle_path = SAMPLES_DIR / bundle_name
        passed, failed_count, failures = validate_bundle(bundle_path)

        assert passed > 0, f"No *_main.json files found under {bundle_name}"
        assert failed_count == 0, _format_failure_message(bundle_name, failures)


@pytest.mark.skipif(not SAMPLES_DIR.is_dir(), reason="samples/ not present")
@pytest.mark.parametrize("bundle_name", JSON_SAMPLE_BUNDLES)
class TestValidateDataflowsScriptPerBundle:
    """Invoke the CLI against each bundle path (not the full ``samples/`` tree)."""

    def test_script_exits_zero(self, bundle_name: str):
        result = subprocess.run(
            [sys.executable, str(VALIDATE_SCRIPT_PATH), f"samples/{bundle_name}/"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def _format_failure_message(bundle_name: str, failures: list) -> str:
    lines = [f"{bundle_name} validation failures:"]
    for path, errors in failures:
        rel = path.relative_to(SAMPLES_DIR / bundle_name)
        lines.append(f"  {rel}:")
        lines.extend(f"    - {msg}" for msg in errors)
    return "\n".join(lines)
