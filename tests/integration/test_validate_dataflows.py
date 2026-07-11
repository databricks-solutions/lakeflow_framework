"""
Integration tests for ``scripts/validate_dataflows.py`` against sample bundles.
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
)

pytestmark = pytest.mark.integration


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
