from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class FlowType:
    """
    Enumeration of flow types.

    Attributes:
        APPEND_SQL (str): Append SQL mode.
        APPEND_VIEW (str): Append View mode.
        MERGE (str): Merge mode.
        MATERIALIZED_VIEW (str): Materialized View mode.
    """
    APPEND_SQL: str = "append_sql"
    APPEND_VIEW: str = "append_view"
    MERGE: str = "merge"
    MATERIALIZED_VIEW: str = "materialized_view"

@dataclass(frozen=True)
class Mode:
    """
    Enumeration of execution modes.

    Attributes:
        BATCH (str): Batch mode.
        STREAM (str): Stream mode.
    """
    BATCH: str = "batch"
    STREAM: str = "stream"


@dataclass
class QuarantineMode():
    """Constants for different quarantine modes."""
    OFF: str = "off"
    FLAG: str = "flag"
    TABLE: str = "table"


@dataclass(frozen=True)
class SourceType:
    """
    Enumeration of supported source types.

    Attributes:
        BATCH_FILES (str): Batch files source type.
        CLOUD_FILES (str): Cloud files source type.
        DELTA (str): Delta source type.
        DELTA_JOIN (str): Delta join source type.
        KAFKA (str): Kafka source type.
        PYTHON (str): Python source type.
        SQL (str): SQL source type.
    """
    BATCH_FILES: str = "batchfiles" 
    CLOUD_FILES: str = "cloudfiles"
    DELTA: str = "delta"
    DELTA_JOIN: str = "deltajoin"
    KAFKA: str = "kafka"
    PYTHON: str = "python"
    SQL: str = "sql"


@dataclass(frozen=True)
class SinkType:
    """Enumeration of supported target types."""
    CUSTOM_PYTHON_SINK: str = "custom_python_sink"
    DELTA_SINK: str = "delta_sink"
    KAFKA_SINK: str = "kafka_sink"
    FOREACH_BATCH_SINK: str = "foreach_batch_sink"


@dataclass(frozen=True)
class TargetType:
    """Enumeration of supported target types."""
    DELTA: str = "delta"
    DELTA_SINK: str = "delta_sink"
    KAFKA_SINK: str = "kafka_sink"
    FOREACH_BATCH_SINK: str = "foreach_batch_sink"
    CUSTOM_PYTHON_SINK: str = "custom_python_sink"


class TableType(str, Enum):
    """Enumeration of supported table types."""
    STREAMING: str = "st"
    MATERIALIZED_VIEW: str = "mv"


@dataclass(frozen=True)
class TargetConfigFlags:
    """Enumeration of supported target config flags.

    Attributes:
        DISABLE_OPERATIONAL_METADATA (str): Disable operational metadata.
    """
    DISABLE_OPERATIONAL_METADATA = "disableOperationalMetadata"
