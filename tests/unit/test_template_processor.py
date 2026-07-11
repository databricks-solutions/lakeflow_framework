"""Unit tests for template_processor.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lakeflow_framework.dataflow_spec_builder.template_processor import TemplateProcessor
from helpers import make_tree


def _processor(bundle_path: Path, framework_src_path: Path) -> TemplateProcessor:
    return TemplateProcessor(str(bundle_path), str(framework_src_path))


def _minimal_template_spec(parameter_sets=None):
    spec = {
        "template": "minimal_template",
        "parameterSets": parameter_sets
        or [
            {
                "dataFlowId": "from_template_a",
                "sourceSystem": "erp",
                "sourceViewName": "v_tpl_a",
                "path": "/data/a",
                "database": "db_a",
                "table": "tbl_a",
            }
        ],
    }
    return spec


class TestTemplateProcessorExpansion:
    def test_expands_template_into_one_spec_per_parameter_set(
        self,
        pipeline_context,
        template_bundle_tree: Path,
        framework_src_path: Path,
        fixtures_dir: Path,
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        template_spec = json.loads(
            (fixtures_dir / "specs" / "template_main_minimal.json").read_text()
        )
        result = processor.process_template_spec(
            "/virtual/template_main_minimal.json",
            template_spec,
        )
        assert len(result) == 2
        ids = {spec["dataFlowId"] for spec in result.values()}
        assert ids == {"from_template_a", "from_template_b"}

    def test_marks_generated_specs_with_template_tags(
        self,
        pipeline_context,
        template_bundle_tree: Path,
        framework_src_path: Path,
        fixtures_dir: Path,
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        template_spec = json.loads(
            (fixtures_dir / "specs" / "template_main_minimal.json").read_text()
        )
        template_spec["parameterSets"] = [template_spec["parameterSets"][0]]
        result = processor.process_template_spec("/virtual/spec.json", template_spec)
        spec = next(iter(result.values()))
        assert spec["tags"]["_isTemplateGenerated"] is True
        assert spec["tags"]["_templateName"] == "minimal_template"

    def test_applies_optional_parameter_defaults(
        self,
        pipeline_context,
        framework_src_path: Path,
        fixtures_dir: Path,
        tmp_path: Path,
    ):
        bundle = tmp_path / "bundle"
        defaults_src = fixtures_dir / "bundles" / "templates" / "defaults_template.json"
        make_tree(bundle, {
            "templates/defaults_template.json": defaults_src.read_text(),
        })
        processor = _processor(bundle, framework_src_path)
        template_spec = {
            "template": "defaults_template",
            "parameterSets": [
                {
                    "dataFlowId": "with_default",
                    "sourceSystem": "erp",
                    "sourceViewName": "v1",
                    "path": "/data",
                    "database": "db",
                    "table": "tbl",
                }
            ],
        }
        result = processor.process_template_spec("/virtual/defaults.json", template_spec)
        spec = next(iter(result.values()))
        assert spec["targetDetails"]["layer"] == "bronze"

    def test_expands_yaml_template_definition(
        self,
        pipeline_context,
        framework_src_path: Path,
        fixtures_dir: Path,
        tmp_path: Path,
    ):
        bundle = tmp_path / "bundle"
        yaml_src = fixtures_dir / "bundles" / "templates" / "typed_template.yaml"
        make_tree(bundle, {"templates/typed_template.yml": yaml_src.read_text()})
        processor = _processor(bundle, framework_src_path)
        template_spec = {
            "template": "typed_template",
            "parameterSets": [
                {
                    "dataFlowId": "typed_flow",
                    "batchSize": 10,
                    "enabled": True,
                    "tags": ["a", "b"],
                    "metadata": {"region": "us"},
                    "label": "orders",
                }
            ],
        }
        result = processor.process_template_spec(
            "/virtual/typed.yaml",
            template_spec,
            spec_file_format="yaml",
        )
        spec = next(iter(result.values()))
        assert spec["features"]["batchSize"] == 10
        assert spec["features"]["enabled"] is True
        assert spec["features"]["tags"] == ["a", "b"]
        assert spec["features"]["metadata"] == {"region": "us"}
        assert spec["description"] == "prefix-orders-suffix"


class TestTemplateProcessorCaching:
    def test_caches_template_definition(
        self,
        pipeline_context,
        template_bundle_tree: Path,
        framework_src_path: Path,
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        first = processor._get_template_definition("minimal_template", "json")
        info = processor.get_cache_info()
        assert info["cached_templates"] == 1
        assert info["template_names"] == ["minimal_template"]
        second = processor._get_template_definition("minimal_template", "json")
        assert first is second

    def test_clear_cache_forces_reload(
        self,
        pipeline_context,
        template_bundle_tree: Path,
        framework_src_path: Path,
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        first = processor._get_template_definition("minimal_template", "json")
        processor.clear_cache()
        assert processor.get_cache_info()["cached_templates"] == 0
        second = processor._get_template_definition("minimal_template", "json")
        assert first == second
        assert first is not second


class TestTemplateProcessorValidation:
    def test_raises_when_template_spec_fails_schema_validation(
        self, pipeline_context, template_bundle_tree, framework_src_path
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        with pytest.raises(ValueError, match="Template definition validation failed"):
            processor.process_template_spec(
                "/bad.json",
                {"template": "minimal_template", "parameterSets": [], "unexpected": True},
            )

    def test_raises_when_template_name_missing(
        self, pipeline_context, template_bundle_tree, framework_src_path
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        with pytest.raises(ValueError, match="validation failed|Template name must be provided"):
            processor.process_template_spec(
                "/x.json",
                {"template": "", "parameterSets": [{"dataFlowId": "x"}]},
            )

    def test_raises_when_parameter_sets_empty(
        self, pipeline_context, template_bundle_tree, framework_src_path
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        with pytest.raises(ValueError, match="validation failed|Dataflow specs must be provided"):
            processor.process_template_spec(
                "/x.json",
                {"template": "minimal_template", "parameterSets": []},
            )

    def test_raises_when_template_file_not_found(
        self, pipeline_context, template_bundle_tree, framework_src_path, fixtures_dir
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        template_spec = _minimal_template_spec()
        template_spec["template"] = "does_not_exist"
        with pytest.raises(FileNotFoundError, match="Template not found"):
            processor.process_template_spec("/x.json", template_spec)

    def test_raises_when_template_definition_fails_schema(
        self, pipeline_context, framework_src_path, tmp_path
    ):
        bundle = tmp_path / "bundle"
        make_tree(bundle, {
            "templates/invalid_template.json": json.dumps({"template": {}}),
        })
        processor = _processor(bundle, framework_src_path)
        with pytest.raises(ValueError, match="Template file validation failed"):
            processor._get_template_definition("invalid_template", "json")

    def test_raises_when_required_parameter_missing(
        self,
        pipeline_context,
        template_bundle_tree: Path,
        framework_src_path: Path,
        fixtures_dir: Path,
    ):
        processor = _processor(template_bundle_tree, framework_src_path)
        template_spec = json.loads(
            (fixtures_dir / "specs" / "template_main_minimal.json").read_text()
        )
        template_spec["parameterSets"] = [{"dataFlowId": "only_id"}]
        with pytest.raises(ValueError, match="missing required parameters"):
            processor.process_template_spec("/x.json", template_spec)

    def test_raises_when_parameter_type_mismatch(
        self, pipeline_context, framework_src_path, fixtures_dir, tmp_path
    ):
        bundle = tmp_path / "bundle"
        yaml_src = fixtures_dir / "bundles" / "templates" / "typed_template.yaml"
        make_tree(bundle, {"templates/typed_template.yaml": yaml_src.read_text()})
        processor = _processor(bundle, framework_src_path)
        template_spec = {
            "template": "typed_template",
            "parameterSets": [
                {
                    "dataFlowId": "typed_flow",
                    "batchSize": "not-an-int",
                    "enabled": True,
                    "tags": [],
                    "metadata": {},
                    "label": "x",
                }
            ],
        }
        with pytest.raises(ValueError, match="Expected type 'integer'"):
            processor.process_template_spec(
                "/virtual/typed.yaml", template_spec, spec_file_format="yaml"
            )

    def test_raises_when_template_has_no_parameters(
        self, pipeline_context, framework_src_path, tmp_path
    ):
        bundle = tmp_path / "bundle"
        make_tree(bundle, {
            "templates/empty_params.json": json.dumps({
                "name": "empty_params",
                "parameters": {},
                "template": {"dataFlowId": "${param.dataFlowId}"},
            }),
        })
        processor = _processor(bundle, framework_src_path)
        with pytest.raises(ValueError, match="contains no parameters"):
            processor._get_template_parameters(
                json.loads((bundle / "templates/empty_params.json").read_text()),
                "empty_params",
            )

    def test_raises_when_dataflow_id_parameter_not_declared(
        self, pipeline_context, framework_src_path, tmp_path
    ):
        definition = {
            "name": "no_id",
            "parameters": {
                "sourceSystem": {"type": "string", "required": True},
            },
            "template": {
                "dataFlowId": "${param.dataFlowId}",
                "sourceSystem": "${param.sourceSystem}",
            },
        }
        processor = _processor(tmp_path, framework_src_path)
        with pytest.raises(ValueError, match="must declare 'dataFlowId' parameter"):
            processor._get_template_parameters(definition, "no_id")

    def test_raises_when_template_uses_undefined_placeholder(
        self, pipeline_context, framework_src_path, tmp_path
    ):
        definition = {
            "name": "bad_placeholder",
            "parameters": {
                "dataFlowId": {"type": "string", "required": True},
            },
            "template": {
                "dataFlowId": "${param.dataFlowId}",
                "sourceSystem": "${param.undefinedParam}",
            },
        }
        processor = _processor(tmp_path, framework_src_path)
        with pytest.raises(ValueError, match="undefined parameters"):
            processor._get_template_parameters(definition, "bad_placeholder")

    def test_warns_about_unused_parameter_definitions(
        self,
        pipeline_context,
        framework_src_path,
        caplog,
    ):
        definition = {
            "name": "unused",
            "parameters": {
                "dataFlowId": {"type": "string", "required": True},
                "neverUsed": {"type": "string", "required": False},
            },
            "template": {"dataFlowId": "${param.dataFlowId}"},
        }
        processor = _processor(Path("/tmp/unused"), framework_src_path)
        with caplog.at_level("WARNING"):
            params = processor._get_template_parameters(definition, "unused")
        assert "neverUsed" in params
        assert any("unused parameter definitions" in r.message for r in caplog.records)

    def test_raises_when_generation_references_missing_optional_param(
        self, pipeline_context, framework_src_path, tmp_path
    ):
        bundle = tmp_path / "bundle"
        make_tree(bundle, {
            "templates/optional_ref.json": json.dumps({
                "name": "optional_ref",
                "parameters": {
                    "dataFlowId": {"type": "string", "required": True},
                    "optionalLayer": {"type": "string", "required": False},
                },
                "template": {
                    "dataFlowId": "${param.dataFlowId}",
                    "dataFlowGroup": "g",
                    "layer": "${param.optionalLayer}",
                },
            }),
        })
        processor = _processor(bundle, framework_src_path)
        template_spec = {
            "template": "optional_ref",
            "parameterSets": [{"dataFlowId": "flow_only"}],
        }
        with pytest.raises(ValueError, match="Failed to generate spec from template"):
            processor.process_template_spec("/virtual/optional.json", template_spec)


class TestTemplateProcessorHelpers:
    def test_validate_parameter_type_rejects_unknown_type(self, pipeline_context, framework_src_path):
        processor = _processor(Path("/tmp"), framework_src_path)
        assert processor._validate_parameter_type("x", "decimal") is False

    def test_replace_string_placeholders_returns_non_string_values_for_full_match(
        self, pipeline_context, framework_src_path
    ):
        processor = _processor(Path("/tmp"), framework_src_path)
        assert processor._replace_string_placeholders("${param.count}", {"count": 7}) == 7
        assert processor._replace_string_placeholders("${param.flag}", {"flag": False}) is False

    def test_get_param_value_raises_key_error(self, pipeline_context, framework_src_path):
        processor = _processor(Path("/tmp"), framework_src_path)
        with pytest.raises(KeyError, match="Parameter 'missing' not found"):
            processor._get_param_value("missing", {})

    def test_resolve_template_path_returns_none_for_missing_json(
        self, pipeline_context, framework_src_path
    ):
        processor = _processor(Path("/tmp"), framework_src_path)
        assert processor._resolve_template_path("/no/such/template", "json") is None

    def test_resolve_template_path_finds_yml_when_yaml_missing(
        self, pipeline_context, framework_src_path, tmp_path
    ):
        bundle = tmp_path / "bundle"
        templates = bundle / "templates"
        templates.mkdir(parents=True)
        (templates / "yml_only.yml").write_text(
            "name: yml_only\nparameters:\n  dataFlowId:\n    type: string\n"
            "    required: true\ntemplate:\n  dataFlowId: ${param.dataFlowId}\n"
        )
        processor = _processor(bundle, framework_src_path)
        base = str(templates / "yml_only")
        assert processor._resolve_template_path(base, "yaml").endswith("yml_only.yml")

    def test_generate_spec_preserves_literal_non_string_values(
        self, pipeline_context, framework_src_path
    ):
        processor = _processor(Path("/tmp"), framework_src_path)
        template = {"retries": 3, "enabled": True, "name": "${param.dataFlowId}"}
        result = processor._generate_spec(template, {"dataFlowId": "flow_x"})
        assert result["retries"] == 3
        assert result["enabled"] is True
        assert result["name"] == "flow_x"
