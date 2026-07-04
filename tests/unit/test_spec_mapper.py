"""Unit tests for spec_mapper.py."""

from __future__ import annotations

import pytest

from dataflow_spec_builder.spec_mapper import SpecMapper


def _standard_spec_payload(data: dict) -> dict:
    return {
        "dataFlowId": "test_flow",
        "dataFlowType": "standard",
        "data": data,
    }


class TestSpecMapper:
    def test_rename_all_applies_global_mapping_version(
        self, pipeline_context, framework_src_path
    ):
        mapper = SpecMapper(str(framework_src_path), max_workers=1)
        specs = {
            "/spec.json": _standard_spec_payload(
                {"cdcApplyChanges": {"keys": "id"}, "sourceType": "delta"}
            )
        }
        result = mapper.apply_mappings(specs, global_version="0.2.0")
        data = result["/spec.json"]["data"]
        assert "cdcApplyChanges" not in data
        assert "cdcSettings" in data

    def test_conditional_move_skips_when_source_type_is_python(
        self, pipeline_context, framework_src_path
    ):
        mapper = SpecMapper(str(framework_src_path), max_workers=1)
        specs = {
            "/spec.json": _standard_spec_payload(
                {
                    "sourceType": "python",
                    "sourceDetails": {
                        "pythonFunctionPath": "/funcs/transform.py",
                    },
                }
            )
        }
        result = mapper.apply_mappings(specs, global_version="0.2.0")
        details = result["/spec.json"]["data"]["sourceDetails"]
        # Conditional move is skipped for sourceType=python; rename_all still applies.
        assert details["functionPath"] == "/funcs/transform.py"
        assert "pythonTransform" not in details

    def test_evaluate_condition_operators(self, pipeline_context, framework_src_path):
        mapper = SpecMapper(str(framework_src_path))
        data = {"sourceType": "delta", "mode": "stream"}

        assert mapper._evaluate_condition(
            data, {"key": "sourceType", "operator": "equal_to", "value": "delta"}
        )
        assert mapper._evaluate_condition(
            data, {"key": "sourceType", "operator": "not_equal_to", "value": "python"}
        )
        assert mapper._evaluate_condition(
            data, {"key": "mode", "operator": "in", "value": ["stream", "batch"]}
        )
        assert mapper._evaluate_condition(
            data, {"key": "mode", "operator": "not_in", "value": ["batch"]}
        )

    def test_get_nested_value_uses_dot_notation(self, pipeline_context, framework_src_path):
        mapper = SpecMapper(str(framework_src_path))
        data = {"sourceDetails": {"table": "orders"}}
        assert mapper._get_nested_value(data, "sourceDetails.table") == "orders"
        assert mapper._get_nested_value(data, "missing.path") is None

    def test_returns_empty_dict_when_no_specs(self, pipeline_context, framework_src_path):
        mapper = SpecMapper(str(framework_src_path))
        assert mapper.apply_mappings({}, global_version="0.2.0") == {}
