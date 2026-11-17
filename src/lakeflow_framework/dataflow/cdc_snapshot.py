import bisect
from dataclasses import dataclass, field
from datetime import datetime
import os
import re
from typing import Dict, List, Literal, Optional, Tuple, Union

from pyspark import pipelines as dp
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
import pyspark.sql.types as T

import pipeline_config

from .dataflow_config import DataFlowConfig
from .sources import SourceDelta, SourceBatchFiles, ReadConfig


@dataclass
class _ListedPath:
    """Minimal file listing entry shared across FUSE / dbutils / Spark discovery."""

    path: str
    name: str
    size: int = 0
    modificationTime: int = 0
    is_dir: bool = False

    def isDir(self) -> bool:
        """Match ``dbutils.fs.FileInfo.isDir()`` for shared recursive helpers."""
        return self.is_dir


@dataclass(frozen=True)
class CDCSnapshotTypes:
    """Constants for the types of CDC Snapshot."""
    HISTORICAL = "historical"
    PERIODIC = "periodic"


@dataclass(frozen=True)
class CDCSnapshotSourceTypes:
    """Constants for the types of CDC Snapshot source types."""
    FILE = "file"
    TABLE = "table"


@dataclass(frozen=True)
class CDCSnapshotVersionTypes:
    """Constants for the types of CDC Snapshot version types."""
    DATE = "date"
    INTEGER = "integer"
    LONG = "long"
    TIMESTAMP = "timestamp"


@dataclass(frozen=True)
class DeduplicateMode:
    """Deduplication strategy for CDC snapshot source data.
    - off: no deduplication (default).
    - full_row: deduplicate based on the full row using dropDuplicates(); deterministic as the full row is deduplicated.
    - keys_only: deduplicate based on the keys using dropDuplicates(keys); non-deterministic as it preserves the first row per key(s) without ordering on any other columns."""
    OFF = "off"
    FULL_ROW = "full_row"
    KEYS_ONLY = "keys_only"


@dataclass
class VersionInfo:
    """A structure to hold version information with both raw and formatted values."""
    raw_value: Union[str, int, datetime]
    version_type: str
    datetime_format: Optional[str] = None
    micro_second_mask_length: Optional[int] = None

    @property
    def formatted_value(self) -> str:
        """Get formatted value based on version type and datetime format."""
        if self.version_type == CDCSnapshotVersionTypes.TIMESTAMP:
            if isinstance(self.raw_value, datetime):
                if self.datetime_format:
                    if '%f' in self.datetime_format and self.micro_second_mask_length:
                        truncate_from_right = 6 - self.micro_second_mask_length
                        return self.raw_value.strftime(self.datetime_format)[:-truncate_from_right]
                    else:
                        return self.raw_value.strftime(self.datetime_format)
                else:
                    return self.raw_value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return str(self.raw_value)
        else:
            return str(self.raw_value)

    @property
    def sql_formatted_value(self) -> str:
        """Get SQL formatted value with appropriate quotes."""
        if self.version_type in [CDCSnapshotVersionTypes.TIMESTAMP, CDCSnapshotVersionTypes.DATE]:
            return f"'{self.formatted_value}'"
        elif self.version_type in [CDCSnapshotVersionTypes.INTEGER, CDCSnapshotVersionTypes.LONG]:
            return f"'{self.formatted_value}'"
        else:
            raise ValueError(f"Unsupported version type: {self.version_type}")

@dataclass
class FilePathInfo:
    """A structure to hold file path information."""
    full_path: str
    filename_with_version_path: str

@dataclass
class CDCSnapshotFileSource:
    """A structure to hold the source configuration for CDC Snapshot."""
    format: str
    path: str
    readerOptions: Dict = field(default_factory=dict)
    filter: Optional[str] = None
    versionType: Optional[str] = None
    startingVersion: Optional[Union[int, str]] = None
    datetimeFormat: Optional[str] = None
    microSecondMaskLength: Optional[int] = None
    schemaPath: Optional[str] = None
    selectExp: Optional[List[str]] = None
    recursiveFileLookup: bool = False
    deduplicateMode: Optional[
        Literal[
            DeduplicateMode.OFF,
            DeduplicateMode.FULL_ROW,
            DeduplicateMode.KEYS_ONLY,
        ]
    ] = DeduplicateMode.OFF


