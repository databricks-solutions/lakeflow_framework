"""
Lakeflow Framework — A metadata-driven framework for building Databricks Spark Declarative Pipelines.

Primary import path:
    from lakeflow_framework import DLTPipelineBuilder
    from lakeflow_framework.dlt_pipeline_builder import DLTPipelineBuilder

Flat-deploy compat shims at ``src/utility.py``, ``src/constants.py`` etc. are kept until v1.0.0.
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__: str = _pkg_version("lakeflow-framework")
except PackageNotFoundError:
    # Flat deploy — package not pip-installed; fall back to the VERSION file.
    import os as _os
    _version_file = _os.path.join(_os.path.dirname(__file__), "..", "..", "VERSION")
    try:
        with open(_version_file) as _f:
            __version__ = _f.read().strip()
    except OSError:
        __version__ = "unknown"

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
    StagingTable,
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
    initialize_mandatory_table_properties,
)
from .secrets_manager import SecretsManager
from .substitution_manager import SubstitutionManager
from .constants import SystemColumns, MetaDataColumnDefs
from . import utility

__all__ = [
    "__version__",
    "DLTPipelineBuilder",
    "DataflowSpec",
    "DataflowSpecBuilder",
    "DataQualityExpectationBuilder",
    # Main classes
    "DataFlow",
    "FlowConfig",
    "FlowGroup",
    "BaseFlow",
    "StagingTable",
    "View",
    # Managers
    "SecretsManager",
    "SubstitutionManager",
    "TableMigrationManager",
    "QuarantineManager",
    # Types and enums
    "TargetType",
    "SinkType",
    # Constants
    "SystemColumns",
    "MetaDataColumnDefs",
    # Utilities
    "utility",
    # Pipeline config
    "get_spark",
    "get_logger",
    "get_operational_metadata_schema",
    "get_pipeline_details",
    "get_substitution_manager",
    "get_mandatory_table_properties",
    "initialize_core",
    "initialize_operational_metadata_schema",
    "initialize_pipeline_details",
    "initialize_substitution_manager",
    "initialize_mandatory_table_properties",
]
