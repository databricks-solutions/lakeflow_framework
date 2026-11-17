"""Unit tests for CDC snapshot settings and version parsing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

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


class TestCDCSnapshotFileListing:
    @pytest.fixture
    def data_dir(self, tmp_path):
        d = tmp_path / "snapshots"
        d.mkdir()
        return d

    @pytest.fixture
    def file_snapshot_flow(self, pipeline_context, data_dir):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={
                "format": "csv",
                "path": f"{data_dir}/customer_{{version}}.csv",
                "versionType": CDCSnapshotVersionTypes.INTEGER,
            },
        )
        return CDCSnapshotFlow(settings)

    def test_fuse_lists_flat_directory(self, file_snapshot_flow, data_dir):
        (data_dir / "customer_1.csv").write_text("id\n1\n")
        (data_dir / "customer_2.csv").write_text("id\n2\n")
        listed = file_snapshot_flow._list_files_fuse(str(data_dir), recursive=False)
        names = sorted(entry.name for entry in listed)
        assert names == ["customer_1.csv", "customer_2.csv"]

    def test_fuse_skips_descending_into_parquet_directories(
        self, file_snapshot_flow, data_dir
    ):
        parquet_dir = data_dir / "snap.parquet"
        parquet_dir.mkdir()
        (parquet_dir / "part-0000.parquet").write_text("x")
        (data_dir / "other.csv").write_text("id\n1\n")

        listed = file_snapshot_flow._list_files_fuse(str(data_dir), recursive=True)
        names = {entry.name for entry in listed}
        assert "snap.parquet" in names
        assert "other.csv" in names
        assert "part-0000.parquet" not in names

    def test_get_listed_files_caches_single_listing(self, file_snapshot_flow, data_dir):
        (data_dir / "customer_1.csv").write_text("id\n1\n")
        calls = {"n": 0}
        original = file_snapshot_flow._list_files

        def counting_list(path, recursive=True):
            calls["n"] += 1
            return original(path, recursive=recursive)

        file_snapshot_flow._list_files = counting_list  # type: ignore[method-assign]
        first = file_snapshot_flow._get_listed_files(str(data_dir), recursive=False)
        second = file_snapshot_flow._get_listed_files(str(data_dir), recursive=False)
        assert calls["n"] == 1
        assert first is second

    def test_available_file_versions_indexes_paths_for_read(
        self, file_snapshot_flow, data_dir
    ):
        (data_dir / "customer_1.csv").write_text("id\n1\n")
        (data_dir / "customer_2.csv").write_text("id\n2\n")
        versions = file_snapshot_flow._get_available_file_versions(None)
        assert sorted(v.raw_value for v in versions) == [1, 2]
        assert file_snapshot_flow._version_paths is not None
        assert any(
            p.endswith("customer_1.csv")
            for p in file_snapshot_flow._version_paths["1"]
        )
        # Second listing should be a cache hit
        calls = {"n": 0}
        original = file_snapshot_flow._list_files

        def counting_list(path, recursive=True):
            calls["n"] += 1
            return original(path, recursive=recursive)

        file_snapshot_flow._list_files = counting_list  # type: ignore[method-assign]
        file_snapshot_flow._get_listed_files(str(data_dir), recursive=False)
        assert calls["n"] == 0


class TestCDCSnapshotMultiFileRead:
    @pytest.fixture
    def data_dir(self, tmp_path):
        d = tmp_path / "multi_frag"
        d.mkdir()
        return d

    @pytest.fixture
    def file_snapshot_flow(self, pipeline_context, data_dir):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={
                "format": "csv",
                "path": f"{data_dir}/{{version}}_FINAL_{{fragment}}.csv",
                "versionType": CDCSnapshotVersionTypes.INTEGER,
                "readerOptions": {"header": "true", "inferSchema": "false"},
            },
        )
        return CDCSnapshotFlow(settings)

    def test_read_snapshot_dataframe_loads_all_fragments_in_one_call(
        self, file_snapshot_flow, data_dir, monkeypatch
    ):
        from lakeflow_framework.dataflow import cdc_snapshot as cdc_mod
        from lakeflow_framework.dataflow.dataflow_config import DataFlowConfig
        from lakeflow_framework.dataflow.features import Features

        p1 = data_dir / "1_FINAL_a.csv"
        p2 = data_dir / "1_FINAL_b.csv"
        p1.write_text("id\n1\n")
        p2.write_text("id\n2\n")

        captured = {}

        class FakeBatchFiles:
            def __init__(self, **kwargs):
                captured["kwargs"] = kwargs

            def read_source(self, read_config):
                captured["read_config"] = read_config
                return "fake-df"

        monkeypatch.setattr(cdc_mod, "SourceBatchFiles", FakeBatchFiles)

        file_snapshot_flow._version_paths = {
            "1": [str(p2), str(p1)],  # unsorted on purpose
        }
        version = VersionInfo(1, CDCSnapshotVersionTypes.INTEGER)
        df = file_snapshot_flow._read_snapshot_dataframe(
            version,
            DataFlowConfig(features=Features()),
            target_config_flags=[],
        )

        assert df == "fake-df"
        assert captured["kwargs"]["path"] == [str(p1), str(p2)]
        assert captured["kwargs"]["format"] == "csv"

    def test_read_snapshot_dataframe_uses_string_path_for_single_file(
        self, file_snapshot_flow, data_dir, monkeypatch
    ):
        from lakeflow_framework.dataflow import cdc_snapshot as cdc_mod
        from lakeflow_framework.dataflow.dataflow_config import DataFlowConfig
        from lakeflow_framework.dataflow.features import Features

        p1 = data_dir / "1_FINAL_a.csv"
        p1.write_text("id\n1\n")

        captured = {}

        class FakeBatchFiles:
            def __init__(self, **kwargs):
                captured["kwargs"] = kwargs

            def read_source(self, read_config):
                return "fake-df"

        monkeypatch.setattr(cdc_mod, "SourceBatchFiles", FakeBatchFiles)
        file_snapshot_flow._version_paths = {"1": [str(p1)]}
        df = file_snapshot_flow._read_snapshot_dataframe(
            VersionInfo(1, CDCSnapshotVersionTypes.INTEGER),
            DataFlowConfig(features=Features()),
            target_config_flags=[],
        )
        assert df == "fake-df"
        assert captured["kwargs"]["path"] == str(p1)


@dataclass
class _FakeFileInfo:
    """dbutils.fs.FileInfo stand-in for listing equivalence tests."""

    path: str
    name: str
    is_dir: bool = False

    def isDir(self) -> bool:
        return self.is_dir


@dataclass
class _FakeRow:
    path: str
    length: int = 0
    modificationTime: int = 0


class _FakeDF:
    """Minimal DataFrame stand-in: rows + union/isEmpty for equivalence checks."""

    def __init__(self, rows: List[tuple]):
        self._rows = list(rows)

    def union(self, other: "_FakeDF") -> "_FakeDF":
        return _FakeDF(self._rows + other._rows)

    def isEmpty(self) -> bool:
        return len(self._rows) == 0

    def sorted_rows(self) -> List[tuple]:
        return sorted(self._rows)


def _csv_rows(path: str) -> List[tuple]:
    text = Path(path).read_text().strip().splitlines()
    # header + data rows; keep body as tuples of cells
    return [tuple(line.split(",")) for line in text[1:]]


class _ContentBatchFiles:
    """SourceBatchFiles stand-in that materializes CSV body rows (no Spark)."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def read_source(self, read_config):
        path = self.kwargs["path"]
        if isinstance(path, list):
            rows: List[tuple] = []
            for p in path:
                rows.extend(_csv_rows(p))
            return _FakeDF(rows)
        return _FakeDF(_csv_rows(path))


