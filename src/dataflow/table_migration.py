from dataclasses import dataclass
import json
from typing import Dict

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.utils import AnalysisException

import pipeline_config
import utility

from .cdc import CDCSettings
from .dataflow_config import DataFlowConfig
from .dataflow_spec import DataflowSpec
from .sources import SourceDelta
from .table_import import create_table_import_flow


@dataclass
class TableMigrationDetails:
    """
    Migration details structure to move data into a Spark Declarative Pipeline.

    Attributes:
        enabled (bool): Flag indicating if migration is enabled.
        catalogType (str): Type of catalog.
        sourceDetails (Dict): Source details for migration.

    Methods:
        get_source_details() -> SourceDelta: Get source details for migration.
    """
    enabled: bool
    catalogType: str
    sourceDetails: Dict
    autoStartingVersionsEnabled: bool = True

    def get_source_details(self) -> SourceDelta:
        """Get source details for migration."""
        return SourceDelta(**self.sourceDetails)


class TableMigrationManager:
    """
    Manage Delta Table Migration.

    Attributes:
        dataflow_spec (DataflowSpec): Dataflow specification.
        target_database (str): Target database.
        target_table_name (str): Target table name.
        cdc_settings (CDCSettings): The CDC Settings.
        dataflow_config (DataFlowConfig): Dataflow configuration.

    Methods:
        initialize_state(views: Dict[str, str]) -> None: Initialize table migration state.
        create_flow() -> None: Create table migration flow.
        set_view_starting_versions(views: Dict[str, View]) -> Dict[str, View]: Set view starting versions.
    """
    def __init__(
        self,
        dataflow_spec: DataflowSpec,
        target_database: str,
        target_table_name: str,
        cdc_settings: CDCSettings = None,
        dataflow_config: DataFlowConfig = None,
    ):
        self.dataflow_spec = dataflow_spec
        self.target_database = target_database
        self.target_table_name = target_table_name
        self.cdc_settings = cdc_settings
        self.dataflow_config = dataflow_config
        
        self.spark = pipeline_config.get_spark()
        self.dbutils = pipeline_config.get_dbutils()
        self.logger = pipeline_config.get_logger()
        self.operational_metadata_schema = pipeline_config.get_operational_metadata_schema()
        self.pipeline_details = pipeline_config.get_pipeline_details()
        self.substitution_manager = pipeline_config.get_substitution_manager()

        # Initialize table migration details
        self.table_migration_details = TableMigrationDetails(
            **self.dataflow_spec.tableMigrationDetails
        ) if self.dataflow_spec.tableMigrationDetails else None
        
        self.table_migration_enabled = (
            self.table_migration_details.enabled 
            if self.table_migration_details else False
        )
        
        self.logger.info(f"Table Migration enabled for table: {self.target_table_name} - {self.table_migration_enabled}")

        # Initialize auto starting versions enabled
        self.auto_starting_versions_enabled = (
            self.table_migration_details.autoStartingVersionsEnabled
            if self.table_migration_details else False  # Default to True if not specified
        )

        # Initialize delta source views (empty if migration disabled)
        self.delta_source_views = (
            {view.viewName: view for view in self.dataflow_spec.get_all_delta_source_views().values()}
            if self.table_migration_enabled else {}
        )
    
        # Initialize checkpoint state variables
        self.checkpoint_state_volume_root_path = None
        self.checkpoint_state_initial_versions_path = None
        self.checkpoint_state_tracking_path = None
        self.checkpoint_state_table_schema = None
        self.table_checkpoint_versions = {}

        # Initialize state (method handles migration disabled case internally)
        self._initialize_state()

    def _initialize_state(self):
        """Set up checkpoint state based on the migration details."""
        if not self.table_migration_enabled or not self.auto_starting_versions_enabled:
            self.logger.info(
                "Table migration disabled, skipping state initialization" if not self.table_migration_enabled 
                else "Table migration enabled, but auto starting version management is disabled. Skipping state initialization"
            )
            return

        self.checkpoint_state_volume_root_path = pipeline_config.get_table_migration_state_volume_path()
        self.checkpoint_state_initial_versions_path = f"{self.checkpoint_state_volume_root_path}/initial_versions"
        self.checkpoint_state_tracking_path = f"{self.checkpoint_state_volume_root_path}/tracking"

        self.logger.info(
            f"Table Migration - Paths:\n"
            f"  - root: {self.checkpoint_state_volume_root_path}\n"
            f"  - initial versions: {self.checkpoint_state_initial_versions_path}\n"
            f"  - tracking: {self.checkpoint_state_tracking_path}"
        )

        self.checkpoint_state_initial_versions_schema = T.StructType([
            T.StructField("pipelineId", T.StringType(), False),
            T.StructField("targetTable", T.StringType(), False),
            T.StructField("tableName", T.StringType(), False),
            T.StructField("viewName", T.StringType(), False),
            T.StructField("initialVersion", T.IntegerType(), False)
        ])
        self.checkpoint_state_tracking_schema = T.StructType([
            T.StructField("pipelineId", T.StringType(), False),
            T.StructField("targetTable", T.StringType(), False),
            T.StructField("tableName", T.StringType(), False),
            T.StructField("viewName", T.StringType(), False),
            T.StructField("version", T.IntegerType(), False),
            T.StructField("currentVersion", T.IntegerType(), True),
            T.StructField("ready", T.BooleanType(), False)
        ])

        self._track_checkpoint_state()
        self._set_view_starting_versions()

        self.logger.debug(f"Table Migration - table: {self.target_table_name}, final dataflow spec: {json.dumps(self.dataflow_spec.__dict__, indent=4)}")
            
    def create_flow(self):
        """Set up table migration flow based on the migration details."""
        if self.table_migration_enabled:
            self.logger.info("Table Migration Setup...")
            create_table_import_flow(
                source_details=self.table_migration_details.sourceDetails,
                target_table_name=self.target_table_name,
                cdc_settings=self.cdc_settings,
                dataflow_config=self.dataflow_config
            )
        else:
            self.logger.info("Table Migration is disabled, skipping flow creation")

    def _track_checkpoint_state(self):
        """Track the table migration checkpoint state."""
        self.logger.info(f"Table Migration - table: {self.target_table_name}, tracking delta table state")

        if self.delta_source_views:
            self.logger.debug(f"Table Migration - table: {self.target_table_name},"
                f" delta views: {list(self.delta_source_views.keys())}"
            )

            # check if checkpoint state store exists
            initial_versions_store_exists = self._state_store_exists(self.checkpoint_state_initial_versions_path)
            tracking_store_exists = self._state_store_exists(self.checkpoint_state_tracking_path)
            
            self.logger.debug(f"Table Migration - table: {self.target_table_name},"
                f" initial versions store exists - {initial_versions_store_exists}\n"
                f" tracking store exists - {tracking_store_exists}"
            )

            # get initial source table versions
            initial_versions_df = None
            if not initial_versions_store_exists:
                self.logger.debug(f"Table Migration - table: {self.target_table_name},"
                    f" initial versions store does not exist, getting initial source table versions"
                )
                initial_versions_df = self._get_source_table_versions()
                self._write_state_store(initial_versions_df, self.checkpoint_state_initial_versions_path)
            else:
                self.logger.debug(f"Table Migration - table: {self.target_table_name},"
                    f" initial versions store exists, reading initial source table versions"
                )
                initial_versions_df = self._read_state_store(
                    path=self.checkpoint_state_initial_versions_path,
                    schema=self.checkpoint_state_initial_versions_schema
                )

                # TODO: remove this once final defect with Auto CDC and group by is tested and this is no longer needed
                # if initial_versions_df.count() < 1:
                #     self.logger.debug(f"Table Migration - table: {self.target_table_name},"
                #         f" initial versions df is empty, getting initial source table versions"
                #     )
                #     initial_versions_df = self._get_source_table_versions()
                #     self._write_state_store(initial_versions_df, self.checkpoint_state_initial_versions_path)

            # Get and save migration state
            checkpoint_state_df = self.get_migration_state(initial_versions_df, tracking_store_exists)
            self.table_checkpoint_versions = {
                row.viewName: {
                    "tableName": row.tableName,
                    "version": row.version,
                    "currentVersion": row.currentVersion,
                    "ready": row.ready,
                }
                for row in checkpoint_state_df.collect()
            }

            self._write_state_store(checkpoint_state_df, self.checkpoint_state_tracking_path)

    def _get_source_table_versions(self) -> DataFrame:
        """Get the initial source table versions."""
        self.logger.debug(
            f"Table Migration - table: {self.target_table_name},"
            f" getting initial source table versions for - {list(self.delta_source_views.keys())}"
        )
        delta_views = {
            view_name: f"{view.get_source_details().database}.{view.get_source_details().table}"
            for view_name, view in self.delta_source_views.items()
        }
        self.logger.debug(f"Table Migration - table: {self.target_table_name}, delta views dict: {json.dumps(delta_views, indent=4)}")
        initial_versions_df = utility.get_table_versions(self.spark, delta_views)
        initial_versions_df = (initial_versions_df
            .withColumn("pipelineId", F.lit(self.pipeline_details.pipeline_id))
            .withColumn("targetTable", F.lit(self.target_table_name))
            .withColumn("initialVersion", F.col("version"))
            .select("pipelineId", "targetTable", "tableName", "viewName", "initialVersion"))

        return initial_versions_df

    def get_migration_state(self, initial_versions_df: DataFrame, checkpoint_state_store_exists: bool,) -> DataFrame:
        """Get the migration state."""
        self.logger.debug(
            f"Table Migration - table: {self.target_table_name} getting migration state."
        )

        if initial_versions_df.count() < 1:
            msg = f"Table Migration - table: {self.target_table_name}, initial versions not stored yet"
            self.logger.error(msg)
            raise RuntimeError(msg)

        self.logger.debug("Table Migration - table: %s, initial versions df:\n%s", self.target_table_name, initial_versions_df.show(truncate=False))

        checkpoint_state_df = None
        if checkpoint_state_store_exists:
            self.logger.debug(f"Table Migration - table: {self.target_table_name}, checkpoint state store exists, reading checkpoint state")
            checkpoint_state_df = self._read_state_store(
                path=self.checkpoint_state_tracking_path,
                schema=self.checkpoint_state_tracking_schema
            )
            checkpoint_state_df.show()
            checkpoint_state_df = initial_versions_df.alias("initial").join(
                checkpoint_state_df.alias("checkpoint"),
                on=["pipelineId", "targetTable", "viewName"],
                how="left"
            ).selectExpr(
                "COALESCE(initial.pipelineId, checkpoint.pipelineId) AS pipelineId",
                "COALESCE(initial.targetTable, checkpoint.targetTable) AS targetTable",
                "COALESCE(initial.tableName, checkpoint.tableName) AS tableName",
                "initial.viewName",
                "initial.initialVersion AS version",
                "COALESCE(checkpoint.currentVersion, initial.initialVersion) AS currentVersion",
                "COALESCE(false, checkpoint.ready) AS ready"
            )
            checkpoint_state_df.show()
        else:
            self.logger.debug(
                f"Table Migration - table: {self.target_table_name},"
                f" checkpoint state store does not exist, creating initial checkpoint state"
            )
            checkpoint_state_df = initial_versions_df.selectExpr(
                "pipelineId",
                "targetTable",
                "tableName",
                "viewName",
                "initialVersion AS version",
                "initialVersion AS currentVersion",
                "false AS ready"
            )

        # get delta views and tables from checkpoint state table
        delta_views = {row.viewName: row.tableName for row in checkpoint_state_df.where("ready = false").collect()}
        if delta_views:
            # get current table versions from source delta tables
            self.logger.debug(f"Table Migration - table: {self.target_table_name}, delta views dict: {json.dumps(delta_views, indent=4)}")
            current_table_versions_df = utility.get_table_versions(self.spark, delta_views)
            
            # join checkpoint state df with current table versions df
            checkpoint_state_df = (
                checkpoint_state_df.alias("checkpoint")
                .join(current_table_versions_df.alias("current"), on=["viewName"], how="left")
                .selectExpr(
                    "pipelineId",
                    "targetTable",
                    "checkpoint.tableName",
                    "checkpoint.viewName",
                    "checkpoint.version",
                    "COALESCE(current.version, checkpoint.currentVersion) AS currentVersion",
                    "COALESCE(current.version > checkpoint.version, checkpoint.ready) AS ready"
                )
            )

        self.logger.debug("Table Migration - table: %s, checkpoint state df:\n%s", self.target_table_name, checkpoint_state_df.show(truncate=False))

        return checkpoint_state_df

    def _write_state_store(self, checkpoint_state_df: DataFrame, path: str):
        """Write the checkpoint state df to the checkpoint state table."""
        pipeline_id = self.pipeline_details.pipeline_id
        options = {
            "header": "true",
            "replaceWhere": f"pipelineId = '{pipeline_id}' AND targetTable = '{self.target_table_name}'"
        }
        (checkpoint_state_df.write.format("csv")
            .options(**options)
            .mode("overwrite")
            .partitionBy("pipelineId", "targetTable")
            .save(path)
        )

    def _read_state_store(self, path: str, schema: T.StructType = None) -> DataFrame:
        """Read the checkpoint state df from the checkpoint state table."""
        pipeline_id = self.pipeline_details.pipeline_id
        target_table = self.target_table_name
        self.logger.debug(f"Table Migration - table: {self.target_table_name}, reading state from - {path}")
        
        reader = self.spark.read.format("csv").option("header", "true")
        reader = reader.schema(schema) if schema else reader
        return reader.load(path).where(f"pipelineId = '{pipeline_id}' AND targetTable = '{target_table}'")

    def _state_store_exists(self, path: str) -> bool:
        """Check if the checkpoint state table exists."""
        try:
            df = self._read_state_store(path)
            return df.count() > 0
        except (Exception):
            self.logger.debug(f"Table Migration - table: {self.target_table_name}, path does not exist yet - {path}")
            return False

    def _set_view_starting_versions(self):
        """
        Sets the appropriate starting version for the view. If the checkpoint state is not ready, 
        a where clause will be added, preventing rows from being returned
        """
        spec = self.dataflow_spec
        for flow_group in spec.flowGroups:
            for flow in flow_group.get("flows", {}).values():
                for view_name, view in flow.get("views", {}).items():
                    checkpoint_state = self.table_checkpoint_versions.get(view_name, None)
                    self.logger.debug(
                        f"Table Migration - table: {self.target_table_name}, view: {view_name}, "
                        f"checkpoint state to be applied: {json.dumps(checkpoint_state, indent=4)}"
                    )
                    if checkpoint_state:
                        source_details = view.get("sourceDetails")
                        if checkpoint_state["ready"]:
                            version = int(checkpoint_state["version"]) + 1
                            if "readerOptions" in source_details:
                                option = {"startingVersion": version}
                                source_details["readerOptions"].update(option)
                                self.logger.debug(f"Table Migration - table: {self.target_table_name}, view: {view_name}, reader options updated - {option}")
                            else:
                                option = {"startingVersion": version}
                                source_details["readerOptions"] = option
                                self.logger.debug(f"Table Migration - table: {self.target_table_name}, view: {view_name}, reader options set - {option}")
                        else:
                            source_details["whereClause"] = ["1=0"]
                            self.logger.debug(f"Table Migration - table: {self.target_table_name}, view: {view_name}, where clause set to 1=0")