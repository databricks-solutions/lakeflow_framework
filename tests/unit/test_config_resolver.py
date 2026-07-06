"""Unit tests for config_resolver.py."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from config_resolver import (
    load_framework_config,
    resolve_framework_config_dir,
    resolve_framework_config_path,
)
from constants import FrameworkPaths


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
        (fw / "config" / "default").mkdir(parents=True)
        with pytest.raises(ValueError, match="Path does not exist"):
            load_framework_config("missing.json", str(fw))

    def test_loads_config_when_name_is_sequence(self, minimal_framework_tree: Path):
        from constants import FrameworkPaths

        result = load_framework_config(
            FrameworkPaths.GLOBAL_CONFIG, str(minimal_framework_tree)
        )
        assert "mandatory_table_properties" in result

    def test_returns_empty_when_sequence_missing_and_fail_false(self, tmp_path: Path):
        from constants import FrameworkPaths

        fw = tmp_path / "fw"
        (fw / "config" / "default").mkdir(parents=True)
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
        assert resolved.endswith(f"config/default/{mapping}")


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
