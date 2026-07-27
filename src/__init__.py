"""
Compat shim — src/ package init.

Delegates all public symbols to ``lakeflow_framework``.
This file is kept so that any code that does ``import src`` or uses ``src``
as a package (unusual) continues to resolve correctly while ``src/`` is on
``sys.path`` and the canonical import path is ``lakeflow_framework.*``.
"""

from lakeflow_framework import (  # noqa: F401
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
    DataflowSpec,
    DataflowSpecBuilder,
    DataQualityExpectationBuilder,
    DLTPipelineBuilder,
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
    SecretsManager,
    SubstitutionManager,
    SystemColumns,
    MetaDataColumnDefs,
    utility,
    __version__,
)
