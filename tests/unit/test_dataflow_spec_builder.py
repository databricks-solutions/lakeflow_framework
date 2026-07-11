"""Unit tests for dataflow_spec_builder.py — filters and parsing."""

from __future__ import annotations

import pytest

from lakeflow_framework.dataflow_spec_builder.dataflow_spec_builder import DataflowSpecBuilder


def _make_builder(secrets_manager, framework_src_path, bundle_path, filters=None, **kwargs):
    params = {"ignore_validation_errors": True, "max_workers": 1}
    params.update(kwargs)
    return DataflowSpecBuilder(
        bundle_path=str(bundle_path),
        framework_path=str(framework_src_path),
        filters=filters or {},
        secrets_manager=secrets_manager,
        **params,
    )


def _spec_payload(data_flow_id, group="g1", table="t1", data_flow_type="standard"):
    return {
        "dataFlowId": data_flow_id,
        "dataFlowGroup": group,
        "dataFlowType": data_flow_type,
        "targetDetails": {"table": table},
        "data": {"dataFlowId": data_flow_id},
    }


class TestDataflowSpecBuilderBuild:
    def test_build_produces_dataflow_spec_from_bundle_tree(
        self,
        secrets_manager,
        framework_src_path,
        dataflow_bundle_tree,
        pipeline_context,
    ):
        builder = _make_builder(
            secrets_manager,
            framework_src_path,
            dataflow_bundle_tree,
            ignore_validation_errors=False,
        )
        specs = builder.build()
        assert len(specs) == 1
        assert specs[0].dataFlowId == "minimal_flow"
        assert specs[0].dataFlowGroup == "test_group"
        assert specs[0].flowGroups

    def test_read_dataflow_specs_loads_main_files_recursively(
        self,
        secrets_manager,
        framework_src_path,
        dataflow_bundle_tree,
        pipeline_context,
    ):
        builder = _make_builder(secrets_manager, framework_src_path, dataflow_bundle_tree)
        main_specs, flow_specs = builder._read_dataflow_specs()
        assert len(main_specs) == 1
        assert flow_specs == {}
        only = next(iter(main_specs.values()))
        assert only["dataFlowId"] == "minimal_flow"

    def test_read_dataflow_specs_raises_when_no_main_files(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context
    ):
        builder = _make_builder(secrets_manager, framework_src_path, minimal_bundle_tree)
        with pytest.raises(ValueError, match="No dataflow specification files found"):
            builder._read_dataflow_specs()


class TestDataflowSpecBuilderPathHandling:
    def test_localize_paths_sets_local_path_and_resolves_schema(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context, tmp_path
    ):
        builder = _make_builder(secrets_manager, framework_src_path, minimal_bundle_tree)
        base = tmp_path / "dataflows" / "grp" / "dataflowspec"
        schema_dir = base / "schemas"
        schema_dir.mkdir(parents=True)
        schema_file = schema_dir / "target.json"
        schema_file.write_text("{}")
        spec = {"dataFlowId": "f1", "schemaPath": "target.json"}
        localized = builder._localize_paths(spec, str(base))
        assert localized["localPath"] == str(base)
        assert localized["schemaPath"] == str(schema_file)

    def test_resolve_python_function_path_finds_file_in_base_directory(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context, tmp_path
    ):
        builder = _make_builder(secrets_manager, framework_src_path, minimal_bundle_tree)
        base = tmp_path / "dataflows" / "grp" / "dataflowspec"
        fn_dir = base / "python_functions"
        fn_dir.mkdir(parents=True)
        fn_file = fn_dir / "transform.py"
        fn_file.write_text("def transform(): pass\n")
        resolved = builder._resolve_python_function_path(
            "transform.py", str(base), {"dataFlowId": "f1"}
        )
        assert resolved == str(fn_file)

    def test_get_base_path_strips_dataflowspec_suffix(self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context):
        builder = _make_builder(secrets_manager, framework_src_path, minimal_bundle_tree)
        path = "/bundle/dataflows/grp/dataflowspec/flow_main.json"
        assert builder._get_base_path(path) == "/bundle/dataflows/grp"


