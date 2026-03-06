from __future__ import annotations

from typing import ClassVar

from pyspark import pipelines as sdp

from dataflow.field import Field
from dataflow.target import Target
from dataflow.targets.mixins.sink import SinkMixin


class CustomPythonSink(Target, SinkMixin):
    """
    Custom Python Sink target.

    A sink for custom Python-based write operations via the SDP sink API.

    Spec fields (``targetDetails`` keys)
    ------------------------------------
    * ``name``        — sink name (required)
    * ``sinkOptions`` — dict of sink options

    Set ``"targetFormat": "custom_python_sink"`` in the dataflow spec.
    """

    target_type: ClassVar[str] = "custom_python_sink"
    sinkOptions: dict = Field(default={})

    def create_target(self) -> None:
        self.logger.info(f"Creating Custom Python Sink: {self.target_name}")
        sdp.create_sink(f"`{self.target_name}`", self.target_type, self.sinkOptions)
