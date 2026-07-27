from dataclasses import dataclass
from typing import Dict

from pyspark import pipelines as dp
from pyspark.sql import types as T

from .base import BaseTargetDelta
from ..features import Features


@dataclass(kw_only=True)
class TargetDeltaStreamingTable(BaseTargetDelta):
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
        rowFilter (str, optional): Row filter for the target table.
        sparkConf (Dict, optional): Spark configuration for the target table.

    Properties:
        schema_type (str): Type of schema ["json", "ddl"].
        schema (Union[Dict, str]): Schema structure.
        schema_json (Dict): Schema JSON.
        schema_struct (StructType): Schema structure.
        schema_ddl (str): Schema DDL.

    Methods:
        add_columns: Add columns to the target schema.
        remove_columns: Remove columns from the target schema.
        add_table_properties: Add table properties to the target details.
        create_table: Create the target table for the data flow.
    """
    def _create_table(
        self,
        schema: T.StructType | str,
        expectations: Dict = None,
        features: Features = None
    ) -> None:
        """Create the target table for the data flow."""
        dp.create_streaming_table(
            name=self.table,
            comment=self.comment,
            spark_conf=self.sparkConf,
            row_filter=self.rowFilter,
            table_properties=self.tableProperties,
            partition_cols=self.partitionColumns,
            cluster_by=self.clusterByColumns,
            cluster_by_auto=self.clusterByAuto,
            path=self.tablePath,
            schema=schema,
            expect_all=expectations.get("expect_all") if expectations else None,
            expect_all_or_drop=expectations.get("expect_all_or_drop") if expectations else None,
            expect_all_or_fail=expectations.get("expect_all_or_fail") if expectations else None
        )
