from dataclasses import dataclass, field
from typing import Dict, Optional

from ..cdc import CDCSettings
from ..cdc_snapshot import CDCSnapshotSettings
from ..expectations import DataQualityExpectations

from .delta_streaming_table import TargetDeltaStreamingTable


@dataclass(kw_only=True)
class StagingTable(TargetDeltaStreamingTable):
    """
    A structure to hold a target used for defining a staging table inside a flow.

    Attributes:
        cdcSettings (Dict, optional): CDC settings.
        cdcSnapshotSettings (Dict, optional): CDC snapshot settings.
        dataQualityExpectationsEnabled (bool, optional): Whether DQ expectations are enabled.
        dataQualityExpectationsPath (str, optional): Path to DQ expectations file.
        dataQualityExpectations (Dict, optional): Loaded DQ expectations.
        quarantineMode (str, optional): Quarantine mode (off/flag/table).
        quarantineTargetDetails (Dict, optional): Quarantine target configuration.
    
    Methods:
        get_cdc_settings() -> CDCSettings: Get CDC settings.
        get_cdc_snapshot_settings() -> CDCSnapshotSettings: Get CDC snapshot settings.
        get_data_quality_expectations() -> DataQualityExpectations: Get DQ expectations.
        has_quarantine_enabled() -> bool: Check if quarantine is enabled.
    """

    cdcSettings: Dict = field(default_factory=dict)
    cdcSnapshotSettings: Dict = field(default_factory=dict)
    dataQualityExpectationsEnabled: bool = False
    dataQualityExpectationsPath: str = None
    dataQualityExpectations: Dict = field(default_factory=dict)
    quarantineMode: str = None
    quarantineTargetDetails: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Post-init processing."""
        super().__post_init__()
        if self.quarantineMode:
            self.quarantineMode = self.quarantineMode.lower()

    def get_cdc_settings(self) -> CDCSettings:
        """Get CDC configuration."""
        return CDCSettings(**self.cdcSettings) \
            if self.cdcSettings else None

    def get_cdc_snapshot_settings(self) -> CDCSnapshotSettings:
        """Get CDC snapshot settings."""
        return CDCSnapshotSettings(**self.cdcSnapshotSettings) \
            if self.cdcSnapshotSettings else None

    def get_data_quality_expectations(self) -> Optional[DataQualityExpectations]:
        """Get data quality expectations for this staging table."""
        return DataQualityExpectations(**self.dataQualityExpectations) \
            if self.dataQualityExpectationsEnabled and self.dataQualityExpectations else None

    def has_quarantine_enabled(self) -> bool:
        """Check if quarantine is enabled for this staging table."""
        return (
            self.dataQualityExpectationsEnabled 
            and self.quarantineMode is not None 
            and self.quarantineMode != "off"
        )
