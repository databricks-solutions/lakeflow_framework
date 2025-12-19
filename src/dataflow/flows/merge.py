from ..cdc import CDCFlow
from ..cdc_snaphot import CDCSnapshotFlow
from ..dataflow_config import DataFlowConfig

from .base import BaseFlowWithViews, FlowConfig


class FlowMerge(BaseFlowWithViews):
    """
    Create a merge flow.
    """
    def create_flow(
        self,
        dataflow_config: DataFlowConfig,
        flow_config: FlowConfig
    ):
        """Create a merge flow based on the provided details, views, and staging tables."""
        cdc_settings = flow_config.cdc_settings
        cdc_snapshot_settings = flow_config.cdc_snapshot_settings
        exclude_columns = flow_config.exclude_columns
        target_config_flags = flow_config.target_config_flags

        if cdc_settings:
            CDCFlow(cdc_settings).create(
                target_table=self.targetTable,
                source_view_name=self.sourceView,
                flow_name=self.flowName,
                additional_except_columns=exclude_columns
            )
            
        elif cdc_snapshot_settings:
            CDCSnapshotFlow(cdc_snapshot_settings).create(
                dataflow_config=dataflow_config,
                target_table=self.targetTable,
                source_view_name=self.sourceView,
                flow_name=self.flowName,
                target_config_flags=target_config_flags
            )
