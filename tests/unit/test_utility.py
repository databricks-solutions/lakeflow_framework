"""Unit tests for utility.py — pure helpers and config loading."""

from __future__ import annotations

import json
from pathlib import Path

import logging

import pytest
import yaml

from lakeflow_framework.constants import SupportedSpecFormat
import lakeflow_framework.utility as utility


class TestGetFormatSuffixes:
    @pytest.mark.parametrize(
        "file_format,suffix_type,expected",
        [
            (SupportedSpecFormat.JSON.value, "main_spec", ["_main.json"]),
            (SupportedSpecFormat.JSON.value, "substitutions", ["_substitutions.json"]),
            (SupportedSpecFormat.YAML.value, "main_spec", ["_main.yaml", "_main.yml"]),
        ],
    )
    def test_returns_suffix_list_for_valid_inputs(self, file_format, suffix_type, expected):
        assert utility.get_format_suffixes(file_format, suffix_type) == expected

    def test_raises_for_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid file format"):
            utility.get_format_suffixes("xml", "main_spec")

    def test_raises_for_invalid_suffix_type(self):
        with pytest.raises(ValueError, match="Invalid suffix type"):
            utility.get_format_suffixes("json", "unknown_type")


class TestMergeDictsRecursively:
    def test_pipeline_keys_take_precedence_over_framework(self):
        pipeline = {"tokens": {"catalog": "pipeline_cat", "schema": "pl_schema"}}
        framework = {"tokens": {"catalog": "fw_cat", "layer": "bronze"}}
        merged = utility.merge_dicts_recursively(pipeline, framework)
        assert merged["tokens"]["catalog"] == "pipeline_cat"
        assert merged["tokens"]["layer"] == "bronze"
        assert merged["tokens"]["schema"] == "pl_schema"

    def test_deep_merge_nested_dicts(self):
        d1 = {"a": {"x": 1, "y": 2}}
        d2 = {"a": {"y": 3, "z": 4}}
        assert utility.merge_dicts_recursively(d1, d2) == {"a": {"x": 1, "y": 2, "z": 4}}


class TestDeepMerge:
    def test_overlay_wins_on_conflicts(self):
        base = {"logger": {"level": "INFO", "enabled": False}}
        overlay = {"logger": {"enabled": True}}
        assert utility.deep_merge(base, overlay) == {
            "logger": {"level": "INFO", "enabled": True}
        }

    def test_does_not_mutate_inputs(self):
        base = {"a": 1}
        overlay = {"b": 2}
        utility.deep_merge(base, overlay)
        assert base == {"a": 1}


