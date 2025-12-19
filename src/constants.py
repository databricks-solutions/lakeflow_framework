from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class FrameworkSettings:
    """
    FrameworkSettings is a class that contains constants for the framework settings.
    """
    OVERRIDE_MAX_WORKERS_KEY: str = "override_max_workers"
    PIPELINE_BUILDER_DISABLE_THREADING_KEY: str = "pipeline_builder_disable_threading"


@dataclass(frozen=True)
class DLTPipelineSettingKeys:
    """
    DLTPipelineSettingKeys is a class that contains constants for various Pipeline settings keys.
    """
    BUNDLE_SOURCE_PATH: str = "bundle.sourcePath"
    BUNDLE_TARGET: str = "bundle.target"
    FRAMEWORK_SOURCE_PATH: str = "framework.sourcePath"
    LOG_LEVEL: str = "logLevel"
    LOGICAL_ENV: str = "logicalEnv"
    PIPELINE_CATALOG: str = "pipelines.catalog"
    PIPELINE_FILE_FILTER: str = "pipeline.fileFilter"
    PIPELINE_FILTER_DATA_FLOW_GROUP: str = "pipeline.dataFlowGroupFilter"
    PIPELINE_FILTER_DATA_FLOW_ID: str = "pipeline.dataFlowIdFilter"
    PIPELINE_FILTER_FLOW_GROUP_ID: str = "pipeline.flowGroupIdFilter"
    PIPELINE_FILTER_TARGET_TABLE: str = "pipeline.targetTableFilter"
    PIPELINE_ID: str = "pipelines.id"
    PIPELINE_IGNORE_VALIDATION_ERRORS: str = "pipeline.ignoreValidationErrors"
    PIPELINE_LAYER: str = "pipeline.layer"
    PIPELINE_TARGET: str = "pipelines.target"
    PIPELINE_SCHEMA: str = "pipelines.schema"
    WORKSPACE_HOST: str = "workspace.host"


@dataclass(frozen=True)
class FrameworkPaths:
    """
    FrameworkPaths is a class that contains constants for various paths and file masks used in the Lakeflow Framework.

    Attributes:
        CONFIG_PATH (str): Path to the config directory.
        EXTENSIONS_PATH (str): The path for extensions.
        GLOBAL_CONFIG (tuple): Paths to the global configuration files.
        GLOBAL_SUBSTITUTIONS (tuple): Paths to the global substitutions files.
        GLOBAL_SECRETS (tuple): Paths to the global secrets files.
        DATAFLOW_SPEC_MAPPING_PATH (str): Path to the dataflow spec mapping directory.
        MAIN_SPEC_SCHEMA_PATH (str): Path to the main specification schema file.
        FLOW_GROUP_SPEC_SCHEMA_PATH (str): Path to the flow group specification schema file.
        EXPECTATIONS_SPEC_SCHEMA_PATH (str): Path to the expectations specification schema file.
        SECRETS_SCHEMA_PATH (str): Path to the secrets specification schema file.
        TEMPLATE_DEFINITION_SPEC_SCHEMA_PATH (str): Path to the template definition specification schema file.
        TEMPLATE_SPEC_SCHEMA_PATH (str): Path to the template specification schema file.
    """
    CONFIG_PATH: str = "./config"
    EXTENSIONS_PATH: str = "./extensions"
    GLOBAL_CONFIG: tuple = ("./config/global.json", "./config/global.yaml", "./config/global.yml")
    GLOBAL_SUBSTITUTIONS: tuple = ("_substitutions.json", "_substitutions.yaml", "_substitutions.yml")
    GLOBAL_SECRETS: tuple = ("_secrets.json", "_secrets.yaml", "_secrets.yml")
    DATAFLOW_SPEC_MAPPING_PATH: str = "./config/dataflow_spec_mapping"
    REQUIREMENTS_FILE: str = "requirements.txt"

    # Spec schema definitions paths
    SPEC_MAPPING_SCHEMA_PATH: str = "./schemas/spec_mapping.json"
    MAIN_SPEC_SCHEMA_PATH: str = "./schemas/main.json"
    FLOW_GROUP_SPEC_SCHEMA_PATH: str = "./schemas/flow_group.json"
    EXPECTATIONS_SPEC_SCHEMA_PATH: str = "./schemas/expectations.json"
    SECRETS_SCHEMA_PATH: str = "./schemas/secrets.json"
    TEMPLATE_DEFINITION_SPEC_SCHEMA_PATH: str = "./schemas/spec_template_definition.json"
    TEMPLATE_SPEC_SCHEMA_PATH: str = "./schemas/spec_template.json"
 

