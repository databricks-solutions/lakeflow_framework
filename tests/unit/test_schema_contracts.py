"""Schema contract tests — fixtures must validate against package schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lakeflow_framework.constants import FrameworkPaths
import lakeflow_framework.utility as utility


@pytest.fixture
def main_validator(framework_src_path: Path):
    schema = framework_src_path / FrameworkPaths.MAIN_SPEC_SCHEMA_PATH.lstrip("./")
    return utility.JSONValidator(str(schema))


@pytest.fixture
def template_spec_validator(framework_src_path: Path):
    schema = framework_src_path / FrameworkPaths.TEMPLATE_SPEC_SCHEMA_PATH.lstrip("./")
    return utility.JSONValidator(str(schema))


@pytest.fixture
def secrets_validator(framework_src_path: Path):
    schema = framework_src_path / FrameworkPaths.SECRETS_SCHEMA_PATH.lstrip("./")
    return utility.JSONValidator(str(schema))


class TestSchemaContracts:
    def test_expanded_main_minimal_validates(self, fixtures_dir: Path, main_validator):
        payload = json.loads((fixtures_dir / "specs" / "expanded_main_minimal.json").read_text())
        errors = main_validator.validate(payload)
        assert errors == [], f"expanded_main_minimal.json: {errors}"

    def test_quarantine_table_minimal_validates(self, fixtures_dir: Path, main_validator):
        payload = json.loads((fixtures_dir / "specs" / "quarantine_table_minimal.json").read_text())
        errors = main_validator.validate(payload)
        assert errors == [], f"quarantine_table_minimal.json: {errors}"

    def test_template_main_minimal_validates(self, fixtures_dir: Path, template_spec_validator):
        payload = json.loads((fixtures_dir / "specs" / "template_main_minimal.json").read_text())
        errors = template_spec_validator.validate(payload)
        assert errors == [], f"template_main_minimal.json: {errors}"

    def test_substitution_fixtures_are_valid_json(self, fixtures_dir: Path):
        for name in ("framework_substitutions.json", "pipeline_substitutions.json"):
            data = json.loads((fixtures_dir / "specs" / name).read_text())
            assert isinstance(data, dict)

    def test_secrets_fixtures_validate(self, fixtures_dir: Path, secrets_validator):
        for name in ("framework_secrets.json", "pipeline_secrets.json"):
            payload = json.loads((fixtures_dir / "specs" / name).read_text())
            errors = secrets_validator.validate(payload)
            assert errors == [], f"{name}: {errors}"

    def test_minimal_template_definition_validates(self, fixtures_dir: Path, framework_src_path: Path):
        schema = framework_src_path / FrameworkPaths.TEMPLATE_DEFINITION_SPEC_SCHEMA_PATH.lstrip("./")
        validator = utility.JSONValidator(str(schema))
        payload = json.loads(
            (fixtures_dir / "bundles" / "templates" / "minimal_template.json").read_text()
        )
        errors = validator.validate(payload)
        assert errors == [], f"minimal_template.json: {errors}"