class TestLoadConfigFile:
    def test_loads_json_file(self, tmp_path: Path):
        path = tmp_path / "cfg.json"
        path.write_text('{"key": "value"}')
        assert utility.load_config_file(str(path), "json") == {"key": "value"}

    def test_loads_yaml_file(self, tmp_path: Path):
        path = tmp_path / "cfg.yaml"
        path.write_text("key: value\n")
        assert utility.load_config_file(str(path), "yaml") == {"key": "value"}

    def test_raises_when_file_missing_and_fail_on_not_exists(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Path does not exist"):
            utility.load_config_file(str(tmp_path / "missing.json"), "json", True)

    def test_returns_empty_dict_when_file_missing_and_fail_false(self, tmp_path: Path):
        assert utility.load_config_file(str(tmp_path / "missing.json"), "json", False) == {}


class TestLoadConfigFileAuto:
    def test_detects_json_extension(self, tmp_path: Path):
        path = tmp_path / "cfg.json"
        path.write_text('{"a": 1}')
        assert utility.load_config_file_auto(str(path)) == {"a": 1}

    def test_detects_yaml_extension(self, tmp_path: Path):
        path = tmp_path / "cfg.yml"
        path.write_text("a: 1\n")
        assert utility.load_config_file_auto(str(path)) == {"a": 1}

    def test_raises_for_unknown_extension(self, tmp_path: Path):
        path = tmp_path / "cfg.txt"
        path.write_text("x")
        with pytest.raises(ValueError, match="Unable to detect file format"):
            utility.load_config_file_auto(str(path))


class TestLoadConfigFiles:
    def test_loads_matching_suffixes_in_directory(self, tmp_path: Path):
        (tmp_path / "a.json").write_text('{"id": "a"}')
        (tmp_path / "b.json").write_text('{"id": "b"}')
        (tmp_path / "ignore.txt").write_text("nope")
        data = utility.load_config_files(str(tmp_path), "json", ".json")
        assert len(data) == 2
        assert {v["id"] for v in data.values()} == {"a", "b"}


class TestJSONValidator:
    def test_validates_against_schema(self, framework_package_path: Path, fixtures_dir: Path):
        schema = framework_package_path / "schemas" / "secrets.json"
        validator = utility.JSONValidator(str(schema))
        payload = json.loads((fixtures_dir / "specs" / "framework_secrets.json").read_text())
        assert validator.validate(payload) == []

    def test_returns_errors_for_invalid_payload(self, framework_package_path: Path):
        schema = framework_package_path / "schemas" / "secrets.json"
        validator = utility.JSONValidator(str(schema))
        errors = validator.validate({"bad_entry": {"scope": 123}})
        assert errors

    def test_raises_when_schema_missing(self, tmp_path: Path):
        with pytest.raises(ValueError, match="JSON Schema not found"):
            utility.JSONValidator(str(tmp_path / "missing.json"))


class TestLoadPythonFunction:
    def test_loads_callable_from_file(self, tmp_path: Path):
        mod = tmp_path / "fn.py"
        mod.write_text("def my_fn(x):\n    return x\n")
        fn = utility.load_python_function(str(mod), "my_fn", required_params=["x"])
        assert fn(42) == 42

    def test_raises_when_required_params_missing(self, tmp_path: Path):
        mod = tmp_path / "fn.py"
        mod.write_text("def my_fn():\n    pass\n")
        with pytest.raises(ValueError, match="missing required parameters"):
            utility.load_python_function(str(mod), "my_fn", required_params=["x"])

    def test_raises_when_function_missing(self, tmp_path: Path):
        mod = tmp_path / "fn.py"
        mod.write_text("def other():\n    pass\n")
        with pytest.raises(AttributeError, match="must contain"):
            utility.load_python_function(str(mod), "my_fn")


class TestLoadPythonFunctionFromModule:
    def test_loads_callable_from_importable_module(self, tmp_path: Path, monkeypatch):
        pkg = tmp_path / "sample_mod.py"
        pkg.write_text("def handler(x):\n    return x + 1\n")
        monkeypatch.syspath_prepend(str(tmp_path))
        fn = utility.load_python_function_from_module("sample_mod.handler", required_params=["x"])
        assert fn(1) == 2

    def test_raises_for_invalid_module_format(self):
        with pytest.raises(ValueError, match="Invalid pythonModule format"):
            utility.load_python_function_from_module("no_dot_function")

    def test_raises_when_module_not_found(self):
        with pytest.raises(ImportError, match="Could not import module"):
            utility.load_python_function_from_module("missing.module.fn")


class TestMergeDicts:
    def test_merges_multiple_dicts_left_to_right(self):
        assert utility.merge_dicts({"a": 1}, {"b": 2}, {"c": 3}) == {"a": 1, "b": 2, "c": 3}

    def test_skips_none_dicts(self):
        assert utility.merge_dicts({"a": 1}, None, {"b": 2}) == {"a": 1, "b": 2}


class TestReplaceDictKeyValue:
    def test_prefixes_matching_string_values(self):
        spec = {"schemaPath": "schema.json", "nested": {"schemaPath": "inner.json"}}
        utility.replace_dict_key_value(spec, "schemaPath", "/base")
        assert spec["schemaPath"] == "/base/schema.json"
        assert spec["nested"]["schemaPath"] == "/base/inner.json"

    def test_skips_empty_values(self):
        spec = {"schemaPath": ""}
        utility.replace_dict_key_value(spec, "schemaPath", "/base")
        assert spec["schemaPath"] == ""


class TestListSubPaths:
    def test_lists_only_subdirectories(self, tmp_path: Path):
        (tmp_path / "dir_a").mkdir()
        (tmp_path / "dir_b").mkdir()
        (tmp_path / "file.txt").write_text("x")
        names = set(utility.list_sub_paths(str(tmp_path)))
        assert names == {"dir_a", "dir_b"}


class TestGetJsonFromFiles:
    def test_loads_json_files_with_suffix(self, tmp_path: Path):
        (tmp_path / "a.json").write_text('{"id": "a"}')
        (tmp_path / "b.json").write_text('{"id": "b"}')
        data = utility.get_json_from_files(str(tmp_path), ".json")
        assert len(data) == 2


class TestGetYamlFromFiles:
    def test_loads_yaml_files_with_suffix(self, tmp_path: Path):
        (tmp_path / "a.yaml").write_text("id: a\n")
        data = utility.get_yaml_from_files(str(tmp_path), ".yaml")
        assert len(data) == 1


class TestGetDataFromFilesParallel:
    def test_loads_files_grouped_by_suffix(self, tmp_path: Path):
        sub = tmp_path / "group" / "dataflowspec"
        sub.mkdir(parents=True)
        (sub / "flow_main.json").write_text('{"dataFlowId": "x"}')
        data = utility.get_data_from_files_parallel(
            str(tmp_path / "group"),
            "json",
            "_main.json",
            recursive=True,
            max_workers=2,
        )
        assert "_main.json" in data
        assert len(data["_main.json"]) == 1

    def test_raises_when_path_missing(self):
        with pytest.raises(ValueError, match="Path does not exist"):
            utility.get_data_from_files_parallel("/no/such/path", "json", ".json")

    def test_skips_files_that_fail_to_load(self, tmp_path: Path):
        sub = tmp_path / "group" / "dataflowspec"
        sub.mkdir(parents=True)
        (sub / "good_main.json").write_text('{"dataFlowId": "ok"}')
        (sub / "bad_main.json").write_text("{not json")
        data = utility.get_data_from_files_parallel(
            str(tmp_path / "group"),
            "json",
            "_main.json",
            recursive=True,
            max_workers=1,
            logger=logging.getLogger("test.parallel"),
        )
        assert len(data["_main.json"]) == 1


class TestSetLogger:
    def test_delegates_to_create_default_logger(self):
        logger = utility.set_logger("lakeflow.test.compat", "WARNING")
        assert logger.name == "lakeflow.test.compat"
        assert logger.level == logging.WARNING
