from __future__ import annotations

from typing import ClassVar, Optional

from pyspark import pipelines as sdp

from dataflow.constraints import RequireOneOf
from dataflow.field import Field
from dataflow.operational_metadata import OperationalMetadataMixin
from dataflow.target import Target
from dataflow.targets.mixins.delta import DeltaMixin
from dataflow.targets.mixins.sql import SqlMixin


class MaterializedViewDelta(Target, DeltaMixin, SqlMixin, OperationalMetadataMixin):
    """
    Delta Materialized View target.

    A SQL-backed materialized view.  The query is sourced from one of:

    * ``sourceView`` — generates ``SELECT * FROM live.<view>``
    * ``sqlPath``    — path to a ``.sql`` file (from :class:`SqlMixin`)
    * ``sqlStatement`` — inline SQL string (from :class:`SqlMixin`)

    Flow groups are processed **before** the MV is created so that any
    intermediate views the MV depends on are available.

    Additional spec field (``targetDetails`` key)
    ---------------------------------------------
    * ``sourceView`` — name of a pipeline view to select from

    Set ``"targetFormat": "materialized_view_delta"`` in the dataflow spec.

    .. note::
       Backward-compat: the old ``"targetFormat": "delta"`` with
       ``"targetDetails": {"type": "mv", ...}`` is handled transparently by
       :meth:`~dataflow.dataflow_spec.DataflowSpec.get_target_details`.
    """

    target_type: ClassVar[str] = "materialized_view_delta"
    creates_before_flows: ClassVar[bool] = False  # MV is created after flow groups
    _schema_constraints: ClassVar[list] = [
        RequireOneOf("sourceView", "sqlPath", "sqlStatement"),
    ]

    sourceView: Optional[str] = Field(required=False)

    def create_target(self) -> None:
        spark = self.spark
        logger = self.logger
        op_meta_schema = self.operational_metadata_schema
        pipeline_details = self.pipeline_details
        sm = self.substitution_manager

        if not self.sourceView and not self.sqlPath and not self.sqlStatement:
            raise ValueError(
                f"MaterializedViewDelta '{self.target_name}': one of "
                "sourceView, sqlPath, or sqlStatement must be set."
            )

        if self.sourceView:
            sql = f"SELECT * FROM live.{self.sourceView}"
        else:
            raw = self.rawSql
            sql = sm.substitute_string(raw) if (sm and raw) else raw

        logger.debug(
            f"MV '{self.target_name}' — sourceView={self.sourceView!r}, "
            f"sqlPath={self.sqlPath!r}"
        )

        @sdp.table(
            name=self.target_name,
            comment=self.comment,
            spark_conf=self.sparkConf,
            row_filter=self.rowFilter,
            path=self.tablePath,
            schema=self._table_schema,
            table_properties=self.tableProperties,
            partition_cols=self.partitionColumns,
            cluster_by=self.clusterByColumns,
            cluster_by_auto=self.clusterByAuto,
            private=self.private,
        )
        @sdp.expect_all(
            self._expectations.get("expect_all", {}) if self._expectations else {}
        )
        @sdp.expect_all_or_drop(
            self._expectations.get("expect_all_or_drop", {}) if self._expectations else {}
        )
        @sdp.expect_all_or_fail(
            self._expectations.get("expect_all_or_fail", {}) if self._expectations else {}
        )
        def mv_query():
            df = spark.sql(sql)
            features = self._features
            op_meta_enabled = features.operationalMetadataEnabled if features else True
            if op_meta_schema and op_meta_enabled:
                df = self._add_operational_metadata(
                    spark,
                    df,
                    op_meta_schema,
                    pipeline_details.__dict__,
                )
            return df
