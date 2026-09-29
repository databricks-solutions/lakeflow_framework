"""Unit tests for the Kafka source read path (dataflow/sources/kafka.py)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pyspark.sql.types as T
import pytest

from lakeflow_framework.dataflow.enums import TargetConfigFlags
from lakeflow_framework.dataflow.features import Features
from lakeflow_framework.dataflow.sources.base import ReadConfig
from lakeflow_framework.dataflow.sources.kafka import SourceKafka


METADATA_SCHEMA = T.StructType([
    T.StructField("meta_load_details", T.StructType([T.StructField("record_insert_timestamp", T.TimestampType())])),
])


@pytest.fixture
def kafka_source(pipeline_context, monkeypatch):
    """A Kafka source whose reader returns a mock DataFrame and records operational metadata calls."""
    source = SourceKafka(topic="orders", readerOptions={"kafka.bootstrap.servers": "broker:9092"})
    source.operational_metadata_schema = METADATA_SCHEMA
    df = MagicMock(name="DataFrame")
    df.columns = ["key", "value", "topic"]
    df.withColumn.return_value = df
    metadata_calls = []

    def add_metadata(spark, frame, schema, details):
        metadata_calls.append(schema)
        return frame

    monkeypatch.setattr(source, "_get_df", lambda read_config: df)
    monkeypatch.setattr(source, "_add_operational_metadata", add_metadata)
    return source, df, metadata_calls


class TestKafkaReadSource:
    def test_adds_operational_metadata(self, kafka_source):
        source, _, metadata_calls = kafka_source
        source.read_source(ReadConfig(features=Features(), mode="stream"))
        assert metadata_calls == [METADATA_SCHEMA]

    def test_target_flag_disables_operational_metadata(self, kafka_source):
        source, _, metadata_calls = kafka_source
        flags = [TargetConfigFlags.DISABLE_OPERATIONAL_METADATA]
        source.read_source(ReadConfig(features=Features(), mode="stream", target_config_flags=flags))
        assert metadata_calls == []

    def test_feature_disables_operational_metadata(self, kafka_source):
        source, _, metadata_calls = kafka_source
        source.read_source(ReadConfig(features=Features(operationalMetadataEnabled=False), mode="stream"))
        assert metadata_calls == []

    def test_adds_quarantine_flag(self, kafka_source):
        source, df, _ = kafka_source
        source.read_source(ReadConfig(features=Features(), mode="stream", quarantine_rules="value IS NULL"))
        assert df.withColumn.call_args.args[0] == "is_quarantined"
