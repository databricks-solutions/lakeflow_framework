---
name: dataflow-spec-builder
description: "Generates Data Flow Spec pipeline bundles using the metadata-driven framework from github.com/databricks-solutions/lakeflow_framework. Creates Data Flow Specs (standard, flows, materialized views), schemas, expectations, SQL transforms, Python extensions, substitutions, templates, pipeline resource YAMLs, and databricks.yml from natural language. Covers CDC (SCD1/2), data quality, quarantine, liquid clustering, multi-source streaming, table migration, secrets, soft deletes, operational metadata, and DABs deployment. This is NOT native Lakeflow Declarative Pipelines — it is the Data Flow Spec Framework that wraps SDP with configuration-over-code."
---

# Data Flow Spec Builder

Generate complete, production-ready pipeline bundles using the [Data Flow Spec Framework](https://github.com/databricks-solutions/lakeflow_framework) (v0.4.0) from natural language descriptions. This is a metadata-driven data engineering framework that wraps Databricks Spark Declarative Pipelines (SDP) with a configuration-over-code approach using JSON/YAML Data Flow Specs.

> **IMPORTANT:** This skill builds pipelines using the **Data Flow Spec Framework** (`databricks-solutions/lakeflow_framework`), NOT native Lakeflow Declarative Pipelines (DLT). The Data Flow Spec Framework is a metadata-driven wrapper that uses JSON configuration files called "Data Flow Specs" to define pipelines declaratively.

## When to Use

- User says "generate a Data Flow Spec", "use the Data Flow Spec framework", "scaffold a DFS pipeline bundle", or "dataflow spec builder"
- User says "use the metadata-driven framework" or "databricks-solutions/lakeflow_framework"
- User needs metadata-driven SDP pipelines with JSON/YAML Data Flow Spec configuration files
- User wants CDC (SCD1/2), data quality expectations, quarantine, or multi-source streaming via Data Flow Specs
- User asks for medallion architecture pipelines using Data Flow Specs (not native DLT/Lakeflow syntax)
- User wants to create reusable pipeline templates for multiple similar tables using the Data Flow Spec Framework
- User needs environment-portable pipelines with substitutions (dev/sit/prod) using Data Flow Spec configuration
- User references `databricks-solutions/lakeflow_framework` or "DFS framework"

## When NOT to Use

- User wants native Lakeflow Declarative Pipelines (DLT) with Python/SQL decorators like `@dlt.table` or `CREATE STREAMING TABLE` — that is native DLT, not this framework
- User wants to write pipeline code directly without JSON/YAML configuration files

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `description` | Yes | Natural language description of the pipeline(s) to build |
| `catalog` | Yes | Unity Catalog name (e.g., `main`) |
| `schema` | Yes | Target schema (e.g., `energy_workshop`) |
| `framework_source_path` | No | Workspace path where the framework bundle is deployed (default: `/Workspace/Users/{owner}/.bundle/lakeflow_framework/dev/current/files/src`) |
| `spec_format` | No | `json` (default) or `yaml` |
| `layer` | No | Medallion layer: `bronze`, `silver`, or `gold` |
| `pattern` | No | Pipeline pattern to use (see Patterns section) |
| `environments` | No | List of target environments for substitutions (e.g., `dev,sit,prod`) |

## Workflow

1. **Analyze request** — Determine data flow type (standard / flows / materialized_view), pattern, layer, sources, targets, and features needed
2. **Generate Data Flow Spec** — Create the main JSON/YAML spec file(s) with correct schema
3. **Generate schemas** — Create StructType JSON schema files for sources and targets
4. **Generate expectations** — Create data quality expectation files if DQ is needed
5. **Generate SQL transforms** — Create SQL files for silver/gold transforms
6. **Generate Python extensions** — Create custom source/transform/sink modules if complex logic is needed
7. **Generate substitutions** — Create environment-specific substitution configs
8. **Generate pipeline resource YAML** — Create `resources/*.yml` with pipeline definition and filters
9. **Generate databricks.yml** — Create the DAB bundle definition
10. **Generate templates** — If the user has multiple similar tables, create reusable Lakeflow templates
11. **Deploy** — Optionally run `databricks bundle deploy` and `databricks bundle run`

---

## Architecture Overview

The Lakeflow Framework has **two bundle types**:

### Framework Bundle (deployed once per workspace)
Contains the core engine code. Deployed to workspace files via:
```bash
cd lakeflow_framework
databricks bundle deploy -t dev
```

### Pipeline Bundle (one per project/domain)
Contains your Data Flow Specs, schemas, expectations, transforms, and pipeline definitions:
```
my_pipeline_bundle/
├── databricks.yml              # DAB bundle definition
├── resources/
│   └── my_pipeline.yml         # SDP pipeline definition(s)
└── src/
    ├── dataflows/
    │   └── my_table/
    │       ├── dataflowspec/
    │       │   └── my_table_main.json    # Data Flow Spec
    │       ├── schemas/
    │       │   └── my_table_schema.json  # StructType schema
    │       ├── expectations/
    │       │   └── my_table_dqe.json     # DQ expectations
    │       └── dml/
    │           └── transform.sql         # SQL transforms
    ├── extensions/                       # Python extensions (optional)
    │   ├── sources.py
    │   ├── transforms.py
    │   └── sinks.py
    ├── templates/                        # Reusable templates (optional)
    │   └── my_template.json
    └── pipeline_configs/
        ├── dev_substitutions.json        # Env substitutions
        └── pipeline_config.json          # Pipeline-level config
```

---

## Data Flow Types

### 1. Standard Data Flow (Bronze / 1:1 Ingestion)

Best for: ingestion, basic 1:1 loads, single-source-to-single-target.

```json
{
    "dataFlowId": "<unique_id>",
    "dataFlowGroup": "<group_name>",
    "dataFlowType": "standard",
    "sourceType": "<cloudFiles|delta|deltaJoin|kafka>",
    "sourceSystem": "<source_system_name>",
    "sourceViewName": "v_<view_name>",
    "sourceDetails": {
        "database": "<catalog.schema>",
        "table": "<source_table>",
        "cdfEnabled": false,
        "schemaPath": "schemas/<schema_file>.json",
        "selectExp": ["*"],
        "whereClause": [],
        "readerOptions": {}
    },
    "mode": "<stream|batch>",
    "targetFormat": "delta",
    "targetDetails": {
        "table": "<target_table>",
        "schemaPath": "schemas/<target_schema>.json",
        "tableProperties": {
            "delta.autoOptimize.optimizeWrite": "true",
            "delta.autoOptimize.autoCompact": "true"
        },
        "partitionColumns": [],
        "clusterByColumns": [],
        "clusterByAuto": false
    },
    "cdcSettings": {
        "keys": ["<primary_key>"],
        "sequence_by": "<timestamp_column>",
        "scd_type": "<1|2>",
        "where": "",
        "ignore_null_updates": true,
        "except_column_list": [],
        "apply_as_deletes": "",
        "track_history_column_list": [],
        "track_history_except_column_list": []
    },
    "dataQualityExpectationsEnabled": false,
    "dataQualityExpectationsPath": "",
    "quarantineMode": "<off|flag|table>",
    "quarantineTargetDetails": {
        "targetFormat": "delta",
        "table": "<quarantine_table>",
        "tableProperties": {}
    },
    "tableMigrationDetails": {
        "enabled": false,
        "catalogType": "<hms|uc>",
        "autoStartingVersionsEnabled": true,
        "sourceDetails": {
            "sourceMigrateDelta": {
                "database": "<old_database>",
                "table": "<old_table>",
                "selectExp": [],
                "whereClause": [],
                "exceptColumns": []
            }
        }
    }
}
```

**Source Types for Standard:**
- `cloudFiles` — Auto Loader from UC Volumes or cloud storage (S3/ADLS/GCS)
- `delta` — Existing Delta table, optionally with CDF
- `deltaJoin` — Join multiple Delta tables (stream + static)
- `kafka` — Apache Kafka topics

**Source Details by Type:**

For `cloudFiles`:
```json
"sourceDetails": {
    "path": "/Volumes/<catalog>/<schema>/<volume>/<folder>/",
    "readerOptions": {
        "cloudFiles.format": "<csv|json|parquet|avro>",
        "header": "true",
        "cloudFiles.inferColumnTypes": "true",
        "cloudFiles.schemaLocation": "<checkpoint_path>"
    },
    "schemaPath": "schemas/<name>.json"
}
```

For `delta`:
```json
"sourceDetails": {
    "database": "<catalog>.<schema>",
    "table": "<table_name>",
    "cdfEnabled": true,
    "schemaPath": "schemas/<name>.json",
    "selectExp": ["col1", "col2", "CAST(col3 AS DATE) AS col3_date"],
    "whereClause": ["col1 IS NOT NULL"]
}
```

For `deltaJoin`:
```json
"sourceDetails": {
    "sources": [
        {
            "alias": "a",
            "database": "<catalog>.<schema>",
            "table": "<table_1>",
            "mode": "stream",
            "cdfEnabled": true
        },
        {
            "alias": "b",
            "database": "<catalog>.<schema>",
            "table": "<table_2>",
            "mode": "static"
        }
    ],
    "joinType": "<inner|left>",
    "joinCondition": "a.key_col = b.key_col",
    "selectExp": ["a.*", "b.description"]
}
```

For `kafka`:
```json
"sourceDetails": {
    "readerOptions": {
        "kafka.bootstrap.servers": "<broker:9092>",
        "subscribe": "<topic_name>",
        "startingOffsets": "earliest"
    },
    "schemaPath": "schemas/<name>.json"
}
```

### 2. Flows Data Flow (Silver / Multi-Source Streaming)

Best for: complex transformations, multiple sources merging into one target, silver/gold layers.

```json
{
    "dataFlowId": "<unique_id>",
    "dataFlowGroup": "<group_name>",
    "dataFlowType": "flow",
    "targetFormat": "delta",
    "targetDetails": {
        "table": "<target_table>",
        "schemaPath": "",
        "tableProperties": {
            "delta.enableChangeDataFeed": "true"
        },
        "partitionColumns": [],
        "clusterByColumns": []
    },
    "cdcSettings": {
        "keys": ["<primary_key>"],
        "sequence_by": "<timestamp_column>",
        "scd_type": "<1|2>",
        "where": "",
        "ignore_null_updates": true,
        "except_column_list": []
    },
    "dataQualityExpectationsEnabled": false,
    "quarantineMode": "off",
    "quarantineTargetDetails": {},
    "flowGroups": [
        {
            "flowGroupId": "<flow_group_id>",
            "stagingTables": {
                "<staging_table_name>": {
                    "type": "<ST|MV>",
                    "schemaPath": "",
                    "partitionColumns": [],
                    "tableProperties": {},
                    "cdcSettings": {}
                }
            },
            "flows": {
                "<flow_name>": {
                    "enabled": true,
                    "flowType": "<append_view|append_sql|merge>",
                    "flowDetails": {
                        "targetTable": "<staging_or_target_table>",
                        "sourceView": "<view_name>"
                    },
                    "views": {
                        "<view_name>": {
                            "mode": "<stream|batch>",
                            "sourceType": "<cloudFiles|delta|deltaJoin|sql|python>",
                            "sourceDetails": {
                                "database": "<catalog>.<schema>",
                                "table": "<source_table>",
                                "cdfEnabled": true,
                                "selectExp": ["*"],
                                "whereClause": []
                            }
                        }
                    }
                }
            }
        }
    ]
}
```

**Flow Types:**
- `append_view` — Append data from a source view to a staging/target table
- `append_sql` — Append data using a raw SQL statement (use `sqlPath` in flowDetails instead of `sourceView`)
- `merge` — CDC merge from a source view/staging table to the target table

**Staging Table Types:**
- `ST` — Streaming Table
- `MV` — Materialized View

**Multi-Source Streaming Pattern:** Stream multiple sources into a single staging table via `append_view` flows, then `merge` the staging table into the final target. Flow groups can be added/removed over time without requiring a full pipeline refresh.

### 3. Materialized View Data Flow (Gold / Aggregations)

Best for: precomputed aggregations, complex joins, gold layer KPIs.

```json
{
    "dataFlowId": "<unique_id>",
    "dataFlowGroup": "<group_name>",
    "dataFlowType": "materialized_view",
    "materializedViews": {
        "<mv_table_name>": {
            "sourceView": {
                "sourceViewName": "v_<source_view>",
                "sourceType": "<delta|python|sql>",
                "sourceDetails": {
                    "database": "<catalog>.<schema>",
                    "table": "<source_table>",
                    "cdfEnabled": false
                }
            },
            "sqlPath": "<relative_path_to_sql_file>",
            "sqlStatement": "<inline_sql_or_empty>",
            "tableDetails": {
                "database": "<catalog>.<schema>",
                "schemaPath": "schemas/<name>.json",
                "tableProperties": {
                    "delta.autoOptimize.optimizeWrite": "true"
                },
                "partitionColumns": [],
                "clusterByColumns": ["<col1>", "<col2>"],
                "clusterByAuto": false,
                "comment": "<description>"
            },
            "dataQualityExpectationsEnabled": false,
            "dataQualityExpectationsPath": "",
            "quarantineMode": "off",
            "quarantineTargetDetails": {}
        }
    }
}
```

**Materialized View Source Options (pick one per MV):**
1. `sourceView` — Define a source view over a Delta table or Python function
2. `sqlPath` — Path to a `.sql` file containing the MV query
3. `sqlStatement` — Inline SQL string

Multiple materialized views can be defined in a single Data Flow Spec by adding more keys under `materializedViews`.

---

## Feature Reference

### CDC — Change Data Capture (SCD Type 1 & 2)

Add `cdcSettings` to any standard or flows data flow spec:

```json
"cdcSettings": {
    "keys": ["customer_id"],
    "sequence_by": "updated_timestamp",
    "scd_type": "2",
    "where": "",
    "ignore_null_updates": true,
    "except_column_list": ["_metadata", "load_timestamp"],
    "apply_as_deletes": "DELETE_FLAG = true",
    "track_history_column_list": [],
    "track_history_except_column_list": ["_metadata"]
}
```

| Field | Description |
|-------|-------------|
| `keys` | Primary key column(s) to identify records |
| `sequence_by` | Timestamp column for ordering CDC events |
| `scd_type` | `"1"` (overwrite) or `"2"` (history tracking with `__START_AT` / `__END_AT`) |
| `apply_as_deletes` | SQL expression — when true, treat the event as a DELETE |
| `ignore_null_updates` | If true, null values in updates don't overwrite existing data |
| `except_column_list` | Columns to exclude from the upsert |
| `track_history_column_list` | Explicit list of columns to track history for (SCD2 only) |
| `track_history_except_column_list` | Columns to exclude from history tracking (SCD2 only) |

### CDC from Historical Snapshots

For snapshot-based CDC ingestion:
```json
"cdcSnapshotSettings": {
    "source": {
        "format": "parquet",
        "path": "/Volumes/main/raw/snapshots/{version}/",
        "versionType": "datetime",
        "datetimeFormat": "yyyyMMdd",
        "startingVersion": "20240101",
        "readerOptions": {},
        "schemaPath": "schemas/snapshot_schema.json",
        "selectExp": ["*"],
        "filter": "active = true",
        "recursiveFileLookup": false
    }
}
```

For table-based snapshot CDC:
```json
"cdcSnapshotSettings": {
    "source": {
        "table": "main.raw.daily_snapshot",
        "versionColumn": "snapshot_date",
        "startingVersion": "2024-01-01",
        "selectExp": ["*"]
    }
}
```

### CDF — Change Data Feed

Enable CDF reading on a source:
```json
"sourceDetails": {
    "database": "main.bronze",
    "table": "customer",
    "cdfEnabled": true
}
```

Enable CDF on a target table:
```json
"targetDetails": {
    "table": "silver_customer",
    "tableProperties": {
        "delta.enableChangeDataFeed": "true"
    }
}
```

### Data Quality — Expectations

Create an expectations file (`expectations/<table>_dqe.json`):
```json
{
    "expect": [
        {"name": "valid_id", "constraint": "customer_id IS NOT NULL", "tag": "completeness", "enabled": true},
        {"name": "valid_email", "constraint": "email LIKE '%@%.%'", "tag": "validity", "enabled": true}
    ],
    "expect_or_drop": [
        {"name": "positive_amount", "constraint": "amount > 0", "tag": "range", "enabled": true}
    ],
    "expect_or_fail": [
        {"name": "unique_key", "constraint": "customer_id IS NOT NULL", "tag": "integrity", "enabled": true}
    ]
}
```

**Expectation types:**
- `expect` — Log violations but keep the record
- `expect_or_drop` — Drop records that violate
- `expect_or_fail` — Fail the entire pipeline if any record violates

Enable in the data flow spec:
```json
"dataQualityExpectationsEnabled": true,
"dataQualityExpectationsPath": "my_table_dqe.json"
```

### Data Quality — Quarantine

Three quarantine modes:
- `"off"` — No quarantine (default)
- `"flag"` — Add a `_quarantine` boolean column to the target table
- `"table"` — Write bad records to a separate quarantine table

```json
"quarantineMode": "table",
"quarantineTargetDetails": {
    "targetFormat": "delta",
    "table": "customer_quarantine",
    "tableProperties": {}
}
```

### Liquid Clustering

Enable automatic or manual clustering on target tables:

```json
"targetDetails": {
    "table": "silver_meter_readings",
    "clusterByColumns": ["customer_id", "reading_date"],
    "clusterByAuto": false
}
```

Or use automatic clustering (Databricks chooses optimal keys):
```json
"targetDetails": {
    "table": "silver_meter_readings",
    "clusterByAuto": true
}
```

### Schemas

Schemas are defined in StructType JSON format:
```json
{
    "type": "struct",
    "fields": [
        {"name": "customer_id", "type": "integer", "nullable": false, "metadata": {}},
        {"name": "name", "type": "string", "nullable": true, "metadata": {}},
        {"name": "email", "type": "string", "nullable": true, "metadata": {}},
        {"name": "created_at", "type": "timestamp", "nullable": true, "metadata": {}},
        {"name": "balance", "type": {"type": "decimal", "precision": 10, "scale": 2}, "nullable": true, "metadata": {}}
    ]
}
```

Or Text DDL format:
```
customer_id INT NOT NULL, name STRING, email STRING, created_at TIMESTAMP, balance DECIMAL(10,2)
```

Generate from an existing table:
```python
schema_json = spark.table("main.energy.raw_customers").schema.json()
```

### Substitutions

Create environment-specific config files (`src/pipeline_configs/<env>_substitutions.json`):

```json
{
    "tokens": {
        "bronze_schema": "main.bronze_energy",
        "silver_schema": "main.silver_energy",
        "gold_schema": "main.gold_energy",
        "landing_path": "/Volumes/main/energy/landing"
    },
    "prefix_suffix": {
        "database": {
            "suffix": "_{workspace_env}"
        }
    }
}
```

Use tokens in Data Flow Specs with curly braces: `{bronze_schema}`, `{landing_path}`.

**Reserved tokens:**
- `{workspace_env}` — The DABs target environment name (dev, sit, prod)

**Precedence:** Pipeline substitutions override framework-level substitutions.

### Templates

Create reusable patterns for multiple similar tables.

**Template definition** (`src/templates/<template_name>.json`):
```json
{
    "name": "bronze_ingestion_template",
    "parameters": {
        "dataFlowId": {"type": "string", "required": true},
        "sourceTable": {"type": "string", "required": true},
        "targetTable": {"type": "string", "required": true},
        "schemaPath": {"type": "string", "required": true},
        "keyColumns": {"type": "list", "required": true},
        "sequenceBy": {"type": "string", "required": true}
    },
    "template": {
        "dataFlowId": "${param.dataFlowId}",
        "dataFlowGroup": "bronze_energy",
        "dataFlowType": "standard",
        "sourceType": "delta",
        "sourceSystem": "smartgrid",
        "sourceViewName": "v_${param.sourceTable}",
        "sourceDetails": {
            "database": "{bronze_schema}",
            "table": "${param.sourceTable}",
            "cdfEnabled": true,
            "schemaPath": "${param.schemaPath}"
        },
        "mode": "stream",
        "targetFormat": "delta",
        "targetDetails": {
            "table": "${param.targetTable}",
            "tableProperties": {
                "delta.autoOptimize.optimizeWrite": "true"
            }
        },
        "cdcSettings": {
            "keys": "${param.keyColumns}",
            "sequence_by": "${param.sequenceBy}",
            "scd_type": "1"
        }
    }
}
```

**Template usage** (`src/dataflows/<group>/dataflowspec/<name>_main.json`):
```json
{
    "template": "bronze_ingestion_template",
    "parameterSets": [
        {
            "dataFlowId": "customers_bronze",
            "sourceTable": "raw_customers",
            "targetTable": "bronze_customers",
            "schemaPath": "schemas/customers_schema.json",
            "keyColumns": ["customer_id"],
            "sequenceBy": "updated_at"
        },
        {
            "dataFlowId": "billing_bronze",
            "sourceTable": "raw_billing",
            "targetTable": "bronze_billing",
            "schemaPath": "schemas/billing_schema.json",
            "keyColumns": ["bill_id"],
            "sequenceBy": "bill_date"
        }
    ]
}
```

**Parameter types:** `string`, `integer`, `boolean`, `list`, `object`

### Python Extensions

Custom Python modules in `src/extensions/`:

**Source extension** (`sources.py`):
```python
from pyspark.sql import DataFrame, SparkSession
from typing import Dict

def get_custom_source(spark: SparkSession, tokens: Dict) -> DataFrame:
    source_table = tokens["sourceTable"]
    return spark.readStream.option("readChangeFeed", "true").table(source_table)
```

Reference in spec:
```json
"sourceType": "python",
"sourceDetails": {
    "tokens": {"sourceTable": "{bronze_schema}.customer"},
    "pythonModule": "sources.get_custom_source"
}
```

**Transform extension** (`transforms.py`):
```python
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def clean_and_enrich(df: DataFrame) -> DataFrame:
    return df.withColumn("processed_at", F.current_timestamp()).dropDuplicates(["id"])
```

Reference in spec:
```json
"sourceDetails": {
    "database": "{bronze_schema}",
    "table": "customer",
    "pythonTransform": {
        "module": "transforms.clean_and_enrich"
    }
}
```

**Sink extension** (`sinks.py`):
```python
from pyspark.sql import DataFrame
from typing import Dict

def write_to_api(df: DataFrame, batch_id: int, tokens: Dict) -> None:
    import requests
    api_url = tokens["apiUrl"]
    records = df.toJSON().collect()
    for record in records:
        requests.post(api_url, json=record)
```

Reference in spec:
```json
"targetFormat": "foreach_batch_sink",
"targetDetails": {
    "name": "api_sink",
    "type": "python_function",
    "config": {
        "module": "sinks.write_to_api",
        "tokens": {"apiUrl": "https://api.example.com/data"}
    }
}
```

### Python Function Transforms

Inline Python transforms via file path (alternative to extensions):

```json
"sourceDetails": {
    "database": "{bronze_schema}",
    "table": "meter_readings",
    "pythonTransform": {
        "path": "python_functions/clean_readings.py",
        "functionName": "clean_readings"
    }
}
```

### Soft Deletes

Enable soft deletes instead of physical deletes:
```json
"cdcSettings": {
    "keys": ["customer_id"],
    "sequence_by": "updated_at",
    "scd_type": "1",
    "apply_as_deletes": "operation = 'DELETE'",
    "soft_delete": true
}
```

### Operational Metadata

The framework automatically adds operational metadata columns. Disable per spec:
```json
"operationalMetadata": {
    "enabled": false
}
```

Or disable at target table level:
```json
"targetDetails": {
    "table": "my_table",
    "operationalMetadata": false
}
```

### Mandatory Table Properties

Set in framework config (`src/config/mandatory_table_properties.json`):
```json
{
    "mandatory_properties": {
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.enableChangeDataFeed": "true"
    }
}
```

### Spark Configuration

Per-materialized-view Spark config:
```json
"tableDetails": {
    "spark_conf": {
        "spark.sql.shuffle.partitions": "200",
        "spark.databricks.delta.optimizeWrite.enabled": "true"
    }
}
```

### Secrets Management

Reference Databricks secrets in Data Flow Specs:
```json
"sourceDetails": {
    "readerOptions": {
        "kafka.bootstrap.servers": "{{secrets/my-scope/kafka-brokers}}",
        "kafka.sasl.jaas.config": "{{secrets/my-scope/kafka-jaas}}"
    }
}
```

### Table Migration

Migrate from HMS or another UC catalog:
```json
"tableMigrationDetails": {
    "enabled": true,
    "catalogType": "hms",
    "autoStartingVersionsEnabled": true,
    "sourceDetails": {
        "sourceMigrateDelta": {
            "database": "legacy_db",
            "table": "old_customer",
            "selectExp": ["customer_id", "name", "email"],
            "whereClause": ["active = true"],
            "exceptColumns": ["_metadata"]
        }
    }
}
```

### Logical Environments

Set in `databricks.yml`:
```yaml
variables:
  logical_env:
    description: Logical environment suffix
    default: "_dev"
```

Pass via CLI:
```bash
databricks bundle deploy -t dev --var="logical_env=_test"
```

### Builder Parallelization

Configure in framework config to parallelize spec building:
```json
{
    "parallelization": {
        "enabled": true,
        "max_workers": 4
    }
}
```

### Versioning — Data Flow Specs

Version your data flow specs with mapping operations:
```json
{
    "version": "2.0",
    "mappings": [
        {"operation": "rename", "from": "old_field", "to": "new_field"},
        {"operation": "move", "from": "sourceDetails.db", "to": "sourceDetails.database"},
        {"operation": "delete", "path": "deprecated_field"}
    ]
}
```

### Versioning — Framework

Deploy specific framework versions:
```bash
databricks bundle deploy -t dev --var="version=0.4.0"
```

Reference in pipeline resources:
```yaml
variables:
  framework_version:
    default: "0.4.0"
  framework_source_path:
    default: /Workspace/Users/${var.owner}/.bundle/lakeflow_framework/dev/${var.framework_version}/files/src
```

### UI Integration

Enable pipeline editor UI integration:
```yaml
configuration:
  ui.pipeline.editorEnabled: "true"
```

### Logging

Set in pipeline YAML:
```yaml
configuration:
  framework.logLevel: "INFO"
```

Levels: `DEBUG`, `INFO`, `WARN`, `ERROR`

---

## Pipeline Resource YAML

Every Pipeline Bundle needs at least one resource YAML in `resources/`:

```yaml
resources:
  pipelines:
    <pipeline_name>:
      name: <pipeline_name>
      catalog: ${var.catalog}
      schema: ${var.schema}
      channel: CURRENT
      serverless: true
      libraries:
        - notebook:
            path: ${var.framework_source_path}/dlt_pipeline

      configuration:
        bundle.sourcePath: /Workspace/${workspace.file_path}/src
        framework.sourcePath: /Workspace/${var.framework_source_path}
        workspace.host: ${workspace.host}
        bundle.target: ${bundle.target}
        pipeline.layer: ${var.layer}
```

**Pipeline Filters** (restrict which data flows a pipeline executes):

| Config Key | Description |
|------------|-------------|
| `pipeline.dataFlowIdFilter` | Filter by data flow ID(s) |
| `pipeline.dataFlowGroupFilter` | Filter by data flow group(s) |
| `pipeline.flowGroupIdFilter` | Filter by flow group ID(s) |
| `pipeline.fileFilter` | Filter by data flow spec file path |
| `pipeline.targetTableFilter` | Filter by target table name(s) |

Multiple values: comma-separated.

---

## databricks.yml Template

```yaml
bundle:
  name: <bundle_name>

include:
  - resources/*.yml

variables:
  owner:
    description: The owner of the bundle
    default: ${workspace.current_user.userName}
  catalog:
    description: The target UC catalog
    default: main
  schema:
    description: The target UC schema
    default: <default_schema>
  layer:
    description: The target medallion layer
    default: bronze
  framework_source_path:
    description: Path to the deployed Lakeflow Framework
    default: /Workspace/Users/${var.owner}/.bundle/lakeflow_framework/dev/current/files/src

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: <workspace_url>
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}
    variables:
      framework_source_path: /Workspace/Users/${var.owner}/.bundle/lakeflow_framework/dev/current/files/src

  staging:
    workspace:
      host: <staging_workspace_url>
    variables:
      schema: <staging_schema>
      framework_source_path: /Workspace/Users/${var.owner}/.bundle/lakeflow_framework/staging/current/files/src

  prod:
    workspace:
      host: <prod_workspace_url>
    variables:
      schema: <prod_schema>
      framework_source_path: /Workspace/shared/.bundle/lakeflow_framework/prod/current/files/src
```

---

## Patterns

| Pattern | Layer | Data Flow Type | Description |
|---------|-------|---------------|-------------|
| Basic 1:1 | Bronze | `standard` | Single source → single target, append or SCD1/2 |
| Stream-Static Basic | Silver | `flow` | Streaming fact table joined with static dimension |
| Stream-Static DWH | Silver/Gold | `flow` | Full streaming data warehouse with multiple fact/dim joins |
| Multi-Source Streaming | Silver | `flow` | Multiple sources → single staging → CDC merge to target |
| CDC from Snapshots | Bronze | `standard` | Ingest periodic snapshot files with automatic CDC |

### Pattern: Basic 1:1 (Bronze Ingestion)
- Data Flow Type: `standard`
- Use when: Ingesting data or performing 1:1 loads
- Supports: Append-only, SCD1, SCD2
- Basic single-row transforms only (type conversion, formatting, cleansing)

### Pattern: Stream-Static (Silver Join)
- Data Flow Type: `flow`
- Use when: Joining a streaming source with a static dimension table
- Flow structure: `append_view` for stream source → join view (batch, deltaJoin) → `merge` to target

### Pattern: Multi-Source Streaming (Silver/Gold Merge)
- Data Flow Type: `flow`
- Use when: Multiple sources need to be merged into a single target
- Flow structure: Multiple `append_view` flows into a staging table → `merge` flow to target
- Key benefit: Add/remove flow groups without full pipeline refresh

---

## Deployment

### Deploy Framework Bundle
```bash
git clone https://github.com/databricks-solutions/lakeflow_framework.git
cd lakeflow_framework
databricks bundle deploy -t dev
```

### Deploy Pipeline Bundle
```bash
cd my_pipeline_bundle
databricks bundle deploy -t dev
```

### Run a Pipeline
```bash
databricks bundle run -t dev <pipeline_name>
```

### Validate Before Deploy
```bash
databricks bundle validate -t dev
```

### Destroy (cleanup)
```bash
databricks bundle destroy -t dev
```

---

## Script: scaffold_lakeflow_bundle.py

Use the scaffolding script at `scripts/scaffold_lakeflow_bundle.py` to generate a complete Data Flow Spec pipeline bundle:

```bash
python scripts/scaffold_lakeflow_bundle.py \
  --name "energy_bronze" \
  --catalog main \
  --schema energy_workshop \
  --layer bronze \
  --pattern basic_1_1 \
  --tables "raw_customers,raw_meter_readings,raw_billing" \
  --format json \
  --workspace-host "https://my-workspace.cloud.databricks.com"
```

This generates the full directory structure, Data Flow Specs, schemas, expectations, pipeline YAML, and databricks.yml.

## References

- [Data Flow Spec Framework Documentation](https://databricks-solutions.github.io/lakeflow_framework/)
- [GitHub Repository — databricks-solutions/lakeflow_framework](https://github.com/databricks-solutions/lakeflow_framework)
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
- [Spark Declarative Pipelines](https://docs.databricks.com/en/delta-live-tables/index.html)
- See `references/` folder for pattern guides, energy-specific examples, and full schema reference

## Prerequisites

- Databricks CLI installed and configured
- Unity Catalog enabled workspace
- Data Flow Spec Framework bundle deployed to the target workspace (from `databricks-solutions/lakeflow_framework`)
- Python 3.9+ (for scaffolding script)
