from dataclasses import dataclass, field
from typing import Dict, List, Any

import utility

from dataflow.cdc import CDCSettings
from dataflow.cdc_snaphot import CDCSnapshotSettings
from dataflow.enums import SourceType
from dataflow.expectations import DataQualityExpectations
from dataflow.features import Features
from dataflow.flow_group import FlowGroup
from dataflow.flows import BaseFlowWithViews
from dataflow.targets import TargetFactory
from dataflow.view import View


@dataclass
class DataflowSpec:
    """
    Dataflow specification structure.

    Attributes:
        dataFlowId (str): ID of the dataflow.
        dataFlowGroup (str): Group of the dataflow.
        dataFlowType (str): Type of the dataflow.
        targetFormat (str): Format of the target.
        targetDetails (Dict): Target details.
        flowGroups (List[Dict]): List of flow groups.
        tags (Dict): Dictionary containing tags.
        features (dic): Dictionary containing a list of enabled optional features / fixes
        cdcSettings (str, optional): CDC settings.
        cdcSnapshotSettings (str, optional): CDC snapshot settings.
        dataFlowVersion (str, optional): Version of the dataflow.
        dataQualityExpectationsEnabled (bool, optional): Flag indicating if data quality expectations are enabled.
        dataQualityExpectationsPath (str, optional): Path to the data quality expectations.
        dataQualityExpectations (Dict, optional): Data quality expectations.
        quarantineMode (str, optional): Quarantine mode.
        quarantineTargetDetails (Dict, optional): Quarantine target details.
        tableMigrationDetails (Dict, optional): Table migration details.
        localPath (str, optional): Local path.

    Methods:
        get_all_views(): Get all views from the flow dataflow specification.
        get_all_cdf_delta_views(): Get all views with CDF enabled for Delta targets.
        get_cdc_settings(): Get CDC settings
        get_cdc_snapshot_settings(): Get CDC snapshot settings.
        get_data_quality_expectations(): Get data quality expectations.
        get_flow_groups(): Get flow groups.
        get_target_details(): Get target details for Delta targets.
        get_all_source_views(): Get all views that directly read from source tables.
    """
    dataFlowId: str
    dataFlowGroup: str
    dataFlowType: str
    targetFormat: str
    targetDetails: Dict
    flowGroups: List[Dict]
    tags: Dict = field(default_factory=dict)
    features: Dict = field(default_factory=dict)
    cdcSettings: Dict = field(default_factory=dict)
    cdcSnapshotSettings: Dict = field(default_factory=dict)
    dataFlowVersion: str = None
    dataQualityExpectationsEnabled: bool = False
    dataQualityExpectationsPath: str = None
    dataQualityExpectations: Dict = field(default_factory=dict)
    quarantineMode: str = None
    quarantineTargetDetails: Dict = field(default_factory=dict)
    tableMigrationDetails: Dict = field(default_factory=dict)
    localPath: str = None

    def __post_init__(self):
        self.dataFlowType = self.dataFlowType.lower()
        self.targetFormat = self.targetFormat.lower()
        self.quarantineMode = self.quarantineMode.lower() if self.quarantineMode else None

    def get_all_views(self) -> Dict[str, View]:
        """Retrieve all views from the flow groups."""
        all_views = {}
        
        for flow_group in self.get_flow_groups():
            flows = flow_group.get_flows()
            for flow_name in flows:
                flow = flows[flow_name]
                if isinstance(flow, BaseFlowWithViews):
                    all_views = utility.merge_dicts(all_views, flow.get_views())
        
        return all_views

    def get_all_cdf_delta_views(self) -> Dict[str, View]:
        """Retrieve all views that are of source type DELTA and have CDF enabled."""
        cdf_delta_views = {}
        all_views = self.get_all_views()

        for view_name in all_views:
            view = all_views[view_name]
            if view.sourceType == SourceType.DELTA and view.isCdfEnabled:
                cdf_delta_views[view_name] = view
        
        return cdf_delta_views

    def get_all_delta_source_views(self) -> Dict[str, View]:
        """Retrieve all views that directly read from Delta source tables."""
        source_views = {}
        target_tables = []
        all_views = self.get_all_views()
        
        for flow_group in self.get_flow_groups():
            flows = flow_group.get_flows()
            for flow_name, flow in flows.items():
                target_tables.append(flow.targetTable)

        for view_name, view in all_views.items():
            if view.sourceType == SourceType.DELTA and view.get_source_details().database.lower() != "live":
                if view.get_source_details().table not in target_tables:
                    source_views[view.viewName] = view
    
        return source_views

    def get_cdc_settings(self) -> CDCSettings:
        """Get CDC configuration for the target table."""
        return CDCSettings(**self.cdcSettings) \
            if self.cdcSettings else None

    def get_cdc_snapshot_settings(self) -> CDCSnapshotSettings:
        """Get CDC snapshot settings for the target table."""
        return CDCSnapshotSettings(**self.cdcSnapshotSettings) \
            if self.cdcSnapshotSettings else None

    def get_data_quality_expectations(self) -> DataQualityExpectations:
        """Get data quality expectations for the target table."""
        return DataQualityExpectations(**self.dataQualityExpectations) \
            if self.dataQualityExpectationsEnabled and self.dataQualityExpectations else None

    def get_features(self) -> Features:
        """Get features for the target table."""
        return Features(**self.features)

    def get_flow_groups(self) -> List[FlowGroup]:
        """Retrieve a list of FlowGroup objects from the flowGroups attribute."""
        return [FlowGroup(**item) for item in self.flowGroups]

    def get_target_details(self) -> Any:
        """Retrieve the target details based on the target format."""
        return TargetFactory.create(self.targetFormat, self.targetDetails)