class TestDataflowSpecBuilderMergeFlowGroups:
    def test_merges_external_flow_groups_into_flow_type_spec(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context
    ):
        builder = _make_builder(secrets_manager, framework_src_path, minimal_bundle_tree)
        specs = {
            "/main.json": {
                "dataFlowId": "flow_a",
                "dataFlowType": "flow",
                "flowGroups": [],
                "data": {},
            }
        }
        flow_groups = {
            "flow_a": [{"flowGroupId": "extra", "flows": {}}],
        }
        merged = builder._merge_flow_groups(specs, flow_groups)
        assert merged["/main.json"]["flowGroups"][0]["flowGroupId"] == "extra"


class TestDataflowSpecBuilderExpectations:
    def test_get_expectations_loads_dqe_files_when_enabled(
        self,
        secrets_manager,
        framework_src_path,
        minimal_bundle_tree,
        pipeline_context,
        fixtures_dir,
        tmp_path,
    ):
        builder = _make_builder(secrets_manager, framework_src_path, minimal_bundle_tree)
        base = tmp_path / "dataflows" / "grp"
        expectations_dir = base / "expectations"
        expectations_dir.mkdir(parents=True)
        (expectations_dir / "rules_expectations.json").write_text(
            (fixtures_dir / "specs" / "expectations_minimal.json").read_text()
        )
        spec = {
            "dataFlowId": "f1",
            "dataQualityExpectationsEnabled": True,
            "dataQualityExpectationsPath": "rules_expectations.json",
        }
        updated = builder._get_expectations(spec, str(base))
        assert updated["dataQualityExpectations"]["expectRules"]["id_not_null"] == "id IS NOT NULL"

    def test_get_expectations_raises_when_path_missing(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context
    ):
        builder = _make_builder(secrets_manager, framework_src_path, minimal_bundle_tree)
        with pytest.raises(ValueError, match="path is not set"):
            builder._get_expectations(
                {"dataQualityExpectationsEnabled": True},
                "/base",
            )


class TestDataflowSpecBuilderFilters:
    def test_matches_filters_keeps_matching_data_flow_id(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context
    ):
        builder = _make_builder(
            secrets_manager,
            framework_src_path,
            minimal_bundle_tree,
            filters={"data_flow_ids": "keep_me"},
        )
        specs = {
            "/a.json": _spec_payload("keep_me"),
            "/b.json": _spec_payload("drop_me"),
        }
        filtered = builder._filter_dataflow_specs(specs)
        assert list(filtered.keys()) == ["/a.json"]

    def test_matches_filters_by_data_flow_group(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context
    ):
        builder = _make_builder(
            secrets_manager,
            framework_src_path,
            minimal_bundle_tree,
            filters={"data_flow_groups": "wanted_group"},
        )
        specs = {
            "/a.json": _spec_payload("id1", group="wanted_group"),
            "/b.json": _spec_payload("id2", group="other"),
        }
        filtered = builder._filter_dataflow_specs(specs)
        assert len(filtered) == 1
        assert filtered["/a.json"]["dataFlowGroup"] == "wanted_group"

    def test_parse_filter_splits_comma_separated_values(self):
        assert DataflowSpecBuilder._parse_filter("a, B ,c") == ["a", "b", "c"]
        assert DataflowSpecBuilder._parse_filter(None) == []

    def test_invalid_spec_format_raises(self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context):
        with pytest.raises(ValueError, match="Invalid enabled format"):
            DataflowSpecBuilder(
                bundle_path=str(minimal_bundle_tree),
                framework_path=str(framework_src_path),
                filters={},
                secrets_manager=secrets_manager,
                spec_file_format="xml",
            )

    def test_validate_dataflow_specs_raises_when_errors_and_not_ignored(
        self, secrets_manager, framework_src_path, minimal_bundle_tree, pipeline_context
    ):
        builder = _make_builder(
            secrets_manager,
            framework_src_path,
            minimal_bundle_tree,
            ignore_validation_errors=False,
        )
        bad_specs = {
            "/bad.json": {
                "fileType": "main",
                "data": {"dataFlowId": "x"},
            }
        }
        with pytest.raises(ValueError, match="Invalid dataflow spec files found"):
            builder._validate_dataflow_specs(bad_specs)
