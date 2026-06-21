# Deploy and Test Nodester Samples

This skill deploys and tests the Lakeflow Framework nodester samples in a Databricks workspace.

## Overview

The nodester samples demonstrate a node-based graph approach to defining DLT pipelines. They live in `samples/nodester_sample/` and include 4 sample dataflows:
- **customer_simple**: Single source → single target (basic streaming)
- **customer_cloudfiles**: Cloud Files → bronze table (file ingestion)
- **customer_with_transform**: Multi-source with transform chain and SCD2 merge
- **customer_multi_target**: Staging append → merge → SCD2 with quarantine table

## Prerequisites

- Databricks CLI installed and authenticated (`databricks auth login`)
- Access to a Databricks workspace with Unity Catalog enabled
- The repo cloned locally — all paths below are relative to the repo root

## Step-by-Step Deployment

### 1. Deploy the Framework (Required First)

The framework source code must be deployed to the workspace before any sample pipelines can run.

```bash
# From the repo root
databricks bundle deploy
```

### 2. Deploy All Samples

To deploy all samples (bronze, silver, gold, yaml, nodester, orchestrator):

```bash
cd samples
./deploy.sh -h <WORKSPACE_URL> -u <DATABRICKS_USER> -l <LOGICAL_ENV>
```

To deploy only the nodester sample:

```bash
cd samples
./deploy_nodester.sh -h <WORKSPACE_URL> -u <DATABRICKS_USER> -l <LOGICAL_ENV>
```

**Parameters:**

| Flag | Description | Example |
|------|-------------|---------|
| `-h` / `--host` | Databricks workspace URL | `https://my-workspace.azuredatabricks.net/` |
| `-u` / `--user` | Your Databricks user email | `alice@example.com` |
| `-l` / `--logical_env` | Logical environment suffix (prefixed with `_`) | `_alice` |
| `--catalog` | Unity Catalog catalog name (default: `main`) | `main` |
| `--schema_namespace` | Schema namespace prefix (default: `lakeflow_samples`) | `lakeflow_samples` |
| `-p` / `--profile` | Databricks CLI profile to use | `my-profile` |

The resulting schemas will be:
- Bronze: `<catalog>.<schema_namespace>_bronze<logical_env>`
- Silver: `<catalog>.<schema_namespace>_silver<logical_env>`
- Staging: `<catalog>.<schema_namespace>_staging<logical_env>`

### 3. Deploy and Run Tests (Run 1 - Full Refresh)

To deploy everything and run the Day 1 initialization job:

```bash
cd samples
./deploy_and_test.sh -h <WORKSPACE_URL> -u <DATABRICKS_USER> -l <LOGICAL_ENV> --runs 1
```

This will:
1. Deploy all sample bundles (bronze, silver, gold, yaml, nodester, orchestrator)
2. Run the "Lakeflow Framework - Run 1 - Load and Schema Initialization" job
3. The job runs all pipelines including the 4 nodester pipelines

### 4. Run Subsequent Tests (Incremental Loads)

```bash
./deploy_and_test.sh -h <WORKSPACE_URL> -u <DATABRICKS_USER> -l <LOGICAL_ENV> --runs 2
./deploy_and_test.sh -h <WORKSPACE_URL> -u <DATABRICKS_USER> -l <LOGICAL_ENV> --runs 3
./deploy_and_test.sh -h <WORKSPACE_URL> -u <DATABRICKS_USER> -l <LOGICAL_ENV> --runs 4
```

## Manual Pipeline Execution via Databricks CLI

To manually trigger a specific nodester pipeline:

```bash
# Find the pipeline ID by name
databricks pipelines list-pipelines --profile <PROFILE> | grep -i nodester

# Run a full refresh
databricks pipelines start-update <PIPELINE_ID> --full-refresh --profile <PROFILE>

# Run an incremental update
databricks pipelines start-update <PIPELINE_ID> --profile <PROFILE>

# Check update status
databricks pipelines get-update <PIPELINE_ID> <UPDATE_ID> --profile <PROFILE>
```

## Key File Locations

| File | Purpose |
|------|---------|
| `samples/nodester_sample/databricks.yml` | Bundle definition for nodester sample |
| `samples/nodester_sample/src/dataflows/base_samples/dataflowspec/` | Nodester JSON spec files |
| `samples/nodester_sample/src/dataflows/base_samples/expectations/` | DQ expectation files |
| `samples/nodester_sample/src/dataflows/base_samples/schemas/` | Table schema files |
| `samples/nodester_sample/src/pipeline_configs/dev_substitutions.json` | Token substitutions |
| `samples/deploy_nodester.sh` | Nodester-only deploy script |
| `samples/deploy.sh` | Full samples deploy script |
| `samples/deploy_and_test.sh` | Deploy + run test job |
| `src/dataflow_spec_builder/transformer/nodester.py` | Nodester spec transformer |

## Troubleshooting

### Pipeline fails with "view not found" or "Failed to analyze flow"
- Check that `inputs` arrays reference **node IDs** (not table/view names)
- If a source reads from an internal pipeline table, ensure its `table` field matches the producing target's `table` — the framework auto-detects internal sources by graph topology

### Quarantine table is empty
- Verify `dataQualityExpectationsEnabled: true` and `dataQualityExpectationsPath` are set on the target node
- For staging tables with quarantine, ensure the DQ path points to a valid expectations file

### Framework source path error
- Re-run `databricks bundle deploy` from the repo root before deploying samples

### Schema not found
- Ensure the `create_schemas_and_tables` notebook ran successfully (it is part of the Run 1 job)

## Architecture Notes

The nodester spec transformer (`src/dataflow_spec_builder/transformer/nodester.py`) converts node-based specs to the standard framework flow spec format. Key rules:
- `inputs` arrays reference **node IDs**, not view or table names
- The primary (terminal) target is auto-detected from the graph — no `isPrimary` flag needed
- Internal pipeline sources are detected by matching `table` against target node tables in the spec; no `database: "live"` needed in user specs
- Views are auto-named `v_{node_id}` unless `outputName` is specified on a transformation node
