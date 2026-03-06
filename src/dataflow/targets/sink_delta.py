from __future__ import annotations

from typing import ClassVar

from pyspark import pipelines as sdp

from dataflow.field import Field
from dataflow.target import Target
from dataflow.targets.mixins.sink import SinkMixin


class DeltaSink(Target, SinkMixin):
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
    sinkOptions: dict = Field(default={})

    def create_target(self) -> None:
        self.logger.info(f"Creating Delta Sink: {self.target_name}")
        sdp.create_sink(f"`{self.target_name}`", self.target_type, self.sinkOptions)
