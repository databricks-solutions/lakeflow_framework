"""
Lakeflow Framework - A framework for building Delta Live Tables pipelines.

This package provides tools and utilities for creating, managing, and orchestrating
Delta Live Tables (DLT) pipelines in Databricks.
"""

from .dataflow import (
    DataFlow,
    FlowConfig,
    FlowGroup,
    BaseFlow,
    QuarantineManager,
    TableMigrationManager,
    TargetType,
    SinkType,
    View,
    StagingTable
)
from .dataflow.dataflow_spec import DataflowSpec
from .dataflow_spec_builder import DataflowSpecBuilder, DataQualityExpectationBuilder
from .dlt_pipeline_builder import DLTPipelineBuilder
from .pipeline_config import (
    get_spark,
    get_logger,
    get_operational_metadata_schema,
    get_pipeline_details,
    get_substitution_manager,
    get_mandatory_table_properties,
    initialize_core,
    initialize_operational_metadata_schema,
    initialize_pipeline_details,
    initialize_substitution_manager,
    initialize_mandatory_table_properties
)
from .secrets_manager import SecretsManager
from .substitution_manager import SubstitutionManager
from .constants import SystemColumns, MetaDataColumnDefs
from . import utility

__all__ = [
    'DLTPipelineBuilder',
    'DataflowSpec',
    'DataflowSpecBuilder',
    'DataQualityExpectationBuilder',

    # Main classes
    'DataFlow', 'FlowConfig', 'FlowGroup', 'BaseFlow', 'StagingTable', 'View',
    
    # Managers
    'SecretsManager', 'SubstitutionManager', 'TableMigrationManager', 'QuarantineManager',
    
    # Types and Enums
    'TargetType', 'SinkType',
    
    # Constants
    'SystemColumns', 'MetaDataColumnDefs',
    
    # Utilities
    'utility',

    # Pipeline Config
    'get_spark', 'get_logger', 'get_operational_metadata_schema', 'get_pipeline_details', 'get_substitution_manager', 'get_mandatory_table_properties',
    'initialize_core', 'initialize_operational_metadata_schema', 'initialize_pipeline_details', 'initialize_substitution_manager', 'initialize_mandatory_table_properties'
]

__version__ = '0.1.0'
