"""Unit tests for config_resolver.py."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from lakeflow_framework.config_resolver import (
    load_framework_config,
    load_framework_default_json,
    load_framework_schema,
    resolve_framework_config_dir,
    resolve_framework_config_path,
)
from lakeflow_framework.constants import FrameworkPaths


class TestLoadFrameworkConfig:
    def test_loads_base_config_file(self, minimal_framework_tree: Path):
        result = load_framework_config("global.json", str(minimal_framework_tree))
        assert "mandatory_table_properties" in result

    def test_deep_merges_local_overlay(self, minimal_framework_tree: Path):
        overlay = minimal_framework_tree / "local" / "config"
        overlay.mkdir(parents=True)
        (overlay / "global.json").write_text('{"version": "overlay", "extra": true}')
        result = load_framework_config("global.json", str(minimal_framework_tree))
        assert result["version"] == "overlay"
        assert result["extra"] is True

    def test_raises_when_config_missing_and_fail_on_not_exists(self, tmp_path: Path):
        fw = tmp_path / "fw"
        (fw / "lakeflow_framework" / "config" / "default").mkdir(parents=True)
        with pytest.raises(ValueError, match="Path does not exist"):
            load_framework_config("missing.json", str(fw))

    def test_loads_config_when_name_is_sequence(self, minimal_framework_tree: Path):
        result = load_framework_config(
            FrameworkPaths.GLOBAL_CONFIG, str(minimal_framework_tree)
        )
        assert "mandatory_table_properties" in result

    def test_returns_empty_when_sequence_missing_and_fail_false(self, tmp_path: Path):
        fw = tmp_path / "fw"
        (fw / "lakeflow_framework" / "config" / "default").mkdir(parents=True)
        assert (
            load_framework_config(
                FrameworkPaths.GLOBAL_CONFIG,
                str(fw),
                fail_on_not_exists=False,
            )
            == {}
        )


class TestResolveFrameworkConfigDir:
    def test_prefers_local_config_subdirectory(self, minimal_framework_tree: Path):
        mapping = "dataflow_spec_mapping"
        local = minimal_framework_tree / "local" / "config" / mapping
        local.mkdir(parents=True)
        resolved = resolve_framework_config_dir(mapping, str(minimal_framework_tree))
        assert resolved.endswith(f"local/config/{mapping}")

    def test_falls_back_to_default_config(self, minimal_framework_tree: Path):
        mapping = "dataflow_spec_mapping"
        resolved = resolve_framework_config_dir(mapping, str(minimal_framework_tree))
        assert resolved.endswith(f"lakeflow_framework/config/default/{mapping}")


class TestResolveFrameworkConfigPath:
    def test_returns_default_config_when_no_override(self, minimal_framework_tree: Path):
        assert (
            resolve_framework_config_path(str(minimal_framework_tree))
            == FrameworkPaths.CONFIG_PATH
        )

    def test_warns_and_returns_override_when_layout_complete(self, minimal_framework_tree: Path):
        override = minimal_framework_tree / "config" / "override"
        override.mkdir(parents=True)
        (override / "global.json").write_text("{}")
        (override / "dataflow_spec_mapping").mkdir()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = resolve_framework_config_path(str(minimal_framework_tree))
        assert result == FrameworkPaths.CONFIG_OVERRIDE_PATH
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    def test_raises_when_no_framework_config_present(self, tmp_path: Path):
        fw = tmp_path / "fw"
        fw.mkdir()
        with pytest.raises(FileNotFoundError, match="No valid files found"):
            resolve_framework_config_path(str(fw))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _config_dir(framework_path: Path) -> Path:
    return framework_path / FrameworkPaths.CONFIG_PATH.lstrip("./")


def _local_dir(framework_path: Path) -> Path:
    return framework_path / FrameworkPaths.LOCAL_CONFIG_PATH.lstrip("./")


class TestWorkspaceFilesFirst:
    def test_loads_from_workspace_files_when_file_exists(self, tmp_path):
        data = {"key": "workspace_value", "nested": {"a": 1}}
        _write_json(_config_dir(tmp_path) / "test.json", data)

        result = load_framework_default_json("test.json", str(tmp_path))

        assert result == data

    def test_workspace_files_takes_priority_over_package_data(self, tmp_path):
        in_workspace = {"source": "workspace_files"}
        _write_json(_config_dir(tmp_path) / "global.json", in_workspace)

        result = load_framework_default_json("global.json", str(tmp_path))

        assert result["source"] == "workspace_files"

    def test_workspace_files_missing_falls_through_to_package_data(self, tmp_path):
        result = load_framework_default_json("global.json", str(tmp_path))

        assert isinstance(result, dict)
        assert len(result) > 0


class TestPackageDataFallback:
    def test_no_framework_path_loads_from_package(self):
        result = load_framework_default_json("global.json")

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_nonexistent_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="nonexistent_file.json"):
            load_framework_default_json("nonexistent_file.json")

    def test_nonexistent_file_with_framework_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_framework_default_json("nonexistent_file.json", str(tmp_path))


class TestLocalConfigOverlay:
    def test_overlay_merges_on_top_of_disk_base(self, tmp_path):
        base = {"logging": {"level": "INFO"}, "other": "unchanged"}
        overlay = {"logging": {"level": "DEBUG"}}
        _write_json(_config_dir(tmp_path) / "global.json", base)
        _write_json(_local_dir(tmp_path) / "global.json", overlay)

        result = load_framework_default_json("global.json", str(tmp_path))

        assert result["logging"]["level"] == "DEBUG"
        assert result["other"] == "unchanged"

    def test_overlay_merges_on_top_of_package_base(self, tmp_path):
        overlay = {"_test_override_key": "overlay_value"}
        _write_json(_local_dir(tmp_path) / "global.json", overlay)

        result = load_framework_default_json("global.json", str(tmp_path))

        assert result["_test_override_key"] == "overlay_value"

    def test_no_overlay_file_returns_base_unchanged(self, tmp_path):
        base = {"key": "value"}
        _write_json(_config_dir(tmp_path) / "global.json", base)

        result = load_framework_default_json("global.json", str(tmp_path))

        assert result == base

    def test_empty_overlay_does_not_alter_base(self, tmp_path):
        base = {"key": "value"}
        _write_json(_config_dir(tmp_path) / "global.json", base)
        _write_json(_local_dir(tmp_path) / "global.json", {})

        result = load_framework_default_json("global.json", str(tmp_path))

        assert result == base


class TestLoadFrameworkSchema:
    def test_returns_readable_traversable(self):
        traversable = load_framework_schema("main.json")
        content = traversable.read_text("utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_all_known_schemas(self):
        schemas = [
            "main.json",
            "flow_group.json",
            "expectations.json",
            "secrets.json",
            "spec_template.json",
            "spec_template_definition.json",
            "spec_mapping.json",
        ]
        for name in schemas:
            ref = load_framework_schema(name)
            data = json.loads(ref.read_text("utf-8"))
            assert isinstance(data, dict), f"{name} did not parse to a dict"
