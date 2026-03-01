from typing import Dict, List

from .base import BaseSpecTransformer
from dataflow.enums import FlowType, Mode, SourceType, TargetType, TableType


class MaterializedViewSpecTransformer(BaseSpecTransformer):
    """Transform a materialized view dataflow specification into a flow specification."""

    # Constants for values not available in enums
    MAIN_FLOW_GROUP_ID = "main"
    FLOW_NAME_PREFIX = "f_"

    def _process_spec(self, spec_data: Dict) -> List[Dict]:
        """Transform a materialized view dataflow specification into flow specifications."""
        materialized_views = spec_data.get("materializedViews", {})
        
        if not materialized_views:
            self.logger.warning("No materialized views found in dataflow spec")
            return []

        mv_specs = []
        for mv_name, mv_config in materialized_views.items():
            try:
                flow_spec = self._create_flow_spec(mv_name, mv_config, spec_data)
                mv_specs.append(flow_spec)
                
            except Exception as e:
                self.logger.error(f"Error transforming materialized view '{mv_name}': {str(e)}")
                raise

        return mv_specs

    def _create_flow_spec(self, mv_name: str, mv_config: Dict, spec_data: Dict) -> Dict:
        """Create a complete flow specification for a materialized view."""
        if not mv_name or not isinstance(mv_name, str):
            raise ValueError(f"Invalid materialized view name: {mv_name}")
        
        target_details = self._build_target_details(mv_name, mv_config)
        flow_spec = self._build_base_flow_spec(spec_data, mv_config, target_details)
        flow_group = self._create_mv_flow_group(mv_name, mv_config, target_details)
        flow_spec["flowGroups"] = [flow_group]
        
        return flow_spec

    def _build_target_details(self, mv_name: str, mv_config: Dict) -> Dict:
        """Build target details for the materialized view."""
        target_details = mv_config.get("tableDetails", {}).copy()
        target_details.update({
            "table": mv_name,
            "type": TableType.MATERIALIZED_VIEW,
            "sqlPath": mv_config.get("sqlPath"),
            "sqlStatement": mv_config.get("sqlStatement")
        })
        return target_details

    def _build_base_flow_spec(self, spec_data: Dict, mv_config: Dict, target_details: Dict) -> Dict:
        """Build the base flow specification structure."""
        return {
            "dataFlowId": spec_data.get("dataFlowId"),
            "dataFlowGroup": spec_data.get("dataFlowGroup"),
            "dataFlowType": spec_data.get("dataFlowType"),
            "features": spec_data.get("features", {}),
            "targetFormat": TargetType.DELTA,
            "targetDetails": target_details,
            "quarantineMode": mv_config.get("quarantineMode"),
            "quarantineTargetDetails": mv_config.get("quarantineTargetDetails"),
            "dataQualityExpectationsEnabled": mv_config.get("dataQualityExpectationsEnabled", False),
            "dataQualityExpectationsPath": mv_config.get("dataQualityExpectationsPath"),
            "localPath": spec_data.get("localPath")
        }

    def _create_mv_flow_group(self, mv_name: str, mv_config: Dict, target_details: Dict) -> Dict:
        """Create a flow group for a materialized view."""
        flow_group = {
            "flowGroupId": self.MAIN_FLOW_GROUP_ID,
            "flows": {}
        }

        source_view = mv_config.get("sourceView", {})
        source_view_name = source_view.get("sourceViewName")
        
        # Return empty flow group if no source view
        if not source_view or not source_view_name:
            return flow_group

        # Update target details with source view
        target_details["sourceView"] = source_view_name

        # Create and add flow
        flow_name = f"{self.FLOW_NAME_PREFIX}{source_view_name}"
        flow = self._build_materialized_view_flow(mv_name, source_view_name, source_view)
        flow_group["flows"][flow_name] = flow

        return flow_group

    def _build_materialized_view_flow(self, mv_name: str, source_view_name: str, source_view: Dict) -> Dict:
        """Build a materialized view flow configuration."""
        flow = {
            "flowType": FlowType.MATERIALIZED_VIEW,
            "flowDetails": {
                "sourceView": source_view_name,
                "targetTable": mv_name
            },
            "enabled": True
        }

        # Configure source details
        source_type = source_view.get("sourceType")
        source_details = source_view.get("sourceDetails", {}).copy()
        
        # Ensure CDF is disabled for delta sources
        if source_type == SourceType.DELTA:
            source_details["cdfEnabled"] = False

        # Add views to the flow
        flow["views"] = {
            source_view_name: {
                "mode": Mode.BATCH,
                "sourceType": source_type,
                "sourceDetails": source_details
            }
        }

        return flow 