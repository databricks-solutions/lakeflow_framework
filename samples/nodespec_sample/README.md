# Nodespec Sample

This sample demonstrates how to use node-based node-based dataflow specifications with the Lakeflow Framework.

## Overview

The Nodespec dataflow type (`dataFlowType: "nodespec"`) provides compatibility with [node-based](https://github.com/Mmodarre/Lakehouse_Nodespec) style specifications. This allows users familiar with Nodespec's graph-based approach to define pipelines using source, transformation, and target nodes.

## Directory Structure

```
nodespec_sample/
├── databricks.yml                    # DABs bundle configuration
├── .gitignore
├── pytest.ini
├── README.md
├── resources/
│   ├── classic/                      # Classic compute pipeline configs
│   │   ├── nodespec_base_samples_pipeline.yml
│   │   ├── nodespec_customer_simple_pipeline.yml
│   │   ├── nodespec_customer_transform_pipeline.yml
│   │   ├── nodespec_customer_multi_target_pipeline.yml
│   │   └── nodespec_customer_cloudfiles_pipeline.yml
│   └── serverless/                   # Serverless pipeline configs
│       ├── nodespec_base_samples_pipeline.yml
│       ├── nodespec_customer_simple_pipeline.yml
│       ├── nodespec_customer_transform_pipeline.yml
│       ├── nodespec_customer_multi_target_pipeline.yml
│       └── nodespec_customer_cloudfiles_pipeline.yml
├── src/
│   ├── dataflows/
│   │   └── base_samples/
│   │       ├── dataflowspec/         # Nodespec-style dataflow specs
│   │       └── schemas/              # Table schemas
│   └── pipeline_configs/
│       ├── dev_substitutions.json
│       └── global.json
├── scratch/                          # For local resource overrides
├── fixtures/                         # Test fixtures
└── tests/                            # Unit tests
```

## Key Concepts

### Node Types

1. **Source Nodes**: Define where data comes from (Delta tables, cloud files, Kafka, etc.)
2. **Transformation Nodes**: Define SQL or Python transformations
3. **Target Nodes**: Define where data is written

### Target-Level Configuration

All target-specific settings are configured directly on target nodes:

| Setting | Description | Location |
|---------|-------------|----------|
| `cdcSettings` | CDC/SCD2 merge settings | Target node `config` |
| `cdcSnapshotSettings` | CDC snapshot settings | Target node `config` |
| `dataQualityExpectationsEnabled` | Enable DQ expectations | Target node `config` |
| `dataQualityExpectationsPath` | Path to DQ file | Target node `config` |
| `quarantineMode` | Quarantine mode (off/flag/table) | Target node `config` |
| `quarantineTargetDetails` | Quarantine table config | Target node `config` |

**Example with CDC settings on target:**

```json
{
    "id": "target_customer",
    "type": "target",
    "inputs": ["transform_final"],
    "config": {
        "table": "customer_final",
        "cdcSettings": {
            "keys": ["CUSTOMER_ID"],
            "scd_type": "2",
            "sequence_by": "LOAD_TIMESTAMP"
        }
    }
}
```

### Main Target Selection

When multiple targets exist, the transformer needs to identify the "main" target:

- Use `isPrimary: true` on a target to explicitly mark it as main (optional)
- If no `isPrimary` flag is specified, the first target node in the array becomes the main target
- Other targets become staging tables with their own independent settings

**All target-level settings are now applied per-target** - including CDC, data quality, and quarantine.

## Sample Files

### `customer_simple_main.json`
Basic example: single source → single target. No `isPrimary` flag needed for single-target specs.

### `customer_with_transform_main.json`
Multiple sources with append-merge pattern. Demonstrates:
- Multiple sources appending to a shared staging table
- CDC merge on staging table (configured at target level)
- Final transformation and CDC merge to enriched target

### `customer_multi_target_main.json`
Demonstrates the staging pattern with:
- Source → Transform → Staging (append) → Transform → Final (CDC merge)
- CDC settings specified on the final target node directly

### `customer_cloudfiles_main.json`
Example of ingesting from cloud files with transformations.

## View Naming Convention

When writing SQL transformations, reference input nodes using the pattern `v_<node_id>`:

```sql
SELECT * FROM v_source_customer WHERE status = 'active'
```

## Deployment

### Prerequisites

1. **Databricks CLI** installed and configured
2. **Framework deployed** to your workspace
3. **Source tables** created (for Delta source examples)

### Deploy using DABs

1. Copy the desired pipeline configuration from `resources/classic/` or `resources/serverless/` to `scratch/resources/`:

```bash
# For classic compute
cp resources/classic/nodespec_base_samples_pipeline.yml scratch/resources/

# For serverless
cp resources/serverless/nodespec_base_samples_pipeline.yml scratch/resources/
```

2. Deploy the bundle:

```bash
databricks bundle deploy \
  --var catalog=<your_catalog> \
  --var schema=<your_schema> \
  --var framework_source_path=<path_to_framework_src> \
  --var workspace_host=<your_workspace_url>
```

3. Run the pipeline:

```bash
databricks bundle run lakeflow_samples_nodespec_base_pipeline
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `catalog` | Unity Catalog name | `main` |
| `schema` | Target schema | `silver_dev` |
| `framework_source_path` | Workspace path to framework src | `/Workspace/Repos/user/lakeflow_framework/src` |
| `workspace_host` | Databricks workspace URL | `https://your-workspace.cloud.databricks.com/` |
| `layer` | Pipeline layer (optional) | `silver` |
| `logical_env` | Logical environment (optional) | `dev` |

## Customization

### Adding Substitutions

Edit `src/pipeline_configs/dev_substitutions.json` to add your own substitution values:

```json
{
    "substitutions": {
        "bronze_schema": "bronze_dev",
        "silver_schema": "silver_dev",
        "catalog": "main"
    }
}
```

### Creating New Nodespec Specs

1. Create a new `*_main.json` file in `src/dataflows/base_samples/dataflowspec/`
2. Use `dataFlowType: "nodespec"` and define your nodes
3. Add corresponding schema files if needed
4. Create a pipeline resource file in `resources/classic/` and `resources/serverless/`

The Nodespec specs are automatically converted to flow specs at runtime, so all framework features (CDC, data quality, secrets, etc.) work seamlessly.

## Backend Behavior Notes

### Per-Target Settings
All target-level settings are now applied independently per target:

| Setting | Main Target | Staging Tables |
|---------|-------------|----------------|
| `cdcSettings` | ✅ Applied | ✅ Applied |
| `cdcSnapshotSettings` | ✅ Applied | ✅ Applied |
| `dataQualityExpectationsEnabled/Path` | ✅ Applied | ✅ Applied |
| `quarantineMode` | ✅ Applied | ✅ Applied |
| `quarantineTargetDetails` | ✅ Applied | ✅ Applied |

This means you can have different CDC, data quality, and quarantine configurations for different targets in the same dataflow.

### Table Migration
Table migration (`tableMigrationDetails`) is only supported on the main target table, as it's designed for migrating external tables to the primary output.

