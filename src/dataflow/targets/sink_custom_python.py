from dataclasses import dataclass, field
from typing import Dict, Any

from .base import BaseSink
from ..enums import SinkType


@dataclass(kw_only=True)
class TargetCustomPythonSink(BaseSink):
    """
    Target details structure for Kafka Sinks.

    Attributes:
        name (str): Name of the sink.
        sinkOptions (Dict, optional): Options for the Delta writer.
    """
    name: str
    sinkOptions: Dict = field(default_factory=dict)

    def __post_init__(self):
        BaseSink.__init__(self)

    @property
    def sink_name(self) -> str:
        """Returns the name of the sink."""
        return self.name

    @property
    def sink_type(self) -> str:
        """Returns the type of the sink."""
        return SinkType.DELTA_SINK

    @property
    def sink_options(self) -> Dict[str, Any]:
        """Returns the options for the sink configuration."""
        return self.sinkOptions
