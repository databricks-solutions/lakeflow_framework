"""Golden JSON comparisons for template expansion (phase 3 contract tests)."""

from __future__ import annotations

import json

from dataflow_spec_builder.template_processor import TemplateProcessor


class TestTemplateExpansionGolden:
    def test_minimal_template_expansion_matches_golden(
        self,
        pipeline_context,
        template_bundle_tree,
        framework_src_path,
        fixtures_dir,
    ):
        processor = TemplateProcessor(str(template_bundle_tree), str(framework_src_path))
        template_spec = json.loads(
            (fixtures_dir / "specs" / "template_main_minimal.json").read_text()
        )
        expanded = processor.process_template_spec(
            "/virtual/template_main_minimal.json",
            template_spec,
        )
        golden_path = fixtures_dir / "golden" / "template_expansion_minimal.json"
        golden = json.loads(golden_path.read_text())
        assert set(expanded.keys()) == set(golden.keys())
        for path, spec in expanded.items():
            assert spec["dataFlowId"] == golden[path]["dataFlowId"]
            assert spec["dataFlowGroup"] == golden[path]["dataFlowGroup"]
            assert spec["tags"]["_templateName"] == golden[path]["tags"]["_templateName"]
