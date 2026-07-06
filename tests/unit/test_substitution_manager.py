"""Unit tests for substitution_manager.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from substitution_manager import SubstitutionManager


class TestSubstitutionManager:
    def test_substitutes_tokens_in_string(self, substitution_manager):
        result = substitution_manager.substitute_string(
            "catalog={catalog}, schema={schema}"
        )
        # Pipeline wins over framework for catalog; schema only in pipeline file.
        assert result == "catalog=pipeline_catalog, schema=pipeline_schema"

    def test_substitutes_tokens_in_nested_dict(self, substitution_manager):
        data = {
            "targetDetails": {
                "database": "{catalog}",
                "table": "{schema}",
            }
        }
        result = substitution_manager.substitute_dict(data)
        assert result["targetDetails"]["database"] == "pipeline_catalog"
        assert result["targetDetails"]["table"] == "pipeline_schema"

    def test_applies_prefix_suffix_rules(self, substitution_manager):
        data = {"table": "orders"}
        result = substitution_manager.substitute_dict(data)
        assert result["table"] == "fw_orders_v1"

    def test_raises_when_paths_not_provided(self):
        with pytest.raises(ValueError, match="must be provided"):
            SubstitutionManager([], ["/tmp/p.json"])

    def test_raises_when_multiple_framework_files_exist(self, tmp_path: Path, pipeline_context):
        fw1 = tmp_path / "fw1.json"
        fw2 = tmp_path / "fw2.json"
        pl = tmp_path / "pl.json"
        fw1.write_text("{}")
        fw2.write_text("{}")
        pl.write_text("{}")
        with pytest.raises(ValueError, match="Multiple framework"):
            SubstitutionManager([str(fw1), str(fw2)], [str(pl)])

    def test_substitute_string_raises_for_non_string(self, substitution_manager):
        with pytest.raises(TypeError, match="Expected string"):
            substitution_manager.substitute_string(123)  # type: ignore
