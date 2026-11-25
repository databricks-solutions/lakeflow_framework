"""Unit tests for SourceDelta startingVersionFromDLTSetup (#176).

The histories below are the ones recorded from a real SCD1 streaming table with change data
feed enabled (serverless, CURRENT channel).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lakeflow_framework.dataflow.sources.base import ReadConfig
from lakeflow_framework.dataflow.sources.delta import SourceDelta, resolve_starting_version_from_history

# First run: the table exists by the time the view is defined.
FIRST_RUN = [(0, "CREATE TABLE"), (1, "DLT SETUP"), (2, "MERGE")]
# A full refresh writes 'DLT REFRESH', 'SET TBLPROPERTIES', 'DLT SETUP', then the data commit.
FULL_REFRESH = FIRST_RUN + [
    (3, "MERGE"), (4, "OPTIMIZE"), (5, "DLT REFRESH"), (6, "SET TBLPROPERTIES"), (7, "DLT SETUP"), (8, "MERGE"),
]
# A normal update after a table definition change writes another 'DLT SETUP', with no data.
DEFINITION_CHANGE_AFTER_REFRESH = FULL_REFRESH + [(9, "DLT SETUP")]


class TestResolveStartingVersionFromHistory:
    def test_never_refreshed_starts_at_first_setup(self):
        assert resolve_starting_version_from_history(FIRST_RUN) == 1

    def test_full_refresh_starts_at_setup_after_refresh(self):
        assert resolve_starting_version_from_history(FULL_REFRESH) == 7

    def test_definition_change_after_full_refresh_is_ignored(self):
        """Issue #176: starting at the latest 'DLT SETUP' (9) skips the rows committed at 8."""
        assert resolve_starting_version_from_history(DEFINITION_CHANGE_AFTER_REFRESH) == 7

    def test_definition_change_without_full_refresh_is_ignored(self):
        assert resolve_starting_version_from_history(FIRST_RUN + [(3, "DLT SETUP"), (4, "MERGE")]) == 1

    def test_uses_latest_full_refresh(self):
        history = FULL_REFRESH + [(9, "DLT REFRESH"), (10, "SET TBLPROPERTIES"), (11, "DLT SETUP"), (12, "MERGE")]
        assert resolve_starting_version_from_history(history) == 11

    def test_history_order_does_not_matter(self):
        assert resolve_starting_version_from_history(reversed(DEFINITION_CHANGE_AFTER_REFRESH)) == 7

    def test_no_setup(self):
        assert resolve_starting_version_from_history([(3, "MERGE"), (4, "WRITE")]) is None
        assert resolve_starting_version_from_history([]) is None


def _history_rows(history):
    return [SimpleNamespace(version=version, operation=operation) for version, operation in history]


@pytest.fixture
def delta_spark(pipeline_context):
    """Mock spark: DESCRIBE HISTORY result plus a recorded stream reader."""
    spark = pipeline_context["spark"]
    spark.reset_mock()
    spark.sql.side_effect = None
    df = MagicMock(name="DataFrame")
    df.where.return_value = df
    spark.readStream.options.return_value.table.return_value = df
    return SimpleNamespace(spark=spark, df=df)


def _set_history(spark, history):
    spark.sql.return_value.filter.return_value.select.return_value.collect.return_value = _history_rows(history)


def _source(**kwargs) -> SourceDelta:
    return SourceDelta(
        database="live", table="stg_customer", cdfEnabled=True, startingVersionFromDLTSetup=True, **kwargs
    )


def _read(source: SourceDelta):
    return source._get_df(ReadConfig(features=None, mode="stream"))


def _reader_options(spark) -> dict:
    return spark.readStream.options.call_args.kwargs


class TestSourceDeltaStartingVersionFromDLTSetup:
    def test_qualifies_live_table_with_pipeline_catalog_and_schema(self, delta_spark):
        _set_history(delta_spark.spark, FIRST_RUN)
        _read(_source())
        delta_spark.spark.sql.assert_called_once_with("DESCRIBE HISTORY test_catalog.test_schema.stg_customer")

    def test_sets_starting_version_after_definition_change(self, delta_spark):
        _set_history(delta_spark.spark, DEFINITION_CHANGE_AFTER_REFRESH)
        _read(_source())
        assert _reader_options(delta_spark.spark) == {"readChangeFeed": "true", "startingVersion": "7"}

    def test_no_setup_leaves_starting_version_unset(self, delta_spark):
        _set_history(delta_spark.spark, [(3, "MERGE")])
        _read(_source())
        assert "startingVersion" not in _reader_options(delta_spark.spark)

    def test_history_error_leaves_starting_version_unset(self, delta_spark, caplog):
        delta_spark.spark.sql.side_effect = Exception("PERMISSION_DENIED")
        _read(_source())
        assert "startingVersion" not in _reader_options(delta_spark.spark)
        assert "Starting version could not be set" in caplog.text

    def test_flag_disabled_does_not_read_history(self, delta_spark):
        _read(SourceDelta(
            database="live", table="stg_customer", cdfEnabled=True, readerOptions={"maxFilesPerTrigger": "1"}
        ))
        delta_spark.spark.sql.assert_not_called()
        assert _reader_options(delta_spark.spark) == {"maxFilesPerTrigger": "1", "readChangeFeed": "true"}