def _dbutils_ls_from_posix(path: str):
    entries = []
    for name in sorted(Path(path).iterdir()):
        entries.append(
            _FakeFileInfo(
                path=str(name),
                name=name.name,
                is_dir=name.is_dir(),
            )
        )
    return entries


def _spark_binary_rows(root: str, recursive: bool) -> List[_FakeRow]:
    root_path = Path(root)
    if recursive:
        files = sorted(p for p in root_path.rglob("*") if p.is_file())
    else:
        files = sorted(p for p in root_path.iterdir() if p.is_file())
    return [_FakeRow(path=str(p)) for p in files]


def _force_single_lister(flow: CDCSnapshotFlow, monkeypatch, which: str) -> None:
    """Make ``_list_files`` succeed only via the named strategy.

    Always rebinds all three methods so prior monkeypatches do not leak
    across strategy iterations in the same test.
    """
    attrs = {
        "fuse": "_list_files_fuse",
        "dbutils": "_list_files_dbutils",
        "spark": "_list_files_spark",
    }
    for name, attr in attrs.items():
        if name == which:
            monkeypatch.setattr(
                flow, attr, getattr(CDCSnapshotFlow, attr).__get__(flow, CDCSnapshotFlow)
            )
            continue

        def _failing(*_a, _label=name, **_k):
            raise OSError(f"skip {_label}")

        monkeypatch.setattr(flow, attr, _failing)


