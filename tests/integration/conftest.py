"""Shared fixtures and helpers for integration tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
VALIDATE_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validate_dataflows.py"

# Top-level sample bundles that ship JSON *_main.json specs (yaml_sample uses YAML only).
JSON_SAMPLE_BUNDLES = (
    "feature-samples",
    "pattern-samples",
    "tpch_sample",
)


def load_validate_dataflows_module():
    """Import ``scripts/validate_dataflows`` as a module."""
    spec = importlib.util.spec_from_file_location("validate_dataflows", VALIDATE_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_dataflows"] = module
    spec.loader.exec_module(module)
    return module


vd = load_validate_dataflows_module()


def validate_bundle(
    bundle_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    apply_mapping: bool = True,
) -> Tuple[int, int, List[Tuple[Path, List[str]]]]:
    """
    Validate all ``*_main.json`` specs under a sample bundle.

    Returns:
        (passed_count, failed_count, [(file_path, error_messages), ...])
    """
    files = vd.find_dataflow_files(bundle_path)
    passed = 0
    failures: List[Tuple[Path, List[str]]] = []

    for file_path in sorted(files):
        try:
            with open(file_path, encoding="utf-8") as handle:
                spec_form = vd.detect_spec_form(json.load(handle))
        except Exception:
            spec_form = vd.SPEC_FORM_EXPANDED

        schema_path = vd.get_schema_path(project_root, spec_form)
        is_valid, error_messages, _ = vd.validate_file(
            file_path,
            schema_path,
            apply_mapping=apply_mapping,
            project_root=project_root,
        )
        if is_valid:
            passed += 1
        else:
            failures.append((file_path, error_messages))

    return passed, len(failures), failures


@pytest.fixture
def feature_samples_bundle_path() -> Path:
    """Pipeline bundle root for feature samples (``src/`` tree)."""
    path = SAMPLES_DIR / "feature-samples" / "src"
    if not path.is_dir():
        pytest.skip("feature-samples bundle not present in checkout")
    return path


@pytest.fixture
def feature_samples_secrets_manager(feature_samples_bundle_path, framework_src_path, pipeline_context):
    """SecretsManager wired to feature-samples pipeline config."""
    from secrets_manager import SecretsManager

    bundle = feature_samples_bundle_path
    framework = framework_src_path
    framework_secrets = framework / "config" / "default" / "secrets.json"
    framework_paths = [str(framework_secrets)] if framework_secrets.exists() else []
    pipeline_secrets = bundle / "pipeline_configs" / "dev_secrets.json"
    return SecretsManager(
        str(framework / "schemas" / "secrets.json"),
        framework_paths,
        [str(pipeline_secrets)] if pipeline_secrets.exists() else [],
    )


@pytest.fixture
def feature_samples_substitution_manager(feature_samples_bundle_path, pipeline_context):
    """SubstitutionManager using feature-samples dev substitutions."""
    from pipeline_config import initialize_substitution_manager
    from substitution_manager import SubstitutionManager

    bundle = feature_samples_bundle_path
    dev_subs = bundle / "pipeline_configs" / "dev_substitutions.json"
    paths = [str(dev_subs)] if dev_subs.exists() else []
    mgr = SubstitutionManager(paths, paths)
    initialize_substitution_manager(mgr)
    return mgr
