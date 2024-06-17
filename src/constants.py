from utility import merge_dicts

# Framework Paths
EXPECTATIONS_SPEC_SCHEMA_PATH = "./schemas/expectations.json"
FLOW_GROUP_SPEC_SCHEMA_PATH = "./schemas/flow_group.json"
MAIN_SPEC_SCHEMA_PATH = "./schemas/main.json"

FLOW_GROUP_FILE_SUFFIX = "_flow.json"
MAIN_SPEC_FILE_SUFFIX = "_main.json"

# Pipeline Bundle Paths
DATAFLOWS_BASE_PATH = "./dataflows"
DML_PATH = "./dml"
DQE_PATH = "./expectations"
SCHEMA_PATH = "./schemas"
PIPELINE_CONFIGS_PATH = "./pipeline_configs"

# System / Reserved Columns
CDF_COLUMN_NAMES = {
    "CDF_CHANGE_TYPE": "_change_type",
    "CDF_COMMIT_VERSION": "_commit_version",
    "CDF_COMMIT_TIMESTAMP": "_commit_timestamp"
}

SCD2_COLUMN_NAMES = {
    "SCD2_START_AT": "__START_AT",
    "SCD2_END_AT": "__END_AT",   
}

RESERVED_COLUMN_NAMES = merge_dicts(CDF_COLUMN_NAMES, SCD2_COLUMN_NAMES)

# Metadata Column Definitions
METADATA_COLUMN_DEFINITIONS = {
    "QUARANTINE_FLAG": {
        "name": "is_quarantined",
        "type": "boolean",
        "nullable": True,
        "metadata": {}
    }
}