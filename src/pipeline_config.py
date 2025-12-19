import os
import json
import logging
from typing import Dict, Any, Optional

from pyspark.dbutils import DBUtils
import pyspark.sql.types as T
from pyspark.sql import SparkSession

from constants import DLTPipelineSettingKeys
from pipeline_details import PipelineDetails
from substitution_manager import SubstitutionManager

# Module-level singletons
_spark = None
_dbutils = None
_logger = None
_substitution_manager = None
_pipeline_details = None
_mandatory_table_properties = None
_operational_metadata_schema = None


def initialize_core(
    spark: SparkSession,
    dbutils: DBUtils,
    logger: logging.Logger
) -> None:
    """Initialize the pipeline configuration."""
    global _spark, _dbutils, _logger
    _spark = spark
    _dbutils = dbutils
    _logger = logger


def initialize_substitution_manager(
    substitution_manager: SubstitutionManager
) -> None:
    """Initialize the substitution manager."""
    global _substitution_manager
    _substitution_manager = substitution_manager


def initialize_pipeline_details(
    pipeline_details: PipelineDetails
) -> None:
    """Initialize the pipeline details."""
    global _pipeline_details
    _pipeline_details = pipeline_details


def initialize_mandatory_table_properties(
    mandatory_table_properties: Dict[str, Any]
) -> None:
    """Initialize the mandatory table properties."""
    global _mandatory_table_properties
    _mandatory_table_properties = mandatory_table_properties

def initialize_mandatory_configuration() -> None:
    """Initialize the mandatory configuration."""
    verion_file = os.path.join(
        os.path.dirname(_spark.conf.get(DLTPipelineSettingKeys.FRAMEWORK_SOURCE_PATH, ".")),
        'VERSION'
    )
    with open(verion_file, mode='r', encoding='utf-8') as f:
        version = f.read().strip()

    mandatory_configuration = {
        'version': version
    }
    _spark.conf.set('tag.lakeflow_framework', json.dumps(mandatory_configuration))

def initialize_operational_metadata_schema(
    operational_metadata_schema: Optional[T.StructType] = None
) -> None:
    """Initialize the operational metadata schema."""
    global _operational_metadata_schema
    _operational_metadata_schema = operational_metadata_schema

def initialize_table_migration(
    table_migration_state_volume_path: str
) -> None:
    """Initialize the table migration state volume path."""
    global _table_migration_state_volume_path
    _table_migration_state_volume_path = table_migration_state_volume_path


def get_spark() -> SparkSession:
    """Get the Spark instance."""
    if _spark is None:
        raise RuntimeError("Spark has not been initialized. Call initialize_pipeline_config() first.")
    return _spark


def get_dbutils() -> DBUtils:
    """Get the DBUtils instance."""
    if _dbutils is None:
        raise RuntimeError("DBUtils has not been initialized. Call initialize_pipeline_config() first.")
    return _dbutils


def get_logger() -> logging.Logger:
    """Get the logger instance."""
    if _logger is None:
        raise RuntimeError("Logger has not been initialized. Call initialize_pipeline_config() first.")
    return _logger


def get_substitution_manager() -> SubstitutionManager:
    """Get the substitution manager instance."""
    if _substitution_manager is None:
        raise RuntimeError("Substitution manager has not been initialized. Call initialize_pipeline_config() first.")
    return _substitution_manager


def get_pipeline_details() -> PipelineDetails:
    """Get the pipeline details instance."""
    if _pipeline_details is None:
        raise RuntimeError("Pipeline details has not been initialized. Call initialize_pipeline_config() first.")
    return _pipeline_details


def get_mandatory_table_properties() -> Dict[str, Any]:
    """Get the mandatory table properties."""
    if _mandatory_table_properties is None:
        raise RuntimeError("Mandatory table properties have not been initialized. Call initialize_pipeline_config() first.")
    return _mandatory_table_properties


def get_operational_metadata_schema() -> Optional[T.StructType]:
    """Get the operational metadata schema."""
    return _operational_metadata_schema


def get_table_migration_state_volume_path() -> str:
    """Get the table migration state volume path."""
    if _table_migration_state_volume_path is None:
        raise RuntimeError("Table migration state volume path has not been initialized. Call initialize_pipeline_config() first.")
    return _table_migration_state_volume_path