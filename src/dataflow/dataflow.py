from typing import Dict, List

import pyspark.sql.types as T

from constants import SystemColumns
import pipeline_config

from .cdc_snaphot import CDCSnapshotFlow
from .dataflow_config import DataFlowConfig
from .dataflow_spec import DataflowSpec
from .enums import QuarantineMode, SinkType, TargetType, TableType
from .flows.base import BaseFlow, BaseFlowWithViews, FlowConfig
from .flow_group import FlowGroup
from .table_migration import TableMigrationManager
from .quarantine import QuarantineManager
from .targets import StagingTable
from .view import View, ViewConfig


class DataFlow:
    """
    manage and orchestrate data pipelines.
    
    Attributes:
        dataflow_spec (DataflowSpec): The dataflow specification.

        # general attributes
        flow_groups (List[FlowGroup]): List of flow groups.
        local_path (str): The local path.
        pipeline_catalog (str): The pipeline catalog.
        pipeline_schema (str): The pipeline schema.
        uc_enabled (bool): Whether Unity Catalog is enabled.

        # target details
        target_details (Dict): The target details.
        target_database (str): The target database.

        # CDC settings
        cdc_settings (CDCSettings): The CDC settings.
        cdc_snapshot_settings (CDCSnapshotSettings): The CDC snapshot settings.

        # expectations
        expectations_enabled (bool): Whether expectations are enabled.
        expectations (DataQualityExpectations): The data quality expectations.
        expectations_clause (Dict): The expectations clause for the SDP create table api.

        # quarantine settings
        quarantine_enabled (bool): Whether quarantine is enabled.
        quarantine_manager (QuarantineManager): The quarantine manager.
        quarantine_mode (str): The quarantine mode.

        # table migration settings
        table_migration_manager (TableMigrationManager): The table migration manager.
        table_migration_enabled (bool): Whether table migration is enabled.

        # features
        features (Dict): The features.

    Methods:
        create_dataflow():
            Creates the data flow based on the specifications.
    """

    CDF_COLUMN_NAMES = [column.value for column in SystemColumns.CDFColumns]
    SCD2_COLUMN_NAMES = [column.value for column in SystemColumns.SCD2Columns]

    def __init__(
            self,
            dataflow_spec: DataflowSpec
        ):
        self.dataflow_spec = dataflow_spec
        self.spark = pipeline_config.get_spark()
        self.logger = pipeline_config.get_logger()
        self.pipeline_details = pipeline_config.get_pipeline_details()
        
        self.pipeline_catalog = self.pipeline_details.pipeline_catalog
        self.pipeline_schema = self.pipeline_details.pipeline_schema
        
        self.flow_groups = self.dataflow_spec.get_flow_groups()
        self.local_path = self.dataflow_spec.localPath        
        self.features = self.dataflow_spec.get_features()
        self.uc_enabled = self.spark.conf.get("spark.databricks.unityCatalog.enabled", "false").lower() == "true"
        self.table_migration_enabled = False
        
        self.dataflow_config = DataFlowConfig(
            features=self.features,
            uc_enabled=self.uc_enabled
        )

        self._init_target_details()
        self._init_cdc_settings()
        self._init_expectations()
        self._init_quarantine()
        self._init_table_migration()

    def _init_target_details(self):
        """init target details from the dataflow specification."""
        self.target_details = self.dataflow_spec.get_target_details()
        self.target_database = (
            self.target_details.database
            if hasattr(self.target_details, 'database') and self.target_details.database
            else f"{self.pipeline_catalog}.{self.pipeline_schema}"
        )
        
        log_target = f"target type: {self.dataflow_spec.targetFormat}, target: " + (
            getattr(self.target_details, 'sink_name')
            if self.dataflow_spec.targetFormat in SinkType.__dict__.values()
            else getattr(self.target_details, 'table')
        )
        self.logger.info(f"Initializing DataFlow for target schema: {self.target_database}, {log_target}")
        self.logger.debug(f"Target Details: {self.target_details.__dict__}")

        # Add operational metadata columns to the schema
        if not hasattr(self.target_details, 'schema') or not self.target_details.schema:
            return

        if not self.features.operationalMetadataEnabled:
            return

    def _init_cdc_settings(self):
        """init CDC settings."""

        def get_scd2_columns(sequence_by_data_type: T.DataType) -> List[T.StructField]:
            return [
                T.StructField(SystemColumns.SCD2Columns.SCD2_START_AT.value, sequence_by_data_type),
                T.StructField(SystemColumns.SCD2Columns.SCD2_END_AT.value, sequence_by_data_type)
            ]

        self.cdc_settings = self.dataflow_spec.get_cdc_settings()
        self.cdc_snapshot_settings = self.dataflow_spec.get_cdc_snapshot_settings()

        # return if target has no schema
        if not hasattr(self.target_details, 'schema') or not self.target_details.schema:
            return
        
        # init CDC
        if self.cdc_settings and self.cdc_settings.scd_type == "2":

            # TODO: implement dynamic sequence by type
            sequence_by_data_type = self.cdc_settings.sequence_by_data_type
            scd2_columns = get_scd2_columns(sequence_by_data_type)
            self.target_details.add_columns(scd2_columns)

        # init CDC Snapshot
        elif self.cdc_snapshot_settings and self.cdc_snapshot_settings.scd_type == "2":

            # TODO: implement dynamic sequence by type
            sequence_by_data_type = self.cdc_snapshot_settings.sequence_by_data_type
            scd2_columns = get_scd2_columns(sequence_by_data_type)
            self.target_details.add_columns(scd2_columns)

    def _init_expectations(self):
        """init expectations."""
        self.expectations_clause = None
        self.expectations_enabled = self.dataflow_spec.dataQualityExpectationsEnabled
        
        if self.expectations_enabled:    
            self.logger.info("Expectations enabled")
            self.expectations = self.dataflow_spec.get_data_quality_expectations()    
            
            if self.expectations is None:
                raise RuntimeError("Expectations object is None and not initialized correctly in Dataflow!")
            
            self.logger.debug(f"Expectations Object: {self.expectations.__dict__}")
            self.expectations_clause = self.expectations.get_expectations()

    def _init_quarantine(self):
        """init quarantine settings."""
        self.quarantine_enabled = (
            self.expectations_enabled 
            and self.expectations.all_rules 
            and self.dataflow_spec.quarantineMode != "off")

        self.quarantine_mode = self.dataflow_spec.quarantineMode
        if self.quarantine_enabled:
            self.logger.info("Quarantine enabled")

            # Initialize quarantine manager
            self.quarantine_manager = QuarantineManager(
                quarantine_mode=self.quarantine_mode,
                data_quality_rules=self.expectations.all_rules if self.expectations_enabled else None,
                target_format=self.dataflow_spec.targetFormat,
                target_details=self.target_details,
                quarantine_target_details=self.dataflow_spec.quarantineTargetDetails
            )

            self.target_details = self.quarantine_manager.add_quarantine_columns_delta(self.target_details)

    def _init_table_migration(self):
        """init table migration."""
        self.table_migration_manager = None

        if not self.dataflow_spec.targetFormat == TargetType.DELTA:
            self.logger.info("Table migration not supported for target type: %s", self.dataflow_spec.targetFormat)
            return

        if not self.dataflow_spec.tableMigrationDetails:
            self.logger.info("Table migration not enabled for table: %s", self.target_details.table)
            return

        self.table_migration_manager = TableMigrationManager(
            dataflow_spec=self.dataflow_spec,
            target_database=self.target_database,
            target_table_name=self.target_details.table,
            cdc_settings=self.cdc_settings,
            dataflow_config=self.dataflow_config,
        )

    def create_dataflow(self):
        """Create the data flow based on the specifications."""
        log_target = f"target type: {self.dataflow_spec.targetFormat}, target: " + (
            getattr(self.target_details, 'sink_name')
            if self.dataflow_spec.targetFormat in SinkType.__dict__.values()
            else getattr(self.target_details, 'table')
        )
        log_msg = (
            f"Flow ID: {self.dataflow_spec.dataFlowId}\n"
            f"Flow Group: {self.dataflow_spec.dataFlowGroup}\n"
            f"Target: {log_target}")
        self.logger.info(log_msg)
        self.logger.debug(f"Pipeline Details: {self.pipeline_details}")
        self.logger.debug(f"Dataflow Specification: {self.dataflow_spec.__dict__}")

        expectations = self.expectations_clause

        # ensure expectations are converted to expect_all if quarantine FLAG mode is enabled
        if self.quarantine_enabled and self.quarantine_mode == QuarantineMode.FLAG:
            expectations = self.expectations.get_expectations_as_expect_all()

        if self.dataflow_spec.targetFormat == TargetType.DELTA:
            
            if self.target_details.type == TableType.STREAMING.value:
                
                # create streaming table
                self.target_details.create_table(expectations)

                # setup table migration
                if self.table_migration_manager:
                    self.table_migration_manager.create_flow()

                # create flow groups
                self._create_flow_groups()

            if self.target_details.type == TableType.MATERIALIZED_VIEW.value:
                
                # create flow groups
                self._create_flow_groups()

                # create materialized view
                self.target_details.create_table(expectations)

        elif self.dataflow_spec.targetFormat in SinkType.__dict__.values():
            
            # create sink
            self.target_details.create_sink()

            # create flow groups
            self._create_flow_groups()
        
        else:
            raise ValueError(f"Unsupported target format: {self.dataflow_spec.targetFormat}")

    def _create_flow_groups(self):
        """Create flow groups."""
        self.logger.info("Creating FlowGroups...")
        for flow_group in self.flow_groups:
            self._create_flow_group(flow_group)

    def _create_flow_group(self, flow_group: FlowGroup):
        """Create a flow group and its associated staging tables and flows."""
        self.logger.info("Creating Flow Group: %s", flow_group.flowGroupId)

        # create staging tables
        staging_tables = flow_group.get_staging_tables()
        if staging_tables:
            self.logger.info("Creating Staging Tables...")
            for staging_table in staging_tables.values():
                staging_table.create_table()

                # Support direct historical snapshots into Staging Tables in Flows
                cdc_snapshot_settings = staging_table.get_cdc_snapshot_settings()
                if (cdc_snapshot_settings and cdc_snapshot_settings.is_historical()):
                    self.logger.info(
                        "Creating CDC historical snapshot source for staging table: %s",
                        staging_table.table
                    )

                    CDCSnapshotFlow(cdc_snapshot_settings).create(
                        dataflow_config=self.dataflow_config,
                        target_table=staging_table.table,
                        target_config_flags=staging_table.configFlags
                    )

        # create flows
        self.logger.info("Creating Flows...")
        flows = flow_group.get_flows()
        for flow in flows.values():
            if flow.enabled:
                self.logger.info("Creating Flow: %s", flow.flowName)
                self._create_flow(flow, staging_tables)
            else:
                self.logger.info("Flow Disabled: %s", flow.flowName)

    def _create_flow(self, flow: BaseFlow, staging_tables: Dict[str, StagingTable]):
        """Create a flow and its associated views."""
        self.logger.info("Creating Views...")

        # Prepare Flow Configuration
        is_target = self.is_target(flow.targetTable)
        flow_config = self._prepare_flow_config(flow, staging_tables)

        if isinstance(flow, BaseFlowWithViews):
            views = flow.get_views() or {}

            # Create views
            self._create_views(views, flow.sourceView, is_target, flow_config.target_config_flags)

            # Create Flow
            flow.create_flow(self.dataflow_config, flow_config)

            # Handle Table Quarantine Mode
            if (self.quarantine_enabled
                and self.quarantine_mode == QuarantineMode.TABLE
                and is_target
            ):
                self.quarantine_manager.create_quarantine_flow(flow.sourceView)

        else:
            # Get quarantine rules if needed. note in table mode we don't apply them to the source view,
            # they are applied to a quarantine view that passes to the the quarantine target table.
            quarantine_rules = None
            if (self.quarantine_enabled
                and self.quarantine_mode != QuarantineMode.TABLE
                and is_target
            ):
                quarantine_rules = self.quarantine_manager.quarantine_rules

            # Create Flow
            flow.create_flow(self.dataflow_config, flow_config, quarantine_rules)

    def _create_views(self, views: Dict[str, View], flow_source_view: str, is_target: bool, target_config_flags: List[str]) -> None:
        """Create views for the flow, handling quarantine as needed."""
        for view in views.values():

            # Get quarantine rules if needed. note in table mode we don't apply them to the source view,
            # they are applied to a quarantine view that passes to the the quarantine target table.
            quarantine_rules = None
            if (self.quarantine_enabled
                and self.quarantine_mode != QuarantineMode.TABLE
                and is_target
                and flow_source_view == view.viewName
            ):
                quarantine_rules = self.quarantine_manager.quarantine_rules

            # Create the view
            view.create_view(
                self.dataflow_config,
                view_config=ViewConfig(target_config_flags=target_config_flags),
                quarantine_rules=quarantine_rules
            )

    def _prepare_flow_config(
        self,
        flow: BaseFlow,
        staging_tables: Dict[str, StagingTable]
    ) -> FlowConfig:
        """Prepare flow configuration."""
        # Get CDC settings
        cdc_settings = self._get_cdc_settings(flow, staging_tables)
        self.logger.debug("Retrieved CDC settings: %s", cdc_settings)

        # Get columns to exclude
        exclude_columns = self._get_exclude_columns(flow)
        
        # Get column prefix exceptions
        prefix_exceptions = self._get_column_prefix_exceptions()

        # Disable operational metadata if needed
        target_config_flags = []
        if self.is_target(flow.targetTable):
            target_config_flags = self.target_details.configFlags
        else:
            target_config_flags = staging_tables.get(flow.targetTable).configFlags

        return FlowConfig(
            exclude_columns=exclude_columns,
            target_config_flags=target_config_flags,
            additional_column_prefix_exceptions=prefix_exceptions,
            **cdc_settings,
        )

    def _get_cdc_settings(self, flow: BaseFlow, staging_tables: Dict[str, StagingTable]) -> Dict:
        """Get CDC settings for the flow."""
        self.logger.debug("Retrieving CDC settings for table: %s", flow.targetTable)
        is_target = self.is_target(flow.targetTable)
        if is_target:
            cdc_settings = self.cdc_settings
            cdc_snapshot_settings = self.cdc_snapshot_settings
        else:
            staging_table = staging_tables.get(flow.targetTable)
            if staging_table is None:
                raise ValueError(f"Staging table not found for CDC settings retrieval: {flow.targetTable}")
            cdc_settings = staging_table.get_cdc_settings()
            cdc_snapshot_settings = staging_table.get_cdc_snapshot_settings()

        self.logger.debug("Retrieved CDC settings: %s \nCDC snapshot settings: %s", cdc_settings, cdc_snapshot_settings)

        return {
            "cdc_settings": cdc_settings,
            "cdc_snapshot_settings": cdc_snapshot_settings
        }

    def _get_exclude_columns(self, flow: BaseFlow) -> List[str]:
        """Get list of columns to exclude based on quarantine and CDF settings."""
        exclude_columns = []
        
        # Add quarantine flag if enabled for this target
        is_target = self.is_target(flow.targetTable)
        if (
            self.quarantine_enabled
            and self.quarantine_mode == QuarantineMode.TABLE
            and is_target
        ):
            exclude_columns.append(QuarantineManager.QUARANTINE_COLUMN.get("name"))
        
        return exclude_columns

    def _get_column_prefix_exceptions(self) -> List[str]:
        """Get list of columns to exclude from prefix treatment."""
        exceptions = [
            SystemColumns.SCD2Columns.SCD2_START_AT.value,
            SystemColumns.SCD2Columns.SCD2_END_AT.value
        ]
        
        return exceptions

    def is_target(self, name: str) -> bool:
        """Check if the table is the target."""
        if self.dataflow_spec.targetFormat in SinkType.__dict__.values():
            return name == self.target_details.sink_name
        else:
            return name == self.target_details.table
