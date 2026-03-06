from __future__ import annotations

from typing import Optional

from dataflow.cdc import CDCSettings
from dataflow.cdc_snapshot import CDCSnapshotSettings
from dataflow.field import Field
from dataflow.targets.delta_streaming_table import StreamingTableDelta


class StagingTable(StreamingTableDelta):
    """
    Staging table used within a flow group.

    Extends :class:`StreamingTableDelta` with per-table CDC and CDC-snapshot
    settings so that intermediate tables in multi-hop pipelines can carry
    their own change-data-capture configuration independently from the
    top-level dataflow spec.

    This class is **not** registered in the target registry (it does not
    redeclare ``target_type``) and is constructed directly by
    :class:`~dataflow.flow_group.FlowGroup`.

    Additional spec fields
    ----------------------
    * ``cdcSettings``         — CDC settings dict (forwarded to
                                :class:`~dataflow.cdc.CDCSettings`)
    * ``cdcSnapshotSettings`` — CDC snapshot settings dict (forwarded to
                                :class:`~dataflow.cdc_snapshot.CDCSnapshotSettings`)
    """

    cdcSettings: Optional[dict] = Field(required=False)
    cdcSnapshotSettings: Optional[dict] = Field(required=False)

    def get_cdc_settings(self) -> Optional[CDCSettings]:
        """Return :class:`~dataflow.cdc.CDCSettings` if configured."""
        return CDCSettings(**self.cdcSettings) if self.cdcSettings else None

    def get_cdc_snapshot_settings(self) -> Optional[CDCSnapshotSettings]:
        """Return :class:`~dataflow.cdc_snapshot.CDCSnapshotSettings` if configured."""
        return (
            CDCSnapshotSettings(**self.cdcSnapshotSettings)
            if self.cdcSnapshotSettings else None
        )
