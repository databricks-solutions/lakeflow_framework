from dataclasses import dataclass, field
from typing import Dict

from ..cdc import CDCSettings
from ..cdc_snaphot import CDCSnapshotSettings

from .delta_streaming_table import TargetDeltaStreamingTable


@dataclass(kw_only=True)
class StagingTable(TargetDeltaStreamingTable):
    """
    A structure to hold a target used for defining a staging table inside a flow.

    Attributes:
        cdcSettings (Dict, optional): CDC settings.
        cdcSnapshotSettings (Dict, optional): CDC snapshot settings.
    
    Methods:
        get_cdc_settings() -> CDCSettings: Get CDC settings.
        get_cdc_snapshot_settings() -> CDCSnapshotSettings: Get CDC snapshot settings.
    """

    cdcSettings: Dict = field(default_factory=dict)
    cdcSnapshotSettings: Dict = field(default_factory=dict)

    def get_cdc_settings(self) -> CDCSettings:
        """Get CDC configuration."""
        return CDCSettings(**self.cdcSettings) \
            if self.cdcSettings else None

    def get_cdc_snapshot_settings(self) -> CDCSnapshotSettings:
        """Get CDC snapshot settings."""
        return CDCSnapshotSettings(**self.cdcSnapshotSettings) \
            if self.cdcSnapshotSettings else None
