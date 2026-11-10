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


@pytest.fixture
def template_definition_validator(framework_src_path: Path):
    schema = framework_src_path / FrameworkPaths.TEMPLATE_DEFINITION_SPEC_SCHEMA_PATH.lstrip("./")
    return utility.JSONValidator(str(schema))


def _template_definition_with_default(param_type: str, default):
    return {
        "name": f"default_{param_type}_template",
        "parameters": {
            "dataFlowId": {"type": "string", "required": True},
            "optionalParam": {
                "type": param_type,
                "required": False,
                "default": default,
            },
        },
        "template": {
            "dataFlowId": "${param.dataFlowId}",
            "value": "${param.optionalParam}",
        },
    }


class TestTemplateDefinitionParameterDefaults:
    """Parameter ``default`` must accept every declared parameter type (#127)."""

    @pytest.mark.parametrize(
        "param_type,default",
        [
            ("string", "bronze"),
            ("integer", 42),
            ("boolean", True),
            ("list", ["*", "_change_type as cdc_change_type"]),
            ("list", []),
            ("object", {"region": "us"}),
            ("object", {}),
        ],
        ids=[
            "string",
            "integer",
            "boolean",
            "list-with-values",
            "list-empty",
            "object-with-values",
            "object-empty",
        ],
    )
    def test_default_value_matches_parameter_type(
        self, template_definition_validator, param_type, default
    ):
        payload = _template_definition_with_default(param_type, default)
        errors = template_definition_validator.validate(payload)
        assert errors == [], f"type={param_type!r} default={default!r}: {errors}"

    def test_rejects_null_default(self, template_definition_validator):
        payload = _template_definition_with_default("string", None)
        errors = template_definition_validator.validate(payload)
        assert errors, "null defaults should be rejected"


class TestNodespecPythonTransformationSchema:
    """``source`` is accepted on python transformations only, not on python sources."""

    @pytest.fixture
    def nodespec_validator(self, framework_src_path: Path):
        return utility.JSONValidator(str(framework_src_path / FrameworkPaths.NODESPEC_SPEC_SCHEMA_PATH.lstrip("./")))

    @staticmethod
    def _spec(python_node):
        return {
            "data_flow_id": "py_chain", "data_flow_group": "grp", "data_flow_type": "nodespec",
            "nodes": [
                {"name": "v_src", "node_type": "source", "source_type": "delta",
                 "config": {"database": "db", "table": "t"}},
                python_node,
                {"name": "target_out", "node_type": "target", "target_type": "delta",
                 "config": {"table": "out", "sources": ["v_py"]}},
            ],
        }

    def test_python_transformation_accepts_source(self, nodespec_validator):
        node = {"name": "v_py", "node_type": "transformation", "transformation_type": "python",
                "config": {"function_path": "f.py", "source": "v_src", "mode": "stream"}}
        assert nodespec_validator.validate(self._spec(node)) == []

    def test_python_source_node_rejects_source(self, nodespec_validator):
        node = {"name": "v_py", "node_type": "source", "source_type": "python",
                "config": {"function_path": "f.py", "source": "v_src"}}
        assert nodespec_validator.validate(self._spec(node)) != []
