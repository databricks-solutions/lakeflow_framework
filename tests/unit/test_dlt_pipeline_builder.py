"""Unit tests for dlt_pipeline_builder.py - mandatory / optional pipeline configuration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lakeflow_framework.constants import DLTPipelineSettingKeys
from lakeflow_framework.dlt_pipeline_builder import DLTPipelineBuilder


class _FakeConf:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def _builder_with_conf(conf_values):
    """Bare instance (no __init__) so only _load_mandatory_paths is exercised."""
    builder = DLTPipelineBuilder.__new__(DLTPipelineBuilder)
    builder.spark = SimpleNamespace(conf=_FakeConf(conf_values))
    return builder


def _base_conf(framework_src_path):
    return {
        DLTPipelineSettingKeys.BUNDLE_SOURCE_PATH: "/Workspace/bundle/src",
        DLTPipelineSettingKeys.FRAMEWORK_SOURCE_PATH: str(framework_src_path),
    }


class TestLoadMandatoryPaths:
    def test_workspace_host_is_not_mandatory(self):
        # Regression for #138: a DAB target that follows the CLI profile resolves
        # ${workspace.host} to "" and every pipeline failed at startup.
        assert DLTPipelineSettingKeys.WORKSPACE_HOST not in DLTPipelineBuilder.MANDATORY_CONFIG_PARAMS

    def test_missing_source_paths_still_raise(self, framework_src_path):
        builder = _builder_with_conf({})
        with pytest.raises(ValueError, match="Missing mandatory config parameters"):
            builder._load_mandatory_paths()

    def test_workspace_host_from_pipeline_configuration(self, framework_src_path):
        conf = {**_base_conf(framework_src_path), DLTPipelineSettingKeys.WORKSPACE_HOST: "https://adb-1.azuredatabricks.net"}
        builder = _builder_with_conf(conf)
        builder._load_mandatory_paths()
        assert builder.workspace_host == "https://adb-1.azuredatabricks.net"
        assert builder.bundle_path == "/Workspace/bundle/src"
        assert builder.framework_path == str(framework_src_path)

    def test_workspace_host_falls_back_to_spark_workspace_url(self, framework_src_path):
        conf = {
            **_base_conf(framework_src_path),
            DLTPipelineSettingKeys.WORKSPACE_HOST: "",  # what an unpinned ${workspace.host} resolves to
            DLTPipelineBuilder.SPARK_WORKSPACE_URL_CONF: "adb-1.azuredatabricks.net",
        }
        builder = _builder_with_conf(conf)
        builder._load_mandatory_paths()
        assert builder.workspace_host == "adb-1.azuredatabricks.net"

    def test_workspace_host_none_when_neither_available(self, framework_src_path):
        builder = _builder_with_conf(_base_conf(framework_src_path))
        builder._load_mandatory_paths()
        assert builder.workspace_host is None
