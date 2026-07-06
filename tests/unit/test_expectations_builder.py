"""Unit tests for expectations_builder.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dataflow_spec_builder.expectations_builder import DataQualityExpectationBuilder


@pytest.fixture
def expectations_builder(pipeline_context, framework_src_path):
    schema = str(framework_src_path / "schemas" / "expectations.json")
    return DataQualityExpectationBuilder(
        pipeline_context["logger"],
        schema,
        spec_file_format="json",
    )


class TestDataQualityExpectationBuilderInit:
    def test_raises_for_invalid_spec_format(self, pipeline_context, framework_src_path):
        schema = str(framework_src_path / "schemas" / "expectations.json")
        with pytest.raises(ValueError, match="Invalid spec file format"):
            DataQualityExpectationBuilder(
                pipeline_context["logger"], schema, spec_file_format="xml"
            )


class TestGetExpectationRules:
    def test_collects_enabled_rules_by_type(self, expectations_builder, fixtures_dir: Path):
        payload = json.loads(
            (fixtures_dir / "specs" / "expectations_minimal.json").read_text()
        )
        rules = expectations_builder.get_expectation_rules(payload, "expect")
        assert rules == {
            "id_not_null": "id IS NOT NULL",
            "tagged_rule": "status = 'active'",
        }

    def test_filters_by_tag(self, expectations_builder):
        payload = {
            "expect": [
                {"name": "prod_rule", "constraint": "status = 'active'", "tag": "prod", "enabled": True},
                {"name": "dev_rule", "constraint": "status = 'draft'", "tag": "dev", "enabled": True},
            ]
        }
        rules = expectations_builder.get_expectation_rules(payload, "expect", tag="prod")
        assert rules == {"prod_rule": "status = 'active'"}

    def test_returns_none_when_type_missing(self, expectations_builder):
        assert expectations_builder.get_expectation_rules({}, "expect") is None


class TestGetExpectations:
    def test_loads_single_file(self, expectations_builder, fixtures_dir: Path, tmp_path: Path):
        src = fixtures_dir / "specs" / "expectations_minimal.json"
        path = tmp_path / "rules_expectations.json"
        path.write_text(src.read_text())
        result = expectations_builder.get_expectations(str(path))
        assert result.expectRules["id_not_null"] == "id IS NOT NULL"
        assert result.expectOrDropRules["drop_bad_rows"] == "amount > 0"

    def test_loads_directory_of_expectations_files(
        self, expectations_builder, fixtures_dir: Path, tmp_path: Path
    ):
        dqe_dir = tmp_path / "dqe"
        dqe_dir.mkdir()
        (dqe_dir / "a_expectations.json").write_text(
            (fixtures_dir / "specs" / "expectations_minimal.json").read_text()
        )
        result = expectations_builder.get_expectations(str(dqe_dir))
        assert "id_not_null" in result.expectRules

    def test_raises_when_path_empty(self, expectations_builder):
        with pytest.raises(ValueError, match="path is not set"):
            expectations_builder.get_expectations("")

    def test_raises_when_file_missing(self, expectations_builder, tmp_path: Path):
        with pytest.raises(ValueError, match="Path does not exist"):
            expectations_builder.get_expectations(str(tmp_path / "missing_expectations.json"))

    def test_raises_when_validation_fails(
        self, expectations_builder, tmp_path: Path
    ):
        bad = tmp_path / "bad_expectations.json"
        bad.write_text('{"expect": [{"name": 1, "constraint": "x"}]}')
        with pytest.raises(ValueError, match="Invalid expectations"):
            expectations_builder.get_expectations(str(bad))
