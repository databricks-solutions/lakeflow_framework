"""Golden JSON comparisons for template expansion and spec mapping."""

from __future__ import annotations

import json

from lakeflow_framework.dataflow_spec_builder.spec_mapper import SpecMapper
from lakeflow_framework.dataflow_spec_builder.template_processor import TemplateProcessor


def _load_json(fixtures_dir, *parts):
    return json.loads((fixtures_dir.joinpath(*parts)).read_text())


class TestTemplateExpansionGolden:
    def test_minimal_template_expansion_matches_golden(
        self,
        pipeline_context,
        template_bundle_tree,
        framework_src_path,
        fixtures_dir,
    ):
        processor = TemplateProcessor(str(template_bundle_tree), str(framework_src_path))
        template_spec = _load_json(fixtures_dir, "specs", "template_main_minimal.json")
        expanded = processor.process_template_spec(
            "/virtual/template_main_minimal.json",
            template_spec,
        )
        golden = _load_json(fixtures_dir, "golden", "template_expansion_minimal.json")
        assert expanded == golden


class TestSpecMappingGolden:
    def test_legacy_spec_mapping_matches_golden(
        self,
        pipeline_context,
        framework_src_path,
        fixtures_dir,
    ):
        mapper = SpecMapper(str(framework_src_path), max_workers=1)
        spec_path = "/legacy/spec.json"
        legacy = _load_json(fixtures_dir, "specs", "legacy_mapping_input.json")
        result = mapper.apply_mappings({spec_path: legacy}, global_version="0.2.0")
        golden = _load_json(fixtures_dir, "golden", "spec_mapping_legacy.json")
        assert result[spec_path] == golden
