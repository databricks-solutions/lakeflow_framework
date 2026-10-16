"""Integration test: DataflowSpecBuilder against the feature_samples bundle."""

from __future__ import annotations

import pytest

from lakeflow_framework.dataflow_spec_builder.dataflow_spec_builder import DataflowSpecBuilder

pytestmark = pytest.mark.integration


class TestFeatureSamplesSpecBuilder:
    def test_build_append_sql_flow_from_feature_samples_bundle(
        self,
        framework_src_path,
        feature_samples_bundle_path,
        feature_samples_secrets_manager,
        feature_samples_substitution_manager,
        pipeline_context,
    ):
        builder = DataflowSpecBuilder(
            bundle_path=str(feature_samples_bundle_path),
            framework_path=str(framework_src_path),
            filters={"data_flow_ids": "append_sql_flow"},
            secrets_manager=feature_samples_secrets_manager,
            ignore_validation_errors=True,
            max_workers=1,
        )
        specs = builder.build()

        assert len(specs) == 1
        spec = specs[0]
        assert spec.dataFlowId == "append_sql_flow"
        assert spec.dataFlowGroup == "feature_samples_general"
        assert spec.dataFlowType == "nodespec"
        assert spec.targetFormat == "delta"
        assert len(spec.flowGroups) == 1
        assert spec.flowGroups[0]["flowGroupId"] == "nodespec_main"
        assert spec.dataQualityExpectationsEnabled is True
        assert spec.quarantineMode == "flag"

        target = spec.get_target_details()
        assert "tgt_append_sql_flow" in target.table

    def test_build_chained_transformations_from_feature_samples_bundle(
        self,
        framework_src_path,
        feature_samples_bundle_path,
        feature_samples_secrets_manager,
        feature_samples_substitution_manager,
        pipeline_context,
    ):
        """Transformations chained off other transformations are standalone views."""
        builder = DataflowSpecBuilder(
            bundle_path=str(feature_samples_bundle_path),
            framework_path=str(framework_src_path),
            filters={"data_flow_ids": "chained_transformations"},
            secrets_manager=feature_samples_secrets_manager,
            ignore_validation_errors=False,
            max_workers=1,
        )
        specs = builder.build()

        assert len(specs) == 1
        group = specs[0].get_flow_groups()[0]
        assert set(group.get_views()) == {"v_chained_clean", "v_chained_enrich"}
        flow = group.get_flows()["f_chained_transformations"]
        assert flow.sourceView == "v_chained_shape"
        assert set(flow.get_views()) == {"v_chained_shape", "v_chained_customer"}

    def test_read_all_feature_sample_main_specs(
        self,
        framework_src_path,
        feature_samples_bundle_path,
        feature_samples_secrets_manager,
        feature_samples_substitution_manager,
        pipeline_context,
    ):
        """Smoke test: builder can load every main spec file in the bundle."""
        builder = DataflowSpecBuilder(
            bundle_path=str(feature_samples_bundle_path),
            framework_path=str(framework_src_path),
            filters={},
            secrets_manager=feature_samples_secrets_manager,
            ignore_validation_errors=True,
            max_workers=2,
        )
        main_specs, flow_specs = builder._read_dataflow_specs()
        assert len(main_specs) >= 30
        assert flow_specs == {}
