from dataclasses import dataclass, field
from typing import Dict

from .flows import BaseFlow, FlowFactory
from .targets import StagingTable


@dataclass
class FlowGroup:
    """
    Flow group definition structure.

    Attributes:
        flowGroupId (str): ID of the flow group.
        flows (List[Dict]): List of flows.
        dataFlowId (str, optional): ID of the data flow.
        stagingTables (Dict[str, Dict], optional): Dictionary of staging tables.

    Methods:
        get_flows() -> Dict[str, BaseFlow]: Get flows associated with the flow group.
        get_staging_tables() -> Dict[str, StagingTable]: Get staging tables associated with the flow group.
    """
    flowGroupId: str
    flows: Dict[str, Dict]
    dataFlowId: str = None
    stagingTables: Dict[str, Dict] = field(default_factory=dict)

    def get_flows(self) -> Dict[str, BaseFlow]:
        """Retrieve all flows as a dictionary of Flow objects."""
        flows = {}
        for key, value in self.flows.items():
            if key in flows:
                raise ValueError(f"Multiple flows found with the same name: {key}")
            flows[key] = FlowFactory.create(key, value)
        return flows

    def get_staging_tables(self) -> Dict[str, StagingTable]:
        """Retrieve the staging tables."""
        staging_tables = {}
        for key, value in self.stagingTables.items():
            table = key
            if value.get("database", None):
                key = f"{value['database']}.{key}"
            if key in staging_tables:
                raise ValueError(f"Multiple staging tables found with the same name: {key}")
            staging_tables[key] = StagingTable(table=table, **value)
        return staging_tables
