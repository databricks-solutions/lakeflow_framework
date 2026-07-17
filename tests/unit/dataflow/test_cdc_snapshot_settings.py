"""Unit tests for CDC snapshot settings and version parsing."""

from __future__ import annotations

from datetime import datetime

import pyspark.sql.types as T
import pytest

from lakeflow_framework.dataflow.cdc_snapshot import (
    CDCSnapshotFlow,
    CDCSnapshotSettings,
    CDCSnapshotSourceTypes,
    CDCSnapshotTypes,
    CDCSnapshotVersionTypes,
    VersionInfo,
)


class TestVersionInfo:
    def test_formatted_value_for_integer(self):
        info = VersionInfo(raw_value=42, version_type=CDCSnapshotVersionTypes.INTEGER)
        assert info.formatted_value == "42"

    def test_formatted_value_for_timestamp_with_custom_format(self):
        info = VersionInfo(
            raw_value=datetime(2024, 1, 15, 10, 30, 45),
            version_type=CDCSnapshotVersionTypes.TIMESTAMP,
            datetime_format="%Y-%m-%d",
        )
        assert info.formatted_value == "2024-01-15"

    def test_formatted_value_truncates_microseconds_when_mask_configured(self):
        info = VersionInfo(
            raw_value=datetime(2024, 1, 15, 10, 30, 45, 123456),
            version_type=CDCSnapshotVersionTypes.TIMESTAMP,
            datetime_format="%Y-%m-%d %H:%M:%S.%f",
            micro_second_mask_length=3,
        )
        assert info.formatted_value == "2024-01-15 10:30:45.123"

    def test_sql_formatted_value_quotes_timestamp(self):
        info = VersionInfo(
            raw_value=datetime(2024, 1, 15, 10, 30, 45),
            version_type=CDCSnapshotVersionTypes.TIMESTAMP,
        )
        assert info.sql_formatted_value == "'2024-01-15 10:30:45'"

    def test_sql_formatted_value_quotes_integer(self):
        info = VersionInfo(raw_value=7, version_type=CDCSnapshotVersionTypes.INTEGER)
        assert info.sql_formatted_value == "'7'"

    def test_sql_formatted_value_rejects_unsupported_type(self):
        info = VersionInfo(raw_value="v1", version_type="string")
        with pytest.raises(ValueError, match="Unsupported version type"):
            _ = info.sql_formatted_value


class TestCDCSnapshotSettings:
    def test_historical_snapshot_requires_source(self):
        with pytest.raises(ValueError, match="Source is required"):
            CDCSnapshotSettings(
                keys=["id"],
                scd_type="1",
                snapshotType=CDCSnapshotTypes.HISTORICAL,
            )

    def test_get_source_returns_file_source(self):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={"format": "parquet", "path": "/data/{version}/", "versionType": "integer"},
        )
        source = settings.get_source()
        assert source.format == "parquet"
        assert source.path == "/data/{version}/"

    def test_get_source_returns_table_source(self):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.TABLE,
            source={"table": "snapshots", "versionColumn": "version", "versionType": "integer"},
        )
        source = settings.get_source()
        assert source.table == "snapshots"
        assert source.versionColumn == "version"

    def test_get_source_rejects_unknown_source_type(self):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.PERIODIC,
            sourceType="kafka",
            source={},
        )
        with pytest.raises(ValueError, match="Unsupported source type"):
            settings.get_source()

    def test_is_historical_and_is_file_source(self):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={"format": "parquet", "path": "/data/", "versionType": "integer"},
        )
        assert settings.is_historical() is True
        assert settings.is_file_source() is True

    def test_scd_type_two_sets_integer_sequence_for_integer_versions(self):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="2",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={"format": "parquet", "path": "/data/", "versionType": "integer"},
        )
        assert settings.sequence_by_data_type == T.IntegerType()

    def test_scd_type_two_defaults_to_timestamp_sequence_for_non_integer_versions(self):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="2",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={"format": "parquet", "path": "/data/", "versionType": "timestamp"},
        )
        assert settings.sequence_by_data_type == T.TimestampType()


class TestCDCSnapshotFlowParsing:
    @pytest.fixture
    def file_snapshot_flow(self, pipeline_context):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={
                "format": "parquet",
                "path": "/data/{version}/part-{fragment}.parquet",
                "versionType": CDCSnapshotVersionTypes.INTEGER,
            },
        )
        return CDCSnapshotFlow(settings)

    def test_path_to_regex_pattern_converts_curly_placeholders(self, file_snapshot_flow):
        pattern = file_snapshot_flow._path_to_regex_pattern("/data/{version}/part-{fragment}.parquet")
        assert "(?P<version_main>.+)" in pattern
        assert "(?P<fragment>.*?)" in pattern

    def test_path_to_regex_pattern_preserves_existing_named_groups(self, file_snapshot_flow):
        regex_path = "/data/(?P<version_main>\\d+)/file.parquet"
        assert file_snapshot_flow._path_to_regex_pattern(regex_path) == regex_path

    def test_get_version_string_from_match_concatenates_version_groups(self, file_snapshot_flow):
        import re

        match = re.match(r"(?P<version_year>\d{4})(?P<version_month>\d{2})", "202401")
        assert file_snapshot_flow._get_version_string_from_match(match) == "202401"

    def test_get_dynamic_path_index_finds_first_placeholder_segment(self, file_snapshot_flow):
        index = file_snapshot_flow._get_dynamic_path_index("/lake/bronze/{version}/data.parquet")
        assert index == 3

    def test_extract_version_from_filename_parses_integer_version(self, file_snapshot_flow):
        info = file_snapshot_flow._extract_version_from_filename(
            "42/part-a.parquet",
            "{version}/part-{fragment}.parquet",
        )
        assert info is not None
        assert info.raw_value == 42
        assert info.version_type == CDCSnapshotVersionTypes.INTEGER

    def test_extract_version_from_filename_returns_none_when_pattern_does_not_match(
        self, file_snapshot_flow
    ):
        assert (
            file_snapshot_flow._extract_version_from_filename(
                "unexpected.parquet",
                "{version}/part-{fragment}.parquet",
            )
            is None
        )


class TestCDCSnapshotSortedVersions:
    @pytest.fixture
    def file_snapshot_flow(self, pipeline_context):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={
                "format": "parquet",
                "path": "/data/{version}/",
                "versionType": CDCSnapshotVersionTypes.INTEGER,
            },
        )
        return CDCSnapshotFlow(settings)

    def test_sorted_versions_orders_by_raw_value(self, file_snapshot_flow):
        file_snapshot_flow._available_versions = [
            VersionInfo(3, CDCSnapshotVersionTypes.INTEGER),
            VersionInfo(1, CDCSnapshotVersionTypes.INTEGER),
            VersionInfo(2, CDCSnapshotVersionTypes.INTEGER),
        ]
        assert [v.raw_value for v in file_snapshot_flow.sorted_versions] == [1, 2, 3]

    def test_version_values_derived_from_sorted_versions(self, file_snapshot_flow):
        file_snapshot_flow._available_versions = [
            VersionInfo(2, CDCSnapshotVersionTypes.INTEGER),
            VersionInfo(1, CDCSnapshotVersionTypes.INTEGER),
        ]
        assert file_snapshot_flow.version_values == [1, 2]
