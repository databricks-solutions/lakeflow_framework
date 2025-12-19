from ..dataflow_config import DataFlowConfig

from .base import BaseFlowWithViews, FlowConfig

class FlowMaterializedView(BaseFlowWithViews):
    """
    Create a materialized view flow.
    """
    def create_flow(
        self,
        dataflow_config: DataFlowConfig,
        flow_config: FlowConfig
    ):
        """Create a materialized view flow."""
        pass
