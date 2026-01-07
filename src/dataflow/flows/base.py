from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pipeline_config

from ..cdc import CDCSettings
from ..cdc_snapshot import CDCSnapshotSettings
from ..dataflow_config import DataFlowConfig
from ..view import View


@dataclass
class FlowConfig:
    """Configuration for flow creation.

    This class encapsulates all possible parameters needed by different flow types,
    making the interface consistent while allowing for type-specific parameters.

    Attributes:
        exclude_columns: List of columns to exclude from the data
        additional_column_prefix_exceptions: List of additional columns to exclude from prefix
        cdc_settings: The CDC Settings.
        cdc_snapshot_settings: The CDC Snapshot Settings.
        target_config_flags: The target config flags.
    """
    exclude_columns: Optional[List[str]] = None
    additional_column_prefix_exceptions: Optional[List[str]] = None
    cdc_settings: Optional[CDCSettings] = None
    cdc_snapshot_settings: Optional[CDCSnapshotSettings] = None
    target_config_flags: Optional[List[str]] = None


@dataclass(kw_only=True)
class BaseFlow(ABC):
    """
    Represents a data flow in the pipeline.

    Attributes:
        flowType (str): Type of the flow (append_sql, append_view, merge).
        flowDetails (Dict): Details specific to the flow.
        enabled (bool): Whether the flow is enabled.

    Properties:
        targetTable (str): Target table.

    Methods:
        create_flow(config: FlowConfig) -> None: Create a flow using the provided configuration.
    """
    flowName: str
    flowType: str
    flowDetails: Dict
    enabled: bool = True

    def __post_init__(self):
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.substitution_manager = pipeline_config.get_substitution_manager()

    @property
    def targetTable(self) -> str:
        """Get the target name."""
        return self.flowDetails.get("targetTable", None)

    @abstractmethod
    def create_flow(self, dataflow_config: DataFlowConfig, flow_config: FlowConfig):
        """Create a flow using the provided configuration.
        
        Args:
            config: FlowConfig object containing all necessary parameters
        """
        pass


@dataclass(kw_only=True)
class BaseFlowWithViews(BaseFlow):
    """
    Represents a data flow in the pipeline.

    Attributes:
        flowType (str): Type of the flow (append_sql, append_view, merge).
        flowDetails (Dict): Details specific to the flow.
        enabled (bool): Whether the flow is enabled.
        views (Dict[str, View]): Views associated with this flow.

    Properties:
        sourceView (str): Source view.
        targetTable (str): Target table.

    Methods:
        get_views() -> Dict: Get the views associated with this flow.
        create_flow(config: FlowConfig) -> None: Create a flow using the provided configuration.
    """
    views: Dict = field(default_factory=dict)

    @property
    def sourceView(self) -> str:
        """Get the source view."""
        return self.flowDetails.get("sourceView", None)

    def get_views(self) -> Dict[str, View]:
        """Get the views associated with this flow."""
        views = {}
        for key, value in self.views.items():
            if key in views:
                raise ValueError(f"Multiple views found with the same name: {key}")
            views[key] = View(viewName=key, **value)
        return views