@dataclass
class CDCSnapshotTableSource:
    """A structure to hold the source configuration for CDC Snapshot."""
    table: str
    versionColumn: str
    versionType: str
    startingVersion: Optional[Union[int, str]] = None
    selectExp: Optional[List[str]] = None
    deduplicateMode: Optional[
        Literal[
            DeduplicateMode.OFF,
            DeduplicateMode.FULL_ROW,
            DeduplicateMode.KEYS_ONLY,
        ]
    ] = DeduplicateMode.OFF


@dataclass
class CDCSnapshotSettings:
    """CDC Settings for the SDP auto CDC Snapshot API."""
    keys: List[str]
    scd_type: str
    snapshotType: str
    sourceType: str = None
    source: Dict = field(default_factory=dict)
    track_history_column_list: Optional[List[str]] = None
    track_history_except_column_list: Optional[List[str]] = None
    sequence_by_data_type: T.DataType = None

    def __post_init__(self):
        if self.snapshotType == CDCSnapshotTypes.HISTORICAL and not self.source:
            raise ValueError("Source is required for Historical CDC from Snapshot")

        if self.scd_type == "2":
            # TODO: implement dynamic sequence by type
            self.sequence_by_data_type = T.TimestampType()

            if self.snapshotType == CDCSnapshotTypes.HISTORICAL:
                version_type = self.get_source().versionType
                if version_type == CDCSnapshotVersionTypes.INTEGER:
                    self.sequence_by_data_type = T.IntegerType()

    def get_source(self) -> Optional[CDCSnapshotFileSource]:
        """Get source configuration for CDC from Snapshot."""
        if self.sourceType == CDCSnapshotSourceTypes.FILE:
            return CDCSnapshotFileSource(**self.source)
        elif self.sourceType == CDCSnapshotSourceTypes.TABLE:
            return CDCSnapshotTableSource(**self.source)
        else:
            raise ValueError(f"Unsupported source type: {self.sourceType}")

    def is_historical(self) -> bool:
        """Is the CDC snapshot type historical."""
        return self.snapshotType == CDCSnapshotTypes.HISTORICAL

    def is_file_source(self) -> bool:
        """Is the CDC snapshot source type file."""
        return self.sourceType == CDCSnapshotSourceTypes.FILE


