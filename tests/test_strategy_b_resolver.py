"""
Unit tests for ``load_framework_default_json()`` and ``load_framework_schema()``
— Strategy B Workspace Files-first resolver.

Coverage:
- Workspace Files-only: file exists in Workspace Files → loads from there (no package data involved).
- Package-data-only: no framework_path → loads via importlib.resources.
- Both sources: Workspace Files takes priority over package data.
- Sparse local/config overlay: only overridden keys change; unset keys come from base.
- Missing everywhere: FileNotFoundError raised.
- load_framework_schema() helper returns a readable traversable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from lakeflow_framework.config_resolver import load_framework_default_json, load_framework_schema
from lakeflow_framework.constants import FrameworkPaths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _config_dir(framework_path: Path) -> Path:
    """Return the on-disk config/default directory under framework_path."""
    return framework_path / FrameworkPaths.CONFIG_PATH.lstrip("./")


def _local_dir(framework_path: Path) -> Path:
    """Return the on-disk local/config directory under framework_path."""
    return framework_path / FrameworkPaths.LOCAL_CONFIG_PATH.lstrip("./")


# ---------------------------------------------------------------------------
# Disk-only tests
# ---------------------------------------------------------------------------

class TestWorkspaceFilesFirst:
    def test_loads_from_workspace_files_when_file_exists(self, tmp_path):
        data = {"key": "workspace_value", "nested": {"a": 1}}
        _write_json(_config_dir(tmp_path) / "test.json", data)

        result = load_framework_default_json("test.json", str(tmp_path))

        assert result == data

    def test_workspace_files_takes_priority_over_package_data(self, tmp_path):
        """When file is in Workspace Files, importlib.resources must NOT be consulted."""
        in_workspace = {"source": "workspace_files"}
        _write_json(_config_dir(tmp_path) / "global.json", in_workspace)

        # If package data were used it would return the real global.json content
        result = load_framework_default_json("global.json", str(tmp_path))

        assert result["source"] == "workspace_files"

    def test_workspace_files_missing_falls_through_to_package_data(self, tmp_path):
        """File not in Workspace Files → package data is used (no FileNotFoundError)."""
        # tmp_path has no config dir — falls through to importlib.resources
        result = load_framework_default_json("global.json", str(tmp_path))

        # Real package data contains at least "global" / pipeline keys
        assert isinstance(result, dict)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Package-data-only test (no framework_path)
# ---------------------------------------------------------------------------

class TestPackageDataFallback:
    def test_no_framework_path_loads_from_package(self):
        """When framework_path is None, importlib.resources is used directly."""
        result = load_framework_default_json("global.json")

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_nonexistent_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="nonexistent_file.json"):
            load_framework_default_json("nonexistent_file.json")

    def test_nonexistent_file_with_framework_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_framework_default_json("nonexistent_file.json", str(tmp_path))


# ---------------------------------------------------------------------------
# Overlay (local/config) tests
# ---------------------------------------------------------------------------

class TestLocalConfigOverlay:
    def test_overlay_merges_on_top_of_disk_base(self, tmp_path):
        base = {"logging": {"level": "INFO"}, "other": "unchanged"}
        overlay = {"logging": {"level": "DEBUG"}}  # sparse — only changes level
        _write_json(_config_dir(tmp_path) / "global.json", base)
        _write_json(_local_dir(tmp_path) / "global.json", overlay)

        result = load_framework_default_json("global.json", str(tmp_path))

        assert result["logging"]["level"] == "DEBUG"
        assert result["other"] == "unchanged"

    def test_overlay_merges_on_top_of_package_base(self, tmp_path):
        """Overlay applied even when disk base file is absent (falls to package data)."""
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


# ---------------------------------------------------------------------------
# load_framework_schema() helper
# ---------------------------------------------------------------------------

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
