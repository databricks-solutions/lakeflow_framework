from __future__ import annotations

from typing import ClassVar

from pyspark import pipelines as sdp

from dataflow.field import Field
from dataflow.target import Target


class DeltaSink(Target):
    """
    Delta Sink target.

    Creates a ``delta`` sink using the Spark Declarative Pipelines API.

    Spec fields (``targetDetails`` keys)
    ------------------------------------
    * ``name``        — sink name (required)
    * ``sinkOptions`` — dict of Delta writer options

    Set ``"targetFormat": "delta_sink"`` in the dataflow spec.
    """

    target_type: ClassVar[str] = "delta_sink"
    is_sink: ClassVar[bool] = True
    creates_before_flows: ClassVar[bool] = True

    target_name: str = Field(spec_field="name")
    sinkOptions: dict = Field(default={})

    @property
    def sink_name(self) -> str:
        """Alias for :attr:`target_name` (backward compatibility)."""
        return self.target_name

    def create_target(self) -> None:
        self.logger.info(f"Creating Delta Sink: {self.target_name}")
        sdp.create_sink(f"`{self.target_name}`", self.target_type, self.sinkOptions)