class CDCSnapshotFlow:
    """A class to create a CDC Snapshot flow."""

    def __init__(self, settings: CDCSnapshotSettings):
        self.settings = settings
        self.logger = pipeline_config.get_logger()

        # Core CDC settings
        self.keys = settings.keys
        self.scd_type = settings.scd_type
        self.snapshotType = settings.snapshotType
        self.track_history_column_list = settings.track_history_column_list
        self.track_history_except_column_list = settings.track_history_except_column_list
        self.sequence_by_data_type = settings.sequence_by_data_type

        # Historical snapshot specific settings
        self.sourceType = None
        self.source = None
        if self.snapshotType == CDCSnapshotTypes.HISTORICAL:
            self.sourceType = settings.sourceType
            self.source = settings.get_source()

            if self.source is None:
                raise ValueError("Source configuration is required for historical snapshots")

        # Cached version data (per pipeline update / flow instance)
        self._available_versions: Optional[List[VersionInfo]] = None
        self._sorted_versions: Optional[List[VersionInfo]] = None
        self._version_values: Optional[List[Union[int, datetime]]] = None
        # Cached file listing for historical file sources — avoids re-listing
        # once for version discovery and again for every version read.
        self._listed_files_key: Optional[Tuple[str, bool]] = None
        self._listed_files: Optional[List] = None
        self._version_paths: Optional[Dict[str, List[str]]] = None

    @property
    def sorted_versions(self) -> List[VersionInfo]:
        """Get sorted versions."""
        if self._sorted_versions is None and self._available_versions:
            self._sorted_versions = sorted(self._available_versions, key=lambda x: x.raw_value)
        return self._sorted_versions or []

    @property
    def version_values(self) -> List[Union[int, datetime]]:
        """Get version values."""
        if self._version_values is None:
            self._version_values = [v.raw_value for v in self.sorted_versions]
        return self._version_values

    def _deduplicate_by_keys(self, df: DataFrame) -> DataFrame:
        """Deduplicate by configured keys, retaining first row per key. WARNING: This is non-deterministic."""
        self.logger.warning(
            "CDC Snapshot: deduplicateMode=keys_only is non-deterministic as it peserves the first row per key."
        )
        return df.dropDuplicates(self.keys)

    def _deduplicate_full_row(self, df: DataFrame) -> DataFrame:
        """Deduplicate by full row besides metadata column if present."""
        columns_to_deduplicate_on = [col for col in df.columns if col not in ["_metadata"]]
        return df.dropDuplicates(columns_to_deduplicate_on)

    def create(
        self,
        dataflow_config: DataFlowConfig,
        target_table: str,
        source_view_name: Optional[str] = None,
        target_config_flags: Optional[List[str]] = None,
        flow_name: Optional[str] = None # TODO: Add flow name
    ) -> None:
        """Create CDC from snapshot flow.

        Args:
            dataflow_config: DataFlow configuration
            target_table: Name of the target table
            source_view_name: Name of the source view
            flow_name: Optional name for the flow
        """
        self.logger.debug(f"CDC From Snapshot: {self.source}")

        try:
            if self.snapshotType == CDCSnapshotTypes.PERIODIC:
                self._apply_periodic_changes(target_table, source_view_name)
            elif self.snapshotType == CDCSnapshotTypes.HISTORICAL:
                self._apply_historical_changes(target_table, dataflow_config, target_config_flags)
            else:
                raise ValueError(f"Unsupported snapshot type: {self.snapshotType}")
        except Exception as e:
            self.logger.error(f"Failed to create CDC snapshot flow: {e}")
            raise

    def _apply_periodic_changes(self, target_table: str, source_view_name: str) -> None:
        """Apply periodic changes from snapshot."""
        dp.create_auto_cdc_from_snapshot_flow(
            target=target_table,
            source=source_view_name,
            keys=self.keys,
            stored_as_scd_type=self.scd_type,
            track_history_column_list=self.track_history_column_list,
            track_history_except_column_list=self.track_history_except_column_list
        )

    def _apply_historical_changes(self, target_table: str, dataflow_config: DataFlowConfig, target_config_flags: Optional[List[str]] = None):
        """Apply historical changes from snapshot."""
        dp.create_auto_cdc_from_snapshot_flow(
            target=target_table,
            snapshot_and_version=lambda version: self._next_snapshot_and_version(version, dataflow_config, target_config_flags),
            keys=self.keys,
            stored_as_scd_type=self.scd_type,
            track_history_column_list=self.track_history_column_list,
            track_history_except_column_list=self.track_history_except_column_list
        )

    def _next_snapshot_and_version(self, latest_snapshot_version, dataflow_config: DataFlowConfig, target_config_flags: Optional[List[str]] = None):
        """Get the next snapshot and version."""
        try:
            if self._available_versions is None:
                self._available_versions = self._get_available_versions(latest_snapshot_version)

            if not self._available_versions:
                self.logger.warning("CDC Snapshot: No valid versions found")
                return None

            version_info = self._get_next_version(latest_snapshot_version)
            if version_info is None:
                self.logger.debug("CDC Snapshot: Retrieving next version was None")
                return None

            self.logger.info(f"CDC Snapshot: Reading file version: {version_info.formatted_value}")
            df = self._read_snapshot_dataframe(version_info, dataflow_config, target_config_flags)
            if df is None or df.isEmpty():
                self.logger.debug("CDC Snapshot: Retrieving snapshot dataframe was None or empty")
                return None

            self.logger.info(f"CDC Snapshot: Returning dataframe with version: {version_info.formatted_value}. Raw version: {version_info.raw_value}.")
            return (df, version_info.raw_value)

        except Exception as e:
            self.logger.error(f"CDC Snapshot: Error processing snapshots: {e}", exc_info=True)
            raise


    def _get_available_versions(self, latest_snapshot_version: Optional[Union[int, datetime]]) -> List[VersionInfo]:
        """Get list of available versions from source."""
        if self.sourceType == CDCSnapshotSourceTypes.FILE:
            return self._get_available_file_versions(latest_snapshot_version)
        elif self.sourceType == CDCSnapshotSourceTypes.TABLE:
            return self._get_available_table_versions(latest_snapshot_version)
        else:
            raise ValueError(f"Unsupported source type: {self.sourceType}")
    
    @staticmethod
    def _posix_path(path: str) -> str:
        """Strip optional ``dbfs:`` scheme for local /Volumes FUSE access."""
        return path[5:] if path.startswith("dbfs:") else path

    @staticmethod
    def _with_caller_scheme(path: str, caller_path: str) -> str:
        """Preserve ``dbfs:`` prefix when the caller used it."""
        if caller_path.startswith("dbfs:") and not path.startswith("dbfs:"):
            return f"dbfs:{path}" if path.startswith("/") else f"dbfs:/{path}"
        if not caller_path.startswith("dbfs:") and path.startswith("dbfs:"):
            return path[5:]
        return path

    def _get_listed_files(self, path: str, recursive: bool = True) -> List:
        """List files once per (path, recursive) for this flow instance."""
        key = (path, recursive)
        if self._listed_files is not None and self._listed_files_key == key:
            self.logger.debug(
                "CDC Snapshot: Reusing cached file listing for '%s' (%s entries)",
                path,
                len(self._listed_files),
            )
            return self._listed_files
        files = self._list_files(path, recursive=recursive)
        self._listed_files_key = key
        self._listed_files = files
        return files

    def _list_files(self, path: str, recursive: bool = True) -> List:
        """List files for snapshot discovery.

        Order (fast → SEG-safe last resort):
        1. FUSE / POSIX ``os.listdir`` / ``os.walk`` (typical for ``/Volumes/...``)
        2. ``dbutils.fs.ls``
        3. Spark ``binaryFile`` + ``collect`` (works under SEG; expensive)

        Args:
            path: Directory path to list files from.
            recursive: If True, list files recursively.

        Returns:
            List of objects with a ``.path`` attribute per discovered entry.
        """
        attempts = (
            ("FUSE/POSIX", self._list_files_fuse),
            ("dbutils.fs.ls", self._list_files_dbutils),
            ("Spark binaryFile", self._list_files_spark),
        )
        errors: List[str] = []
        for label, lister in attempts:
            try:
                files = lister(path, recursive)
                self.logger.debug(
                    "CDC Snapshot: Listed %s entr(y/ies) under '%s' via %s",
                    len(files),
                    path,
                    label,
                )
                return files
            except Exception as exc:
                errors.append(f"{label}: {exc}")
                self.logger.warning(
                    "CDC Snapshot: %s listing failed at '%s' (%s). Trying next strategy.",
                    label,
                    path,
                    exc,
                )
        raise RuntimeError(
            "CDC Snapshot: All file listing strategies failed for "
            f"'{path}': {'; '.join(errors)}"
        )

    def _list_files_fuse(self, path: str, recursive: bool = True) -> List:
        """List via local filesystem (UC Volume FUSE mount when available)."""
        posix = self._posix_path(path)
        if not os.path.isdir(posix):
            raise FileNotFoundError(
                f"FUSE/POSIX path is not a directory or is not mounted: {posix}"
            )

        def _make(entry_posix: str, is_dir: bool) -> _ListedPath:
            normalized = self._with_caller_scheme(entry_posix, path)
            return _ListedPath(
                path=normalized,
                name=entry_posix.rstrip("/").rsplit("/", 1)[-1],
                is_dir=is_dir,
            )

        all_files: List[_ListedPath] = []
        if not recursive:
            for name in sorted(os.listdir(posix)):
                child = os.path.join(posix, name)
                all_files.append(_make(child, os.path.isdir(child)))
            return all_files

        for root, dirnames, filenames in os.walk(posix):
            # Match dbutils: do not recurse into directories whose name ends with .parquet
            parquet_dirs = [d for d in dirnames if d.endswith(".parquet")]
            dirnames[:] = [d for d in dirnames if not d.endswith(".parquet")]
            for dirname in dirnames:
                all_files.append(_make(os.path.join(root, dirname), True))
            for parquet_dir in parquet_dirs:
                all_files.append(_make(os.path.join(root, parquet_dir), True))
            for filename in filenames:
                all_files.append(_make(os.path.join(root, filename), False))

        return all_files

    def _list_files_dbutils(self, path: str, recursive: bool = True) -> List:
        """List via ``dbutils.fs.ls`` (may be blocked under SEG)."""
        dbutils = pipeline_config.get_dbutils()
        all_files = []
        for f in dbutils.fs.ls(path):
            all_files.append(f)
            if recursive and f.isDir() and not f.path.rstrip("/").endswith(".parquet"):
                all_files.extend(self._list_files_dbutils(f.path, recursive=True))
        return all_files

    def _list_files_spark(self, path: str, recursive: bool = True) -> List:
        """List via Spark ``binaryFile`` + ``collect`` (SEG-safe, expensive)."""
        spark = pipeline_config.get_spark()
        rows = (
            spark.read.format("binaryFile")
            .option("recursiveFileLookup", str(recursive).lower())
            .load(path)
            .select("path", "modificationTime", "length")
            .collect()
        )

        def _truncate_at_parquet_dir(p: str) -> str:
            segments = p.split("/")
            for i, seg in enumerate(segments[:-1]):
                if seg.endswith(".parquet"):
                    return "/".join(segments[: i + 1])
            return p

        seen_paths = set()
        files: List[_ListedPath] = []
        for row in rows:
            raw = row.path
            if path.startswith("dbfs:"):
                normalized = raw if raw.startswith("dbfs:") else f"dbfs:{raw}"
            else:
                normalized = raw[5:] if raw.startswith("dbfs:") else raw
            normalized = _truncate_at_parquet_dir(normalized)
            if normalized in seen_paths:
                continue
            seen_paths.add(normalized)
            files.append(
                _ListedPath(
                    path=normalized,
                    name=normalized.rstrip("/").rsplit("/", 1)[-1],
                    size=row.length,
                    modificationTime=row.modificationTime,
                )
            )
        return files

    def _path_to_regex_pattern(self, path: str) -> str:
        """Convert path to normalized regex pattern with named groups.

        Curly-brace syntax is converted to named capture groups:
        - {version} -> (?P<version_main>.+)  (single capture group for version)
        - {fragment} -> (?P<fragment>.*?)     (single capture group for fragment)

        If path already contains regex named groups (?P<version_ or (?P<fragment>,
        it is returned as-is (already a regex pattern).
        """
        if re.search(r'\(\?P<version_', path) or re.search(r'\(\?P<fragment>', path):
            return path
        if '{version}' not in path and '{fragment}' not in path:
            return path
        escaped = re.escape(path)
        normalized = (
            escaped
            .replace(r'\{version\}', r'(?P<version_main>.+)')
            .replace(r'\{fragment\}', r'(?P<fragment>.*?)')
        )
        return normalized

    def _get_dynamic_path_index(self, path: str) -> int:
        """Return index of first path segment that contains version or fragment (curly or regex)."""
        path_parts = path.split('/')
        for idx, part in enumerate(path_parts):
            if '{version}' in part or '{fragment}' in part:
                return idx
            if '(?P<version_' in part or '(?P<fragment>' in part:
                return idx
        raise ValueError(f"No version or fragment placeholder found in path: {path}")

    def _get_version_string_from_match(self, match: re.Match) -> Optional[str]:
        """From a regex match, concatenate all groups named version_* (sorted) to form version string."""
        groupdict = match.groupdict()
        version_keys = [k for k in groupdict if k.startswith('version_')]
        if not version_keys:
            return None
        return ''.join(groupdict[k] or '' for k in version_keys)

    def _has_fragment_group(self, pattern: str) -> bool:
        """Return True if pattern has a fragment capture group."""
        if '{fragment}' in pattern:
            return True
        return bool(re.search(r'\(\?P<fragment>', pattern))

    def _get_available_file_versions(self, latest_snapshot_version: Optional[Union[int, datetime]]) -> List[VersionInfo]:
        """Get list of available versions from file path (supports regex and {version}/{fragment} syntax)."""
        path = self.source.path
        pattern = self._path_to_regex_pattern(path)
        dynamic_idx = self._get_dynamic_path_index(path)
        path_parts = path.split('/')
        parent_dir = '/'.join(path_parts[:dynamic_idx]) or '.'
        # Anchor pattern so we only match full path (e.g. exclude customer.parquet/_SUCCESS)
        file_pattern_regex = '/'.join(pattern.split('/')[dynamic_idx:]) + r'/?$'

        self.logger.debug(f"CDC Snapshot: Listing files in {parent_dir} with pattern {file_pattern_regex}")

        # List files using the configured recursive file lookup option (cached)
        recursive_file_lookup = self.source.recursiveFileLookup
        self.logger.debug(f"CDC Snapshot: Using recursive file lookup: {recursive_file_lookup}")
        files_list = self._get_listed_files(parent_dir, recursive=recursive_file_lookup)
        files_with_path_info = [
            FilePathInfo(
                full_path=f.path,
                filename_with_version_path="/".join(f.path.split("/")[dynamic_idx:]),
            )
            for f in files_list
        ]

        self.logger.debug(f"CDC Snapshot: Found {len(files_with_path_info)} files")

        # Extract version from filename; index paths for later reads without re-listing
        version_paths: Dict[str, List[str]] = {}
        available_versions = []
        for file in files_with_path_info:
            self.logger.debug(f"CDC Snapshot: Processing file: {file.filename_with_version_path}")
            try:
                version_info = self._extract_version_from_filename(
                    file.filename_with_version_path, file_pattern_regex
                )
                if version_info is None:
                    continue

                self.logger.debug(
                    "CDC Snapshot: Extracted version from filename: "
                    f"{version_info.formatted_value}. Raw version: {version_info.raw_value}"
                )

                version_paths.setdefault(version_info.formatted_value, []).append(
                    file.full_path
                )

                if (
                    latest_snapshot_version is None
                    and self.source.startingVersion is not None
                    and version_info.raw_value < self.source.startingVersion
                ):
                    continue

                if (
                    latest_snapshot_version is not None
                    and version_info.raw_value <= latest_snapshot_version
                ):
                    continue

                # Dedupe by version (multiple fragments can share same version)
                if any(v.raw_value == version_info.raw_value for v in available_versions):
                    continue
                available_versions.append(version_info)
                self.logger.debug(
                    f"CDC Snapshot: Added version {version_info.formatted_value} "
                    "to available versions"
                )

            except ValueError as e:
                self.logger.warning(
                    f"CDC Snapshot: Skipping file '{file.filename_with_version_path}' - {e}"
                )
                continue

        self._version_paths = version_paths
        return available_versions

    def _get_available_table_versions(self, latest_snapshot_version: Optional[Union[int, datetime]]) -> List[VersionInfo]:
        """Get list of available versions from table."""
        spark = pipeline_config.get_spark()
        table_name = self.source.table

        self.logger.info(f"CDC Snapshot: Getting versions from table: {table_name}")
        try:
            df = spark.table(table_name)
        except Exception as e:
            self.logger.error(f"CDC Snapshot: Error getting versions from table: {e}")
            raise

        # Get the version column
        version_column = self.source.versionColumn

        # Check if the version column is a valid data type
        valid_data_types = ["timestamp", "date", "integer","long"]
        version_column_type = df.schema[version_column].dataType.typeName()
        if version_column_type not in valid_data_types:
            raise ValueError(f"Version column: {version_column}, type: {version_column_type}, is not a valid data type: {valid_data_types}")
        if version_column_type != self.source.versionType:
            raise ValueError(f"Version column: {version_column}, type: {version_column_type}, does not match specified version type: {self.source.versionType}")

        # Get the version values and filter by latest_snapshot_version if provided
        if latest_snapshot_version is not None:
            latest_version_info = VersionInfo(
                raw_value=latest_snapshot_version,
                version_type=self.source.versionType)
            version_df = df.select(version_column).where(f"{version_column} > {latest_version_info.sql_formatted_value}").distinct()
        else:
            version_df = df.select(version_column).distinct()

        available_versions = []
        for row in version_df.collect():
            version = row[version_column]

            if version is None:
                continue

            if self.source.startingVersion is not None and version < self.source.startingVersion:
                self.logger.debug(f"CDC Snapshot: Skipping version {version} because it is less than the starting version {self.source.startingVersion}")
                continue

            if latest_snapshot_version is not None and version <= latest_snapshot_version:
                self.logger.debug(f"CDC Snapshot: Skipping version {version} because it is less than or equal to the latest snapshot version {latest_snapshot_version}")
                continue

            version_info = VersionInfo(
                raw_value=version,
                version_type=self.source.versionType,
                datetime_format=None
            )

            available_versions.append(version_info)

        self.logger.debug(f"CDC Snapshot: Found {len(available_versions)} available versions")

        return available_versions

    def _extract_version_from_filename(self, filename: str, file_pattern: str) -> Optional[VersionInfo]:
        """Extract version from filename using pattern (regex or curly-brace; normalized to regex).

        Version is taken from all named groups starting with version_, concatenated in name order.
        Curly-brace {version} is converted to (?P<version_main>.+); {fragment} to (?P<fragment>.*?).
        """
        regex_pattern = self._path_to_regex_pattern(file_pattern)
        match = re.match(regex_pattern, filename)

        if not match:
            self.logger.debug(f"CDC Snapshot: No match for filename: {filename}")
            self.logger.debug(f"CDC Snapshot: Regex pattern: {regex_pattern}")
            return None

        version_str = self._get_version_string_from_match(match)

        if not version_str:
            self.logger.debug(f"CDC Snapshot: No version_* groups in pattern for filename: {filename}")
            return None

        self.logger.debug(f"CDC Snapshot: Version string match found: {version_str}")

        try:
            if self.source.versionType == CDCSnapshotVersionTypes.TIMESTAMP:
                raw_value = datetime.strptime(version_str, self.source.datetimeFormat)
            else:
                raw_value = int(version_str)

            return VersionInfo(
                raw_value=raw_value,
                version_type=self.source.versionType,
                datetime_format=self.source.datetimeFormat if self.source.versionType == CDCSnapshotVersionTypes.TIMESTAMP else None,
                micro_second_mask_length=self.source.microSecondMaskLength \
                    if self.source.versionType == CDCSnapshotVersionTypes.TIMESTAMP and self.source.microSecondMaskLength else None
            )
        except (ValueError, TypeError) as e:
            self.logger.error(f"CDC Snapshot: Failed to parse version '{version_str}': {e}")
            raise

    def _get_next_version(self, latest_snapshot_version: Optional[Union[int, datetime]]) -> Optional[VersionInfo]:
        """Get the next version to process."""
        # If no previous version exists yet
        if latest_snapshot_version is None:
            if not self.sorted_versions:
                return None
            version_info = self.sorted_versions[0]
            self.logger.debug(f"CDC Snapshot: Using initial version: {version_info.formatted_value}")
            return version_info

        # If a previous version exists,
        # use bisect to find the first version greater than latest_snapshot_version
        index = bisect.bisect_right(self.version_values, latest_snapshot_version)
        if index < len(self.sorted_versions):
            version_info = self.sorted_versions[index]
            self.logger.debug(f"CDC Snapshot: Using next version: {version_info.formatted_value}")
            return version_info
        else:
            self.logger.debug("CDC Snapshot: No more versions available")
            return None

    def _read_snapshot_dataframe(self, version_info: VersionInfo, dataflow_config: DataFlowConfig, target_config_flags: Optional[List[str]] = None) -> Optional[DataFrame]:
        """Read snapshot data into dataframe."""
        read_config = ReadConfig(
            features=dataflow_config.features,
            mode="batch",
            target_config_flags=target_config_flags
        )

        if self.sourceType == CDCSnapshotSourceTypes.FILE:
            path = self.source.path
            pattern = self._path_to_regex_pattern(path)
            dynamic_idx = self._get_dynamic_path_index(path)
            path_parts = path.split('/')
            parent_dir = '/'.join(path_parts[:dynamic_idx]) or '.'
            # Anchor pattern so we only match full path (e.g. exclude customer.parquet/_SUCCESS)
            file_pattern_regex = '/'.join(pattern.split('/')[dynamic_idx:]) + r'/?$'
            regex_pattern = self._path_to_regex_pattern(file_pattern_regex)

            target_version = version_info.formatted_value
            files_to_read: List[str] = []

            # Prefer paths indexed during version discovery (no second listing).
            if self._version_paths is not None and target_version in self._version_paths:
                files_to_read = list(self._version_paths[target_version])
            else:
                recursive_file_lookup = self.source.recursiveFileLookup
                files_list = self._get_listed_files(
                    parent_dir, recursive=recursive_file_lookup
                )
                for f in files_list:
                    full_path = f.path
                    relative_path = "/".join(full_path.split("/")[dynamic_idx:])
                    match = re.match(regex_pattern, relative_path)
                    if not match:
                        continue
                    version_str = self._get_version_string_from_match(match)
                    if version_str is None or version_str != target_version:
                        continue
                    files_to_read.append(full_path)

            if not files_to_read:
                self.logger.warning(f"CDC Snapshot: No files found for version {target_version}")
                return None

            files_to_read = sorted(files_to_read)
            self.logger.info(f"CDC Snapshot: Reading {len(files_to_read)} file(s) for version {target_version}")
            for file_path in files_to_read:
                self.logger.debug(f"CDC Snapshot: Reading file: {file_path}")

            # One Spark load for all fragments of this version (same as union, cheaper).
            source_path: Union[str, List[str]] = (
                files_to_read[0] if len(files_to_read) == 1 else files_to_read
            )
            df = SourceBatchFiles(
                path=source_path,
                format=self.source.format,
                readerOptions=self.source.readerOptions,
                schemaPath=self.source.schemaPath,
                selectExp=self.source.selectExp,
            ).read_source(read_config)

            # Apply filter if specified
            if self.source.filter:
                df = df.where(self.source.filter.replace("{version}", version_info.formatted_value))

        elif self.sourceType == CDCSnapshotSourceTypes.TABLE:
            table_parts = self.source.table.split(".")
            if not 1 < len(table_parts) < 4:
                raise ValueError(f"Invalid table name format: {self.source.table}. Accepted formats are: schema.table & database.schema.table")

            if len(table_parts) == 3:
                database = f"{table_parts[0]}.{table_parts[1]}"
            else:
                # set to the specified target catalog by default
                _pipeline_details = pipeline_config.get_pipeline_details()
                database = f"{_pipeline_details.pipeline_catalog}.{table_parts[0]}"

            table = table_parts[-1]

            select_exp = self.source.selectExp
            where_clause = [
                f"{self.source.versionColumn} = {version_info.sql_formatted_value}"]

            self.logger.info(f"CDC Snapshot: Reading table: {database}.{table} with where clause: {where_clause}")
            df = SourceDelta(
                database=database,
                table=table,
                whereClause=where_clause,
                selectExp=select_exp
            ).read_source(read_config)

        if self.source.deduplicateMode == DeduplicateMode.KEYS_ONLY:
            df = self._deduplicate_by_keys(df)
            self.logger.debug("CDC Snapshot: Applied deduplication by keys")
        elif self.source.deduplicateMode == DeduplicateMode.FULL_ROW:
            df = self._deduplicate_full_row(df)
            self.logger.debug("CDC Snapshot: Applied full-row deduplication")

        return df