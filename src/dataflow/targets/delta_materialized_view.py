from dataclasses import dataclass
from typing import Dict, Optional

from pyspark import pipelines as dp
from pyspark.sql import types as T

from ..operational_metadata import OperationalMetadataMixin
from ..sql import SqlMixin

from .base import BaseTargetDelta


@dataclass(kw_only=True)
class TargetDeltaMaterializedView(BaseTargetDelta, SqlMixin, OperationalMetadataMixin):
    """
    Target details structure for Delta targets.

    Attributes:
        table (str): Table name.
        type (str, optional): Type of table ["st", "mv"]. Defaults to "st".
        tableProperties (Dict, optional): Properties of the target table.
        partitionColumns (List[str], optional): List of partition columns.
        clusterByColumns (List[str], optional): List of cluster by columns.        
        clusterByAuto (bool, optional): Whether to enable cluster by auto.
        schemaPath (str, optional): Path to the schema file (JSON or DDL format).
        tablePath (str, optional): Path to the Delta table.
        sourceView (str, optional): Source view name.
        sqlPath (str, optional): Path to the SQL file.
        sqlStatement (str, optional): SQL statement.
        rowFilter (str, optional): Row filter for the target table.
        sparkConf (Dict, optional): Spark configuration for the target table.

    Properties:
        schema_type (str): Type of schema ["json", "ddl"].
        schema (Union[Dict, str]): Schema structure.
        schema_json (Dict): Schema JSON.
        schema_struct (StructType): Schema structure.
        schema_ddl (str): Schema DDL.
        rawSql (str): Raw SQL statement.

    Methods:
        add_columns: Add columns to the target schema.
        add_table_properties: Add table properties to the target details.
        create_table: Create the target table for the data flow.
        get_sql (str): SQL with substitutions applied.
        remove_columns: Remove columns from the target schema.
    """
    sourceView: Optional[str] = None

    def _create_table(
        self,
        schema: T.StructType | str,
        expectations: Dict = None
    ) -> None:
        """Create the target table for the data flow."""
        spark = self.spark
        logger = self.logger
        operational_metadata_schema = self.operational_metadata_schema
        pipeline_details = self.pipeline_details
        substitution_manager = self.substitution_manager

        msg = (
            f"SQL Settings for MV: {self.table}\n"
            f"Source View: {self.sourceView}\n"
            f"SQL Path: {self.sqlPath}\n"
            f"SQL Statement: {self.sqlStatement}\n"
        )
        logger.debug(msg)

        if not self.sourceView and not self.sqlPath and not self.sqlStatement:
            raise ValueError(
                "Error: sourceView or sqlPath or sql Statement must be set when creating a Materialized View"
            )

        sql = None
        if self.sourceView:
            sql = f"SELECT * FROM live.{self.sourceView}"
        elif self.rawSql:
            sql = substitution_manager.substitute_string(self.rawSql)
        
        @dp.table(
            name=self.table,
            comment=self.comment,
            spark_conf=self.sparkConf,
            row_filter=self.rowFilter,
            path=self.tablePath,
            schema=schema,
            table_properties=self.tableProperties,
            partition_cols=self.partitionColumns,
            cluster_by=self.clusterByColumns,
            cluster_by_auto=self.clusterByAuto,
            private=self.private
        )
        @dp.expect_all(expectations.get("expect_all", {}) if expectations else {})
        @dp.expect_all_or_drop(expectations.get("expect_all_or_drop", {}) if expectations else {})
        @dp.expect_all_or_fail(expectations.get("expect_all_or_fail", {}) if expectations else {})
        def mv_query():
            df = spark.sql(sql)
            
            # Add operational metadata if needed
            if operational_metadata_schema:
                df = self._add_operational_metadata(
                    spark,
                    df,
                    operational_metadata_schema,
                    pipeline_details.__dict__
                )

            return df
