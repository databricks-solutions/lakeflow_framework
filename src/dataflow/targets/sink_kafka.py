from __future__ import annotations

from typing import ClassVar

from pyspark import pipelines as sdp

from dataflow.field import Field
from dataflow.target import Target


class KafkaSink(Target):
    """
    Kafka Sink target.

    Creates a ``kafka`` sink using the Spark Declarative Pipelines API.

    Spec fields (``targetDetails`` keys)
    ------------------------------------
    * ``name``        — sink name (required)
    * ``sinkOptions`` — dict of Kafka writer options

    Set ``"targetFormat": "kafka_sink"`` in the dataflow spec.
    """

    target_type: ClassVar[str] = "kafka_sink"
    is_sink: ClassVar[bool] = True
    creates_before_flows: ClassVar[bool] = True

    target_name: str = Field(spec_field="name")
    sinkOptions: dict = Field(default={}, schema_extra={
        "properties": {
            "topic": {"type": "string"},
            "kafka.bootstrap.servers": {"type": "string"},
            "kafka.group.id": {"type": "string"},
            "kafka.security.protocol": {"type": "string", "default": "SASL_SSL"},
            "kafka.ssl.keystore.location": {"type": "string"},
            "kafka.ssl.keystore.password": {"type": "string"},
            "kafka.ssl.truststore.location": {"type": "string"},
            "kafka.ssl.truststore.password": {"type": "string"},
        },
        "required": ["topic", "kafka.bootstrap.servers"],
    })

    @property
    def sink_name(self) -> str:
        """Alias for :attr:`target_name` (backward compatibility)."""
        return self.target_name

    def create_target(self) -> None:
        self.logger.info(f"Creating Kafka Sink: {self.target_name}")
        sdp.create_sink(f"`{self.target_name}`", self.target_type, self.sinkOptions)
