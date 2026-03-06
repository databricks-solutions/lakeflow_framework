from __future__ import annotations

from typing import ClassVar

from pyspark import pipelines as sdp

from dataflow.field import Field
from dataflow.target import Target
from dataflow.targets.mixins.sql import SqlMixin


class SqlForEachBatchSink(Target, SqlMixin):
    """
    For-each-batch sink that executes a SQL statement against each micro-batch.

    Each micro-batch is registered as a temporary view, the SQL runs against
    it, and the result is written to a Delta table.

    Spec fields (``targetDetails`` keys)
    ------------------------------------
    * ``name``   — sink name (required)
    * ``config`` — dict with the following keys:

      * ``sqlPath`` / ``sqlStatement`` — SQL to run (from :class:`SqlMixin`)
      * ``database`` + ``table``       — destination table (mutually
                                         exclusive with ``path``)
      * ``path``                        — external Delta path destination
      * ``partitionBy``                 — partition column(s)
      * ``clusterBy``                   — liquid-clustering column(s)
      * ``tableProperties``             — applied on first write

    Set ``"targetFormat": "sql_foreach_batch_sink"`` in the spec.

    .. note::
       Backward-compat: the old ``"targetFormat": "foreach_batch_sink"`` with
       ``"type": "basic_sql"`` is remapped transparently by
       :meth:`~dataflow.dataflow_spec.DataflowSpec.get_target_details`.
    """

    target_type: ClassVar[str] = "sql_foreach_batch_sink"
    is_sink: ClassVar[bool] = True
    creates_before_flows: ClassVar[bool] = True

    target_name: str = Field(spec_field="name")
    config: dict = Field(default={})

    @property
    def sink_name(self) -> str:
        """Alias for :attr:`target_name` (backward compatibility)."""
        return self.target_name

    def __post_init__(self) -> None:
        # Populate SqlMixin fields from the nested config dict before
        # super().__post_init__ runs, so that SqlMixin.rawSql works correctly.
        fp = self.field_prefix
        self.__dict__[fp + "sqlPath"] = self.config.get("sqlPath")
        self.__dict__[fp + "sqlStatement"] = self.config.get("sqlStatement")
        super().__post_init__()

    def create_target(self) -> None:
        self.logger.info(
            f"Creating SQL ForEachBatch Sink: {self.target_name}"
        )

        @sdp.foreach_batch_sink(name=self.target_name)
        def batch_function(df, batch_id):
            spark = self.spark
            sm = self.substitution_manager

            temp_view = f"micro_batch_view_{self.target_name}"
            df.createOrReplaceTempView(temp_view)

            raw = self.rawSql
            sql = sm.substitute_string(raw) if (sm and raw) else raw
            sql = sql.replace("micro_batch_view", temp_view)

            result_df = spark.sql(sql)

            partition_by = self.config.get("partitionBy")
            cluster_by = self.config.get("clusterBy")
            writer = result_df.write.format("delta").mode("append")
            if cluster_by:
                writer = writer.clusterBy(cluster_by)
            elif partition_by:
                writer = writer.partitionBy(partition_by)

            path = self.config.get("path")
            if path:
                writer.save(sm.substitute_string(path) if sm else path)
            else:
                table_name = "{}.{}".format(
                    self.config["database"], self.config["table"]
                )
                try:
                    spark.sql(f"DESCRIBE TABLE {table_name}")
                    writer.saveAsTable(table_name)
                except Exception:
                    writer.saveAsTable(table_name)
                    table_properties = self.config.get("tableProperties", {})
                    if table_properties:
                        props_str = ", ".join(
                            f"'{k}' = '{v}'"
                            for k, v in table_properties.items()
                        )
                        spark.sql(
                            f"ALTER TABLE {table_name} "
                            f"SET TBLPROPERTIES ({props_str})"
                        )
