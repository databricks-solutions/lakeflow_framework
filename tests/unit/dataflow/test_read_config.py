"""Unit tests for ReadConfig, CDCSettings, and related config dataclasses."""

from __future__ import annotations

import pyspark.sql.types as T
import pytest

from lakeflow_framework.dataflow.cdc import CDCSettings
from lakeflow_framework.dataflow.dataflow_config import DataFlowConfig
from lakeflow_framework.dataflow.features import Features
from lakeflow_framework.dataflow.sources.base import ReadConfig


class TestReadConfig:
    def test_accepts_stream_and_batch_modes(self):
        features = Features()
        assert ReadConfig(features=features, mode="stream").mode == "stream"
        assert ReadConfig(features=features, mode="batch").mode == "batch"

    def test_rejects_invalid_mode(self):
        with pytest.raises(ValueError, match="Mode must be either 'stream' or 'batch'"):
            ReadConfig(features=Features(), mode="microbatch")

    def test_rejects_non_string_mode(self):
        with pytest.raises(ValueError, match="Mode must be a string"):
            ReadConfig(features=Features(), mode=1)


class TestCDCSettings:
    def test_scd_type_two_sets_timestamp_sequence_type(self):
        settings = CDCSettings(
            keys=["id"],
            sequence_by="updated_at",
            scd_type="2",
        )
        assert settings.sequence_by_data_type == T.TimestampType()

    def test_scd_type_one_leaves_sequence_type_none(self):
        settings = CDCSettings(
            keys=["id"],
            sequence_by="updated_at",
            scd_type="1",
        )
        assert settings.sequence_by_data_type is None


class TestFeatures:
    def test_defaults_operational_metadata_enabled(self):
        assert Features().operationalMetadataEnabled is True

    def test_none_operational_metadata_defaults_to_true(self):
        assert Features(operationalMetadataEnabled=None).operationalMetadataEnabled is True


class TestDataFlowConfig:
    def test_stores_features_and_uc_flag(self):
        features = Features(operationalMetadataEnabled=False)
        config = DataFlowConfig(features=features, uc_enabled=False)
        assert config.features is features
        assert config.uc_enabled is False
