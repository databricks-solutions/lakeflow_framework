"""Unit tests for constants.py."""

from lakeflow_framework.constants import (
    FrameworkPaths,
    PipelineBundlePaths,
    PipelineBundleSuffixesJson,
    SupportedSpecFormat,
    SystemColumns,
)


class TestFrameworkPaths:
    def test_config_paths_use_expected_segments(self):
        assert FrameworkPaths.CONFIG_PATH == "./lakeflow_framework/config/default"
        assert FrameworkPaths.LOCAL_CONFIG_PATH == "./local/config"

    def test_schema_paths_are_under_schemas_directory(self):
        assert FrameworkPaths.MAIN_SPEC_SCHEMA_PATH.endswith("main.json")
        assert FrameworkPaths.TEMPLATE_SPEC_SCHEMA_PATH.endswith("spec_template.json")


class TestPipelineBundlePaths:
    def test_dataflow_spec_path_segment(self):
        assert PipelineBundlePaths.DATAFLOW_SPEC_PATH == "dataflowspec"

    def test_template_path(self):
        assert PipelineBundlePaths.TEMPLATE_PATH == "./templates"


class TestSupportedSpecFormat:
    def test_json_and_yaml_values(self):
        assert SupportedSpecFormat.JSON.value == "json"
        assert SupportedSpecFormat.YAML.value == "yaml"


class TestSuffixConstants:
    def test_json_main_spec_suffix_is_usable_by_get_format_suffixes(self):
        from lakeflow_framework.utility import get_format_suffixes

        # Dataclass stores a parenthesized string, not a 1-tuple — use get_format_suffixes.
        assert get_format_suffixes("json", "main_spec") == ["_main.json"]


class TestSystemColumns:
    def test_cdf_column_values(self):
        values = {c.value for c in SystemColumns.CDFColumns}
        assert "_change_type" in values
        assert "_commit_version" in values
