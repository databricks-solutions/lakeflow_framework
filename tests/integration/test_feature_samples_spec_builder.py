"""Integration test: DataflowSpecBuilder against the feature-samples bundle."""

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
        assert spec.dataFlowType == "flow"
        assert spec.targetFormat == "delta"
        assert len(spec.flowGroups) == 1
        assert spec.flowGroups[0]["flowGroupId"] == "main"
        assert spec.dataQualityExpectationsEnabled is True
        assert spec.quarantineMode == "flag"

        target = spec.get_target_details()
        assert "tgt_append_sql_flow" in target.table

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