class SupportedSpecFormat(str, Enum):
    """Supported specification file formats."""
    JSON = "json"
    YAML = "yaml"


@dataclass(frozen=True)
class PipelineBundleSuffixesJson:
    """
    PipelineBundleSuffixesJson is a class that contains constants for various file suffixes used in the Pipeline Bundles in JSON format.
    """
    MAIN_SPEC_FILE_SUFFIX: tuple = ("_main.json")
    FLOW_GROUP_FILE_SUFFIX: tuple = ("_flow.json")
    EXPECTATIONS_FILE_SUFFIX: tuple = (".json")
    SECRETS_FILE_SUFFIX: tuple = ("_secrets.json")
    SUBSTITUTIONS_FILE_SUFFIX: tuple = ("_substitutions.json")


@dataclass(frozen=True)
class PipelineBundleSuffixesYaml:
    """
    PipelineBundleSuffixesYaml is a class that contains constants for various file suffixes used in the Pipeline Bundles in YAML format.
    """
    MAIN_SPEC_FILE_SUFFIX: tuple = ("_main.yaml", "_main.yml")
    FLOW_GROUP_FILE_SUFFIX: tuple = ("_flow.yaml", "_flow.yml")
    EXPECTATIONS_FILE_SUFFIX: tuple = ("_expectations.yaml", "_expectations.yml")
    SECRETS_FILE_SUFFIX: tuple = ("_secrets.yaml", "_secrets.yml")
    SUBSTITUTIONS_FILE_SUFFIX: tuple = ("_substitutions.yaml", "_substitutions.yml")


@dataclass(frozen=True)
class PipelineBundlePaths:
    """
    PipelineBundlePaths is a class that contains constants for various paths and file masks
    used in the Pipeline Bundles.

    Attributes:
        DATAFLOWS_BASE_PATH (str): The base path for dataflows.
        DATAFLOW_SPEC_PATH (str): The path for dataflow specifications.
        DML_PATH (str): The path for DML (Data Manipulation Language) files.
        DQE_PATH (str): The path for data quality expectations.
        EXTENSIONS_PATH (str): The path for extensions.
        GLOBAL_CONFIG_FILE (tuple): The file names for global configuration files.
        PIPELINE_CONFIGS_PATH (str): The path for pipeline configuration files.
        PYTHON_FUNCTION_PATH (str): The path for python functions.
        SCHEMA_PATH (str): The path for schema files.
        TEMPLATE_PATH (str): Path to the template directory.
    """
    DATAFLOWS_BASE_PATH: str = "./dataflows"
    DATAFLOW_SPEC_PATH: str = "dataflowspec"
    DML_PATH: str = "./dml"
    DQE_PATH: str = "./expectations"
    EXTENSIONS_PATH: str = "./extensions"
    GLOBAL_CONFIG_FILE: tuple = ("./global.json", "./global.yaml", "./global.yml")
    PIPELINE_CONFIGS_PATH: str = "./pipeline_configs"
    PYTHON_FUNCTION_PATH: str = "./python_functions"
    SCHEMA_PATH: str = "./schemas"
    TEMPLATE_PATH: str = "./templates"
    REQUIREMENTS_FILE: str = "requirements.txt"


class SystemColumns:
    """
    SystemColumns is a container for constants related to SDP and Framework system columns.

    Classes:
        CDFColumns (Enum): Contains constants for Change Data Feed (CDF) system columns.
        SCD2Columns (Enum): Contains constants for Slowly Changing Dimension Type 2 (SCD2) system columns.
    """
    class CDFColumns(Enum):
        """Change Data Feed system columns."""
        CDF_CHANGE_TYPE = "_change_type"
        CDF_COMMIT_VERSION = "_commit_version"
        CDF_COMMIT_TIMESTAMP = "_commit_timestamp"

    class SCD2Columns(Enum):
        """SCD2 system columns."""
        SCD2_START_AT = "__START_AT"
        SCD2_END_AT = "__END_AT"

class MetaDataColumnDefs:
    """MetaDataColumnDefs is a class that contains constants for all Framework metadata columns."""

    QUARANTINE_FLAG = {
        "name": "is_quarantined",
        "type": "boolean",
        "nullable": True,
        "metadata": {}
    }

FILE_METADATA_COLUMN = "_metadata"
