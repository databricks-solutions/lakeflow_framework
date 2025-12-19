from typing import Dict

from pyspark import pipelines as dp
import pyspark.sql.functions as F

from constants import MetaDataColumnDefs, SystemColumns
import pipeline_config
import utility

from .enums import QuarantineMode, TableType, TargetType, Mode
from .targets import (
    TargetFactory,
    TargetDeltaMaterializedView,
    TargetDeltaStreamingTable
)


class QuarantineManager():
    """
    Manager for quarantine operations.

    Attributes:
        quarantine_mode (str): Quarantine mode.
        data_quality_rules (Dict): Data quality expectations.
        quarantineTargetDetails (Dict): Quarantine target details.
        quarantine_table (TargetDelta): Quarantine table.

    Methods:
        create_quarantine_table: Create the quarantine table.
        add_quarantine_columns: Add quarantine columns to the target details.
        create_quarantine_flow: Create quarantine flow and view.
    """

    QUARANTINE_COLUMN = MetaDataColumnDefs.QUARANTINE_FLAG
    CDF_COLUMNS = [column.value for column in SystemColumns.CDFColumns]

    def __init__(
        self,
        quarantine_mode: str,
        data_quality_rules: Dict = None,
        target_format: str = TargetType.DELTA,
        target_details: TargetDeltaStreamingTable | TargetDeltaMaterializedView = None,
        quarantine_target_details: Dict = None
    ):
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.substitution_manager = pipeline_config.get_substitution_manager()
        self.mandatory_table_properties = pipeline_config.get_mandatory_table_properties()
        self.quarantine_mode = quarantine_mode
        self.data_quality_rules = data_quality_rules
        self.target_format = target_format
        self.quarantine_target_details = quarantine_target_details
        self.target_details = target_details
        self.quarantine_rules = f"NOT({ ' AND '.join(data_quality_rules.values()) })"
        self.mode = Mode.STREAM if (
            (self.target_format == TargetType.DELTA and self.target_details.type == TableType.STREAMING.value)
            or self.target_format in (TargetType.KAFKA_SINK) #TODO: Add other types as they become supported
        ) else Mode.BATCH
        self.target = getattr(self.target_details, 'table') or getattr(self.target_details, 'sink_name')
        self.quarantine_table = None

        self._init_quarantine()

    def _init_quarantine(self):
        """Initialize quarantine mode."""
        if self.quarantine_mode != QuarantineMode.TABLE:
            return

        quarantine_details = {
            "table": f"{self.target}_quarantine" if not self.quarantine_target_details.get("table", None) else self.quarantine_target_details.get("table"),
            "database": self.quarantine_target_details.get("database", None) if not self.quarantine_target_details.get("table", None) else None,
            "tableProperties": utility.merge_dicts(
                self.quarantine_target_details.get("tableProperties", {}),
                self.mandatory_table_properties
            ),
            "partitionColumns": self.quarantine_target_details.get("partitionColumns", None),
            "clusterByColumns": self.quarantine_target_details.get("clusterByColumns", None),
            "clusterByAuto": self.quarantine_target_details.get("clusterByAuto", False),
            "tablePath": self.quarantine_target_details.get("path", None)
        }
        if self.mode == Mode.STREAM:

            quarantine_details["type"] = TableType.STREAMING.value
            self._create_quarantine_table(quarantine_details)

        if self.mode == Mode.BATCH:
            
            quarantine_view_name=f"v_{self.target}_quarantine"
            quarantine_details["type"] = TableType.MATERIALIZED_VIEW.value
            quarantine_details["sourceView"] = quarantine_view_name

            quarantine_view_name=f"v_{self.target}_quarantine"
            self._create_quarantine_view_mv(
                quarantine_view_name=quarantine_view_name,
                target_details=self.target_details
            )

            self._create_quarantine_table(quarantine_details)

    def _create_quarantine_table(self, quarantine_details: Dict):
        """Create the quarantine table."""
        self.quarantine_table = TargetFactory.create(TargetType.DELTA, quarantine_details)

        self.logger.info("Creating Quarantine Table: %s, Mode: %s, Partition Columns: %s, Cluster By Columns: %s, Cluster By Auto: %s",
            self.quarantine_table.table, self.mode, self.quarantine_table.partitionColumns,
            self.quarantine_table.clusterByColumns, self.quarantine_table.clusterByAuto)

        self.quarantine_table.create_table()

    def add_quarantine_columns_delta(
        self,
        target_details: TargetDeltaStreamingTable | TargetDeltaMaterializedView
    ) -> TargetDeltaStreamingTable | TargetDeltaMaterializedView:
        """
        Add quarantine columns to the target details.

        Args:
            target_details (TargetDelta): Target details.
        """
        if self.target_format == TargetType.DELTA and self.quarantine_mode == QuarantineMode.FLAG:
            if target_details.schema:
                return target_details.add_columns([QuarantineManager.QUARANTINE_COLUMN])

        return target_details

    def create_quarantine_flow(self, source_view_name: str):
        """
        Create quarantine flows and views.

        Args:
            flow_groups (List[FlowGroup]): List of flow groups.
        """
        if self.quarantine_mode != QuarantineMode.TABLE:
            self.logger.info("Quarantine mode is not table, skipping quarantine flow creation.")
            return
        
        if self.mode == Mode.STREAM:
            
            quarantine_view_name = f"{source_view_name}_quarantine"
            
            self._create_quarantine_view_st(
                quarantine_view_name=quarantine_view_name,
                source_view_name=source_view_name
            )

            self._create_quarantine_flow(
                quarantine_view_name=quarantine_view_name,
                quarantine_table_name=self.quarantine_table.table
            )

        else:
            msg = "Cannot create quarantine flow for batch mode. Batch mode only requires the quarantine MV."
            self.logger.error(msg)
            raise ValueError(msg)

    def _create_quarantine_view_mv(
        self,
        quarantine_view_name: str,
        target_details: TargetDeltaMaterializedView
    ) -> str:
        """Create a view with the quarantine flag."""
        quarantine_column_name = QuarantineManager.QUARANTINE_COLUMN["name"]

        self.logger.info("Creating Quarantine View: %s", quarantine_view_name)
        self.logger.debug("Quarantine Rules for %s: %s", quarantine_view_name, self.quarantine_rules)

        def get_quarantine_view():

            df = None
            if target_details.sourceView:
                df = self.spark.read.table(f"live.{target_details.sourceView}")
            elif target_details.rawSql:
                sql = self.substitution_manager.substitute_string(target_details.rawSql)
                df = self.spark.sql(sql)
            else:
                raise ValueError("No source view or sql path or sql statement provided")

            return (df
                .withColumn(quarantine_column_name, F.expr(self.quarantine_rules))
                .where(f"{quarantine_column_name} = 1")
                .drop(quarantine_column_name)
            )

        dp.view(
                get_quarantine_view,
                name=quarantine_view_name,
                comment="Final view with quarantine flag",
            )

    def _create_quarantine_view_st(
        self,
        quarantine_view_name: str,
        source_view_name: str
    ):
        """Create a view with the quarantine flag."""
        quarantine_column_name = QuarantineManager.QUARANTINE_COLUMN["name"]

        self.logger.info("Creating Quarantine View: %s", quarantine_view_name)
        self.logger.debug("Quarantine Rules for %s: %s", quarantine_view_name, self.quarantine_rules)

        def get_quarantine_view():
            df = self.spark.readStream.table(f"live.{source_view_name}")
            df = df.withColumn(quarantine_column_name, F.expr(self.quarantine_rules))
            return df

        dp.view(
                get_quarantine_view,
                name=quarantine_view_name,
                comment="Final view with quarantine flag",
            )

    def _create_quarantine_flow(
        self,
        quarantine_view_name: str,
        quarantine_table_name: str
    ):
        """Create a flow to append to quarantine table for flagged rows."""
        self.logger.info("Creating Quarantine Append Flow, Source View: %s, Quarantine Table: %s",
            quarantine_view_name, quarantine_table_name)

        quarantine_column_name = QuarantineManager.QUARANTINE_COLUMN["name"]
        columns_to_drop = [quarantine_column_name] + QuarantineManager.CDF_COLUMNS

        @dp.append_flow(
            name=f"f_quarantine_{quarantine_view_name}",
            target=quarantine_table_name)
        def quarantined_rows():
            df = self.spark.readStream.table(f"live.{quarantine_view_name}").where(f"{quarantine_column_name} = 1")
            df = utility.drop_columns(df, columns_to_drop)
            return df
    