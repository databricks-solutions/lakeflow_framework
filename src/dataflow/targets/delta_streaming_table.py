from __future__ import annotations

from typing import ClassVar

from pyspark import pipelines as sdp

from dataflow.target import Target
from dataflow.targets.mixins.delta import DeltaMixin


class StreamingTableDelta(Target, DeltaMixin):
    """
    Delta Streaming Table target.

    Creates a Spark Declarative Pipelines streaming table backed by Delta.
    Flow groups are processed **after** this table is created.

    Spec fields are declared in
    :class:`~dataflow.targets.mixins.delta.DeltaMixin`.

    Set ``"targetFormat": "streaming_table_delta"`` in the dataflow spec.

    .. note::
       Backward-compat: the old ``"targetFormat": "delta"`` with
       ``"targetDetails": {"type": "st", ...}`` is handled transparently by
       :meth:`~dataflow.dataflow_spec.DataflowSpec.get_target_details`.
    """

    target_type: ClassVar[str] = "streaming_table_delta"
    creates_before_flows: ClassVar[bool] = True

    def create_target(self) -> None:
        sdp.create_streaming_table(
            name=self.target_name,
            comment=self.comment,
            spark_conf=self.sparkConf,
            row_filter=self.rowFilter,
            table_properties=self.tableProperties,
            partition_cols=self.partitionColumns,
            cluster_by=self.clusterByColumns,
            cluster_by_auto=self.clusterByAuto,
            path=self.tablePath,
            schema=self._table_schema,
            expect_all=(
                self._expectations.get("expect_all")
                if self._expectations else None
            ),
            expect_all_or_drop=(
                self._expectations.get("expect_all_or_drop")
                if self._expectations else None
            ),
            expect_all_or_fail=(
                self._expectations.get("expect_all_or_fail")
                if self._expectations else None
            ),
        )