def _reset_listing_cache(flow: CDCSnapshotFlow) -> None:
    flow._listed_files = None
    flow._listed_files_key = None
    flow._version_paths = None
    flow._available_versions = None
    flow._sorted_versions = None
    flow._version_values = None


def _version_discovery_fingerprint(flow: CDCSnapshotFlow):
    versions = flow._get_available_file_versions(None)
    version_values = sorted(v.raw_value for v in versions)
    paths = {
        ver: sorted(Path(p).name for p in paths)
        for ver, paths in (flow._version_paths or {}).items()
    }
    return version_values, paths


class TestCDCSnapshotListingEquivalence:
    """FUSE / dbutils / Spark listing must agree on versions and fragment paths."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        d = tmp_path / "equiv_snapshots"
        d.mkdir()
        # Multi-fragment versions + an extra version for ordering / startingVersion
        (d / "1_FINAL_a.csv").write_text("id,name\n1,a\n")
        (d / "1_FINAL_b.csv").write_text("id,name\n2,b\n")
        (d / "2_FINAL_a.csv").write_text("id,name\n1,a2\n")
        (d / "3_FINAL_a.csv").write_text("id,name\n3,c\n")
        return d

    @pytest.fixture
    def file_snapshot_flow(self, pipeline_context, data_dir):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={
                "format": "csv",
                "path": f"{data_dir}/{{version}}_FINAL_{{fragment}}.csv",
                "versionType": CDCSnapshotVersionTypes.INTEGER,
                "startingVersion": 1,
                "readerOptions": {"header": "true"},
            },
        )
        return CDCSnapshotFlow(settings)

    def _wire_dbutils(self, pipeline_context, monkeypatch):
        dbutils = pipeline_context["dbutils"]
        dbutils.fs.ls = MagicMock(side_effect=_dbutils_ls_from_posix)
        monkeypatch.setattr(
            "lakeflow_framework.dataflow.cdc_snapshot.pipeline_config.get_dbutils",
            lambda: dbutils,
        )

    def _wire_spark(self, pipeline_context, monkeypatch, data_dir):
        spark = pipeline_context["spark"]
        state = {"recursive": False}

        def _load(path):
            rows = _spark_binary_rows(path, recursive=state["recursive"])
            select = MagicMock()
            select.collect.return_value = rows
            result = MagicMock()
            result.select.return_value = select
            return result

        def _option(key, value):
            if key == "recursiveFileLookup":
                state["recursive"] = str(value).lower() == "true"
            return reader

        reader = MagicMock()
        reader.option.side_effect = _option
        reader.load.side_effect = _load
        spark.read.format.return_value = reader
        monkeypatch.setattr(
            "lakeflow_framework.dataflow.cdc_snapshot.pipeline_config.get_spark",
            lambda: spark,
        )

    def test_fuse_dbutils_spark_agree_on_versions_and_paths(
        self, file_snapshot_flow, data_dir, pipeline_context, monkeypatch
    ):
        self._wire_dbutils(pipeline_context, monkeypatch)
        self._wire_spark(pipeline_context, monkeypatch, data_dir)

        fingerprints = {}
        for which in ("fuse", "dbutils", "spark"):
            _reset_listing_cache(file_snapshot_flow)
            _force_single_lister(file_snapshot_flow, monkeypatch, which)
            fingerprints[which] = _version_discovery_fingerprint(file_snapshot_flow)

        assert fingerprints["fuse"] == fingerprints["dbutils"] == fingerprints["spark"]
        version_values, paths = fingerprints["fuse"]
        assert version_values == [1, 2, 3]
        assert paths["1"] == ["1_FINAL_a.csv", "1_FINAL_b.csv"]
        assert paths["2"] == ["2_FINAL_a.csv"]
        assert paths["3"] == ["3_FINAL_a.csv"]


class TestCDCSnapshotMultiFragmentReadEquivalence:
    """Single multi-path load must match legacy per-file load + union content."""

    @pytest.fixture
    def data_dir(self, tmp_path):
        d = tmp_path / "union_equiv"
        d.mkdir()
        (d / "1_FINAL_a.csv").write_text("id,name\n1,a\n")
        (d / "1_FINAL_b.csv").write_text("id,name\n2,b\n")
        return d

    @pytest.fixture
    def file_snapshot_flow(self, pipeline_context, data_dir):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={
                "format": "csv",
                "path": f"{data_dir}/{{version}}_FINAL_{{fragment}}.csv",
                "versionType": CDCSnapshotVersionTypes.INTEGER,
                "readerOptions": {"header": "true", "inferSchema": "false"},
            },
        )
        return CDCSnapshotFlow(settings)

    def test_multipath_load_matches_legacy_union_rows(
        self, file_snapshot_flow, data_dir, monkeypatch
    ):
        from lakeflow_framework.dataflow import cdc_snapshot as cdc_mod
        from lakeflow_framework.dataflow.dataflow_config import DataFlowConfig
        from lakeflow_framework.dataflow.features import Features

        p1 = data_dir / "1_FINAL_a.csv"
        p2 = data_dir / "1_FINAL_b.csv"
        files_to_read = sorted([str(p1), str(p2)])
        file_snapshot_flow._version_paths = {"1": [str(p2), str(p1)]}

        monkeypatch.setattr(cdc_mod, "SourceBatchFiles", _ContentBatchFiles)
        cfg = DataFlowConfig(features=Features())
        version = VersionInfo(1, CDCSnapshotVersionTypes.INTEGER)

        multi_df = file_snapshot_flow._read_snapshot_dataframe(
            version, cfg, target_config_flags=[]
        )

        # Legacy behaviour: sorted per-file load + union
        legacy_df = None
        for file_path in files_to_read:
            file_df = _ContentBatchFiles(
                path=file_path,
                format="csv",
                readerOptions={"header": "true", "inferSchema": "false"},
            ).read_source(None)
            legacy_df = file_df if legacy_df is None else legacy_df.union(file_df)

        assert multi_df.sorted_rows() == legacy_df.sorted_rows()
        assert multi_df.sorted_rows() == [("1", "a"), ("2", "b")]


class TestCDCSnapshotSequenceContract:
    """``_next_snapshot_and_version`` ordering and empty-version stop behaviour."""

    @pytest.fixture
    def file_snapshot_flow(self, pipeline_context, tmp_path):
        settings = CDCSnapshotSettings(
            keys=["id"],
            scd_type="1",
            snapshotType=CDCSnapshotTypes.HISTORICAL,
            sourceType=CDCSnapshotSourceTypes.FILE,
            source={
                "format": "csv",
                "path": f"{tmp_path}/{{version}}.csv",
                "versionType": CDCSnapshotVersionTypes.INTEGER,
            },
        )
        return CDCSnapshotFlow(settings)

    def test_versions_returned_in_ascending_order(
        self, file_snapshot_flow, monkeypatch
    ):
        from lakeflow_framework.dataflow.dataflow_config import DataFlowConfig
        from lakeflow_framework.dataflow.features import Features

        file_snapshot_flow._available_versions = [
            VersionInfo(3, CDCSnapshotVersionTypes.INTEGER),
            VersionInfo(1, CDCSnapshotVersionTypes.INTEGER),
            VersionInfo(2, CDCSnapshotVersionTypes.INTEGER),
        ]

        def _read(version_info, *_a, **_k):
            return _FakeDF([(str(version_info.raw_value),)])

        monkeypatch.setattr(file_snapshot_flow, "_read_snapshot_dataframe", _read)
        cfg = DataFlowConfig(features=Features())

        seen = []
        latest = None
        while True:
            result = file_snapshot_flow._next_snapshot_and_version(
                latest, cfg, target_config_flags=[]
            )
            if result is None:
                break
            _df, raw = result
            seen.append(raw)
            latest = raw

        assert seen == [1, 2, 3]

    def test_empty_version_stops_sequence_not_skips(
        self, file_snapshot_flow, monkeypatch
    ):
        from lakeflow_framework.dataflow.dataflow_config import DataFlowConfig
        from lakeflow_framework.dataflow.features import Features

        file_snapshot_flow._available_versions = [
            VersionInfo(1, CDCSnapshotVersionTypes.INTEGER),
            VersionInfo(2, CDCSnapshotVersionTypes.INTEGER),
            VersionInfo(3, CDCSnapshotVersionTypes.INTEGER),
        ]

        def _read(version_info, *_a, **_k):
            if version_info.raw_value == 2:
                return _FakeDF([])
            return _FakeDF([(str(version_info.raw_value),)])

        monkeypatch.setattr(file_snapshot_flow, "_read_snapshot_dataframe", _read)
        cfg = DataFlowConfig(features=Features())

        first = file_snapshot_flow._next_snapshot_and_version(
            None, cfg, target_config_flags=[]
        )
        assert first is not None and first[1] == 1

        # Empty version 2 ends the stream (does not advance to 3).
        second = file_snapshot_flow._next_snapshot_and_version(
            1, cfg, target_config_flags=[]
        )
        assert second is None
