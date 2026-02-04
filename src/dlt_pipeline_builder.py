from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
import sys

from pyspark import pipelines as dp
from pyspark.dbutils import DBUtils
import pyspark.sql.types as T
from pyspark.sql import SparkSession
from typing import Dict, Any

from constants import(
    FrameworkPaths, FrameworkSettings, PipelineBundlePaths, DLTPipelineSettingKeys, SupportedSpecFormat
)
from dataflow import DataFlow
from dataflow_spec_builder import DataflowSpecBuilder
from pipeline_details import PipelineDetails
from secrets_manager import SecretsManager
from substitution_manager import SubstitutionManager

import pipeline_config
import utility


class DLTPipelineBuilder:
    """
    Initializes a dataflow in a Spark Declarative Pipeline based on the pipeline configuration and dataflow specifications.
    
    Args:
        spark (SparkSession): The Spark session to use for the pipeline.
        dbutils (DBUtils): The DBUtils to use for the pipeline.

    Attributes:
        spark (SparkSession): The Spark session to use for the pipeline.
        dbutils (DBUtils): The DBUtils to use for the pipeline.

        logger (Logger): The logger to use for the pipeline.
        context (NotebookContext): The notebook context to use for the pipeline.
        token (str): The token to use for the pipeline.
        
        pipeline_config (Dict[str, Any]): The pipeline configuration to use for the pipeline.
        framework_path (str): The path to the framework to use for the pipeline.
        bundle_path (str): The path to the bundle to use for the pipeline.
        dataflow_path (str): The path to the dataflow to use for the pipeline.
        workspace_host (str): The host to use for the pipeline.
        
        dataflow_specs (List[DataflowSpec]): The dataflow specifications to use for the pipeline.
        dataflow_spec_filters (Dict[str, Any]): The filters to use for the dataflow specifications.
        
        pipeline_details (PipelineDetails): The pipeline details to use for the pipeline.
        mandatory_table_properties (Dict[str, Any]): The mandatory table properties to use for the pipeline.
        operational_metadata_schema (StructType): The operational metadata schema to use for the pipeline.
        substitution_manager (SubstitutionManager): The substitution manager to use for the pipeline.

    Methods:
        initialize_pipeline(): Initializes a dataflow in a Spark Declarative Pipeline.
    """

    MANDATORY_CONFIG_PARAMS = [
        DLTPipelineSettingKeys.BUNDLE_SOURCE_PATH,
        DLTPipelineSettingKeys.FRAMEWORK_SOURCE_PATH,
        DLTPipelineSettingKeys.WORKSPACE_HOST
    ]

    def __init__(self, spark: SparkSession, dbutils: DBUtils):
        """Initialize the pipeline builder with Spark session and utilities."""
        # Initialize Spark context
        self.spark = spark
        self.dbutils = dbutils
        self.context = self.dbutils.entry_point.getDbutils().notebook().getContext()
        self.token = self.context.apiToken().get()

        self.pipeline_bundle_spec_format = "json" # Default to JSON format
        self.dataflow_specs = []
        self.dataflow_spec_filters = {}
        self.mandatory_table_properties = {}
        self.operational_metadata_schema = None
        self.pipeline_config = {}
        self.secrets_manager = None
        self.substitution_manager = None
        self.driver_cores = os.cpu_count()
        self.default_max_workers = self.driver_cores - 1 if self.driver_cores else 1
        
        # Initialize logger
        log_level = self.spark.conf.get(DLTPipelineSettingKeys.LOG_LEVEL, "INFO").upper()
        self.logger = utility.set_logger("DltFramework", log_level)
        self.logger.info("Initializing Pipeline...")
        self.logger.info("Logical cores (threads): %s", self.driver_cores)
        self.logger.info("Max workers: %s", self.default_max_workers)

        # Initialize core singletons
        pipeline_config.initialize_core(
            spark=self.spark,
            dbutils=self.dbutils,
            logger=self.logger,
        )

        # Load configurations and initialize components
        self._init_configurations()
        self._init_pipeline_components()

    def _init_configurations(self) -> None:
        """Load and validate all necessary configurations."""
        # Load mandatory parameters
        config_values = {
            param: self.spark.conf.get(param, None)
            for param in self.MANDATORY_CONFIG_PARAMS
        }
        
        missing_params = [param for param, value in config_values.items() if not value]
        if missing_params:
            raise ValueError(f"Missing mandatory config parameters: {missing_params}")

        self.bundle_path = config_values[DLTPipelineSettingKeys.BUNDLE_SOURCE_PATH]
        self.framework_path = config_values[DLTPipelineSettingKeys.FRAMEWORK_SOURCE_PATH]
        self.workspace_host = config_values[DLTPipelineSettingKeys.WORKSPACE_HOST]

        # Load optional parameters
        ignore_validation_errors = self.spark.conf.get(
            DLTPipelineSettingKeys.PIPELINE_IGNORE_VALIDATION_ERRORS, "false"
        )
        self.ignore_validation_errors = (ignore_validation_errors.lower() == "true")

        # Load pipeline details
        self.logger.info("Loading Pipeline Details...")
        self.pipeline_details = PipelineDetails(
            pipeline_id=self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_ID, None),
            pipeline_catalog=self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_CATALOG, None),
            pipeline_schema=(
                self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_SCHEMA, None)
                or self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_TARGET, None)
            ),
            pipeline_layer=self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_LAYER, None),
            start_utc_timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f'),
            workspace_env=self.spark.conf.get(DLTPipelineSettingKeys.BUNDLE_TARGET, None),
            logical_env=self.spark.conf.get(DLTPipelineSettingKeys.LOGICAL_ENV, "")
        )
        self.logger.info("Pipeline Details: %s", json.dumps(self.pipeline_details.__dict__, indent=4))

        # Initialize pipeline details singleton
        pipeline_config.initialize_pipeline_details(self.pipeline_details)

        # Get the pipeline update id via event hook (only method at the moment)
        # This only gets populated post initiliazation. Currently retrieved in operational_metadata.py
        @dp.on_event_hook
        def update_id_hook(event):
            if self.spark.conf.get("pipeline.pipeline_update_id", "") == "":
                update_id = event.get("origin", {}).get("update_id", "")
                if update_id:
                    self.spark.conf.set("pipeline.pipeline_update_id", update_id)
        
        # Load dataflow filters
        self.logger.info("Loading Dataflow Filters...")
        self.dataflow_spec_filters = {
            "data_flow_ids": self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_FILTER_DATA_FLOW_ID, None),
            "data_flow_groups": self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_FILTER_DATA_FLOW_GROUP, None),
            "flow_group_ids": self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_FILTER_FLOW_GROUP_ID, None),
            "target_tables": self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_FILTER_TARGET_TABLE, None),
            "files": self.spark.conf.get(DLTPipelineSettingKeys.PIPELINE_FILE_FILTER, None),
        }

    def _init_pipeline_components(self) -> None:
        """Initialize all pipeline components."""
        
        # Load and merge configurations
        self._load_merged_config()

        # Initialize substitution manager
        self._init_substitution_manager()

        # Initialize secrets manager
        self._init_secrets_manager()

        # Preload shared Python modules
        self._preload_extensions()
        
        # Initialize dataflow specifications
        self._init_dataflow_specs()
        
        # Setup operational metadata
        self._setup_operational_metadata()
        
        # Apply Spark configurations
        self._apply_spark_config()

    def _load_framework_global_config_file(self) -> Dict[str, Any]:
        """Load a global config file"""
        global_config_paths = [os.path.join(self.framework_path, path) for path in FrameworkPaths.GLOBAL_CONFIG]
        
        # Check if more than one global config exists
        existing_configs = [path for path in global_config_paths if os.path.exists(path)]
        if len(existing_configs) > 1:
            raise ValueError(f"Multiple framework global config files found. Only one is allowed: {existing_configs}")
        
        if not existing_configs:
            raise FileNotFoundError(f"Framework global config file not found, in path: {global_config_paths}")
        
        global_config_path = existing_configs[0]
        self.logger.info("Retrieving Global Framework Config From: %s", global_config_path)
        return utility.load_config_file_auto(global_config_path, False) or {}

    def _load_pipeline_bundle_global_config_file(self) -> Dict[str, Any]:
        """Load a global config file"""
        global_config_paths = [
            os.path.join(self.bundle_path, PipelineBundlePaths.PIPELINE_CONFIGS_PATH, path) for path in PipelineBundlePaths.GLOBAL_CONFIG_FILE
        ]
        
        # Check if more than one global config exists
        existing_configs = [path for path in global_config_paths if os.path.exists(path)]
        if len(existing_configs) > 1:
            raise ValueError(f"Multiple pipeline global config files found. Only one is allowed: {existing_configs}")
        
        if not existing_configs:
            return {}
        
        pipeline_config_path = existing_configs[0]
        self.logger.info("Retrieving Pipeline Global Config From: %s", pipeline_config_path)
        return utility.get_json_from_file(pipeline_config_path, False) or {}

    def _load_merged_config(self) -> None:
        """Load and merge global and pipeline-specific configurations."""
        self.pipeline_config = self._load_framework_global_config_file()
        pipeline_bundle_config = self._load_pipeline_bundle_global_config_file()

        # Initialize pipeline bundle spec format
        self._init_pipeline_bundle_spec_format(pipeline_bundle_config)
        
        # Merge pipeline bundle config
        if pipeline_bundle_config:
            self.pipeline_config.update(pipeline_bundle_config)

        self.mandatory_table_properties = self.pipeline_config.get("mandatory_table_properties", {})
        
        # Initialize mandatory table properties singleton
        pipeline_config.initialize_mandatory_table_properties(self.mandatory_table_properties)

        # Initialize mandatory configuration singleton
        pipeline_config.initialize_mandatory_configuration()

        # Initialize table migration state volume path
        pipeline_config.initialize_table_migration(self.pipeline_config.get("table_migration_state_volume_path", None))

    def _init_pipeline_bundle_spec_format(self, pipeline_bundle_config: Dict[str, Any]) -> None:
        """Initialize the pipeline bundle spec format."""
        valid_formats = [fmt.value for fmt in SupportedSpecFormat]
        
        # Process global format configuration
        global_format_dict = self.pipeline_config.pop("pipeline_bundle_spec_format", None)
        if global_format_dict:
            self.logger.info("Global pipeline bundle spec format: %s", global_format_dict)
            global_format = global_format_dict.get("format", "json")
            
            if global_format not in valid_formats:
                raise ValueError(f"Invalid pipeline bundle spec format: {global_format}. Valid formats are: {valid_formats}")
            
            self.pipeline_bundle_spec_format = global_format
            allow_override = global_format_dict.get("allow_override", False)
        else:
            allow_override = False
        
        # Process pipeline-specific format configuration
        pipeline_format_dict = pipeline_bundle_config.pop("pipeline_bundle_spec_format", None)
        if pipeline_format_dict:
            self.logger.info("Pipeline bundle spec format: %s", pipeline_format_dict)
            pipeline_format = pipeline_format_dict.get("format", None)

            if pipeline_format and pipeline_format not in valid_formats:
                raise ValueError(f"Invalid pipeline bundle spec format: {pipeline_format}. Valid formats are: {valid_formats}")

            if pipeline_format and pipeline_format != self.pipeline_bundle_spec_format and not allow_override:
                raise ValueError(f"Pipeline bundle spec format has been set at global framework level as {self.pipeline_bundle_spec_format}. Override has been disabled.")
            
            if pipeline_format and allow_override:
                self.pipeline_bundle_spec_format = pipeline_format

        self.logger.info("Pipeline bundle spec format: %s", self.pipeline_bundle_spec_format)

    def _init_substitution_manager(self) -> None:
        """Initialize the substitution manager."""
        self.logger.info("Initializing Substitution Manager...")
        
        workspace_env = self.pipeline_details.workspace_env or ""
        
        # Build framework substitutions paths
        framework_subs_paths = [
            os.path.join(self.framework_path, FrameworkPaths.CONFIG_PATH, workspace_env + path) 
            for path in FrameworkPaths.GLOBAL_SUBSTITUTIONS
        ]
        self.logger.info("Framework substitutions paths: %s", framework_subs_paths)
        
        # Build pipeline substitutions paths
        suffixes = utility.get_format_suffixes(self.pipeline_bundle_spec_format, "substitutions")
        pipeline_subs_paths = [os.path.join(
            self.bundle_path, PipelineBundlePaths.PIPELINE_CONFIGS_PATH, workspace_env + suffix
            ) for suffix in suffixes
        ]
        self.logger.info("Pipeline substitutions paths: %s", pipeline_subs_paths)
        
        self.substitution_manager = SubstitutionManager(
            framework_substitutions_paths=framework_subs_paths,
            pipeline_substitutions_paths=pipeline_subs_paths,
            additional_tokens=self.pipeline_details.__dict__
        )
        self.logger.debug("Loaded substitution config: %s", self.substitution_manager._substitutions_config)

        # Initialize substitution manager singleton
        pipeline_config.initialize_substitution_manager(self.substitution_manager)

    def _init_secrets_manager(self) -> None:
        """Initialize the secrets manager."""
        self.logger.info("Initializing Secrets Manager...")
        
        workspace_env = self.pipeline_details.workspace_env or ""
        
        # Build framework secrets paths
        framework_secrets_config_paths = [
            os.path.join(self.framework_path, FrameworkPaths.CONFIG_PATH, workspace_env + path)
            for path in FrameworkPaths.GLOBAL_SECRETS
        ]
        
        # Build pipeline secrets paths
        suffixes = utility.get_format_suffixes(self.pipeline_bundle_spec_format, "secrets")
        pipeline_secrets_configs_paths = [os.path.join(
            self.bundle_path, PipelineBundlePaths.PIPELINE_CONFIGS_PATH, workspace_env + suffix
            ) for suffix in suffixes
        ]
        
        secrets_validator_path = os.path.join(
            self.framework_path, FrameworkPaths.SECRETS_SCHEMA_PATH
        )

        self.secrets_manager = SecretsManager(
            json_validation_schema_path=secrets_validator_path,
            framework_secrets_config_paths=framework_secrets_config_paths,
            pipeline_secrets_config_paths=pipeline_secrets_configs_paths
        )

    def _init_dataflow_specs(self) -> None:
        """Initialize dataflow specifications."""
        self.logger.info("Initializing Dataflow Spec Builder...")

        dataflow_spec_version = self.pipeline_config.get("dataflow_spec_version", None)
        dataflow_spec_builder_max_workers = self.pipeline_config.get(
            FrameworkSettings.OVERRIDE_MAX_WORKERS_KEY,
            self.default_max_workers
        )
        
        self.dataflow_specs = DataflowSpecBuilder(
            bundle_path=self.bundle_path,
            framework_path=self.framework_path,
            filters=self.dataflow_spec_filters,
            secrets_manager=self.secrets_manager,
            ignore_validation_errors=self.ignore_validation_errors,
            dataflow_spec_version=dataflow_spec_version,
            max_workers=dataflow_spec_builder_max_workers,
            spec_file_format=self.pipeline_bundle_spec_format
        ).build()
        
        if not self.dataflow_specs:
            raise ValueError(f"No dataflow specifications found in: {self.bundle_path}")

    def _setup_operational_metadata(self) -> None:
        """Set up operational metadata schema."""
        self.logger.info("Initializing Operational Metadata...")
        layer = self.pipeline_details.pipeline_layer
        if not layer:
            self.logger.info("Layer not set in pipeline, skipping operational metadata...")
            self.operational_metadata_schema = None
            return

        self.logger.info("Operational Metadata: layer set to %s", layer)
        metadata_path = os.path.join(self.framework_path, f"config/operational_metadata_{layer}.json")
        self.logger.info("Operational Metadata Path: %s", metadata_path)
        metadata_json = utility.get_json_from_file(metadata_path, False)
        self.operational_metadata_schema = (
            T.StructType.fromJson(metadata_json) if metadata_json else None
        )

        # Initialize operational metadata schema singleton
        pipeline_config.initialize_operational_metadata_schema(self.operational_metadata_schema)

    def _apply_spark_config(self) -> None:
        """Apply Spark configuration settings."""
        spark_config = self.pipeline_config.get("spark_config", {})
        if spark_config:
            self.logger.info("Initializing Spark Configs...")
            for prop, value in spark_config.items():
                self.logger.info("Set Spark Config: %s = %s", prop, value)
                self.spark.conf.set(prop, value)

    def _preload_extensions(self) -> None:
        """Add shared extension directories to sys.path."""
        # Framework extensions
        framework_extensions = os.path.join(self.framework_path, FrameworkPaths.EXTENSIONS_PATH)
        if os.path.exists(framework_extensions):
            sys.path.insert(0, framework_extensions)
            self.logger.info("Added framework extensions to sys.path: %s", framework_extensions)
        
        # Bundle extensions
        bundle_extensions = os.path.join(self.bundle_path, PipelineBundlePaths.EXTENSIONS_PATH)
        if os.path.exists(bundle_extensions):
            sys.path.insert(0, bundle_extensions)
            self.logger.info("Added bundle extensions to sys.path: %s", bundle_extensions)

    def initialize_pipeline(self) -> None:
        """Initialize the Spark Declarative Pipeline."""
        def create_dataflow(spec):
            """Create a dataflow from a specification."""
            return DataFlow(dataflow_spec=spec).create_dataflow()
        
        self.logger.info("Initializing Pipeline...")
        pipeline_builder_threading_disabled = self.pipeline_config.get(
            FrameworkSettings.PIPELINE_BUILDER_DISABLE_THREADING_KEY,
            True
        )
        
        self.logger.info("Processing Dataflow Specs...")
        if pipeline_builder_threading_disabled:
            self.logger.info("Pipeline Builder Threading Disabled, creating dataflows sequentially...")
            for spec in self.dataflow_specs:
                create_dataflow(spec)
        else:
            pipeline_builder_max_workers = self.pipeline_config.get(
                FrameworkSettings.OVERRIDE_MAX_WORKERS_KEY,
                self.default_max_workers
            )

            with ThreadPoolExecutor(max_workers=pipeline_builder_max_workers) as executor:
                self.logger.info("Pipeline Builder Threading Enabled. Max Workers: %s", pipeline_builder_max_workers)
                futures = [
                    executor.submit(create_dataflow, spec)
                    for spec in self.dataflow_specs
                ]
                for future in futures:
                    future.result()
