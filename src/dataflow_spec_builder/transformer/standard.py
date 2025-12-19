from typing import Dict

from .base import BaseSpecTransformer
from dataflow.enums import FlowType, Mode, TableType


class StandardSpecTransformer(BaseSpecTransformer):
    """Transform a standard dataflow specification into a flow specification."""

    # Constants for values not available in enums
    MAIN_FLOW_GROUP_ID = "main"
    FLOW_NAME_PREFIX = "f_"

    def _process_spec(self, spec_data: Dict) -> Dict:
        """Transform a standard dataflow specification into a flow specification."""
        # Determine processing configuration
        mode = spec_data.get("mode", Mode.STREAM).lower()
        has_cdc_settings = spec_data.get("cdcSettings") is not None
        has_cdc_snapshot_settings = spec_data.get("cdcSnapshotSettings") is not None
        
        # Set target table type if delta
        target_format = spec_data.get("targetFormat")
        if target_format == "delta":
            target_type = TableType.STREAMING if mode == Mode.STREAM or has_cdc_snapshot_settings else TableType.MATERIALIZED_VIEW
            spec_data["targetDetails"]["type"] = target_type

        # Create base flow spec
        flow_spec = self._build_base_flow_spec(spec_data)
        
        # Create flow group with main flow
        flow_group = self._create_flow_group(spec_data, mode, has_cdc_settings, has_cdc_snapshot_settings)
        flow_spec["flowGroups"] = [flow_group]
        
        # Add CDC configuration if present
        self._add_cdc_configuration(flow_spec, spec_data)
        
        return flow_spec

    def _build_base_flow_spec(self, spec_data: Dict) -> Dict:
        """Build the base flow specification structure."""
        return {
            "dataFlowId": spec_data.get("dataFlowId"),
            "dataFlowGroup": spec_data.get("dataFlowGroup"),
            "dataFlowType": spec_data.get("dataFlowType"),
            "targetFormat": spec_data.get("targetFormat"),
            "targetDetails": spec_data.get("targetDetails"),
            "quarantineMode": spec_data.get("quarantineMode"),
            "quarantineTargetDetails": spec_data.get("quarantineTargetDetails"),
            "dataQualityExpectationsEnabled": spec_data.get("dataQualityExpectationsEnabled", False),
            "dataQualityExpectationsPath": spec_data.get("dataQualityExpectationsPath"),
            "dataQualityExpectations": spec_data.get("dataQualityExpectations"),
            "tableMigrationDetails": spec_data.get("tableMigrationDetails"),
            "localPath": spec_data.get("localPath")
        }

    def _create_flow_group(self, spec_data: Dict, mode: str, has_cdc_settings: bool, has_cdc_snapshot_settings: bool) -> Dict:
        """Create the main flow group with flows."""
        flow_group = {
            "flowGroupId": self.MAIN_FLOW_GROUP_ID,
            "flows": {}
        }

        # Get target and source details
        source_view_name = spec_data.get("sourceViewName")
        target_details = spec_data.get("targetDetails", {})
        target_format = spec_data.get("targetFormat")
        if target_format == "delta":
            target_database = target_details.get("database", None)
            target_table = target_details.get("table", None)
            target_table = target_table if target_database is None else f"{target_database}.{target_table}"
        elif target_format.lower().endswith("sink"):
            target_table = target_details.get("name")
        else:
            raise ValueError(f"Standard Spec Transformation: Unknown target format: {target_format}")

        # Create flow name and type
        flow_name = self._create_flow_name(source_view_name, target_table, has_cdc_snapshot_settings, spec_data)
        flow_type = FlowType.MERGE if has_cdc_settings or has_cdc_snapshot_settings else FlowType.APPEND_VIEW
        
        # Build flow
        flow = {
            "flowType": flow_type,
            "flowDetails": {
                "sourceView": source_view_name,
                "targetTable": target_table
            },
            "enabled": True
        }
        flow_group["flows"][flow_name] = flow

        # Add views if source view exists
        if source_view_name:
            flow["views"] = self._build_views(spec_data, source_view_name, mode)

        return flow_group

    def _create_flow_name(self, source_view_name: str, target_table: str, has_cdc_snapshot_settings: bool, spec_data: Dict) -> str:
        """Create appropriate flow name based on configuration."""
        if has_cdc_snapshot_settings:
            snapshot_type = spec_data.get("cdcSnapshotSettings", {}).get("snapshotType")
            if snapshot_type == "historical":
                return f"f_historical_snapshot_for_{target_table}"
        
        return f"{self.FLOW_NAME_PREFIX}{source_view_name}"        

    def _build_views(self, spec_data: Dict, source_view_name: str, mode: str) -> Dict:
        """Build views configuration for the flow."""
        return {
            source_view_name: {
                "mode": mode,
                "sourceType": spec_data.get("sourceType"),
                "sourceDetails": spec_data.get("sourceDetails", {}),
            }
        }

    def _add_cdc_configuration(self, flow_spec: Dict, spec_data: Dict) -> None:
        """Add CDC configuration to flow spec if present."""
        if spec_data.get("cdcSettings"):
            flow_spec["cdcSettings"] = spec_data["cdcSettings"]
        if spec_data.get("cdcSnapshotSettings"):
            flow_spec["cdcSnapshotSettings"] = spec_data["cdcSnapshotSettings"]
