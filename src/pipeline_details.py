from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineDetails:
    """Container for pipeline configuration details."""
    pipeline_id: Optional[str]
    pipeline_catalog: Optional[str]
    pipeline_schema: Optional[str]
    pipeline_layer: Optional[str]
    start_utc_timestamp: str
    workspace_env: Optional[str]
    logical_env: str