# The Samples

The Framework comes with extensive samples that demonstrate the use of the framework and Lakeflow concepts. Samples are organised into the following bundles:

| Bundle | Description |
|--------|-------------|
| **`feature-samples`** | Demonstrates every framework feature in isolation using a single `{namespace}_feature` schema. The simplest entry point. |
| **`pattern-samples`** | End-to-end medallion architecture patterns (bronze → silver → gold) across multiple schemas. Includes multi-source streaming, stream-static joins, CDC from snapshot sources, and gold-layer materialized views. |
| **`yaml_sample`** | Demonstrates that data flow specs can be written in YAML format instead of JSON. Contains YAML equivalents of basic specs. |
| **`tpch_sample`** | The most comprehensive end-to-end reference, built on the TPC-H dataset in the UC samples catalog. Covers multi-source schema-on-read bronze, conformed/history-tracked silver (SCD2 + SCD1 + append-only facts with DQ quarantine), and a governed gold star schema with surrogate keys, point-in-time joins, pre-aggregated MVs, and UC metric views. Uses template specs and a three-run incremental simulation. See its README.md |

## Deploying the Samples

The samples can be deployed using the scripts located in the `samples` directory:

* `deploy.sh`: Deploys all the samples (feature-samples + pattern-samples).
* `deploy_feature_samples.sh`: Deploys only the feature-samples bundle.
* `deploy_pattern_samples.sh`: Deploys only the pattern-samples bundle.
* `deploy_tpch.sh`: Deploys only the TPC-H sample.

### Prerequisites

* Databricks CLI installed and configured
* Lakeflow framework already deployed to your workspace (see {doc}`deploy_framework`)

### Interactive Deployment

1. Navigate to the samples directory in the root of the Framework repository:

   ```console
   cd samples
   ```

2. Run the desired deploy script:

   ```console
   ./deploy.sh
   ```

3. Follow the prompts to deploy the samples.

   * **Databricks username**: Your Databricks username e.g. `jane.doe@company.com`.
   * **Databricks workspace**: The full URL of the workspace e.g. `https://company.cloud.databricks.com`.
   * **Databricks CLI profile**: The CLI profile to use. Default: `DEFAULT`.
   * **Select Compute**: Classic/Enhanced or Serverless (0=Enhanced, 1=Serverless). Default: `1`.
   * **UC Catalog**: The Unity Catalog to deploy into. Default: `main`.
   * **Schema Namespace**: Prefix for all deployed schemas. Default: `lakeflow_samples`.
     * `feature-samples` creates: `{namespace}_feature{logical_env}`
     * `pattern-samples` creates: `{namespace}_staging{logical_env}`, `{namespace}_bronze{logical_env}`, `{namespace}_silver{logical_env}`, `{namespace}_gold{logical_env}`
   * **Logical environment**: Suffix to isolate your deployment e.g. `_jd`.

   > **Important:**
   >
   > Always specify a logical environment when deploying the samples. This ensures you don't overwrite anyone else's existing samples in the workspace, as long as the logical environment is unique.
   >
   > Suggested naming:
   >
   > * Your initials, e.g. Jane Doe → `_jd`
   > * A Story ID, e.g. `123456` → `_123456`
   > * Your client name, e.g. Company → `_client`
   > * Others: business unit, team name, project name, etc.

4. Once deployment is complete, you can find the deployed bundles under `/Users/<username>/.bundle/`

### Single Command Line Deployment

1. Navigate to the samples directory in the root of the Framework repository:

   ```console
   cd samples
   ```

2. Run the desired deploy script with required parameters:

   ```console
   ./deploy.sh -u <databricks_username> -h <workspace_host> [-p <profile>] [-c <compute>] [-l <logical_env>] [--catalog <catalog>] [--schema_namespace <schema_namespace>]
   ```

   Parameters:

   * `-u, --user`: Your Databricks username (required)
   * `-h, --host`: Databricks workspace host URL (required)
   * `-p, --profile`: Databricks CLI profile (optional). Default: `DEFAULT`.
   * `-c, --compute`: The type of compute to use (0=Enhanced, 1=Serverless). Default: `1`.
   * `-l, --logical_env`: Logical environment suffix (optional). Default: `_test`.
   * `--catalog`: Unity Catalog name (optional). Default: `main`.
   * `--schema_namespace`: Override the schema name prefix (optional). Default: `lakeflow_samples`.

   For example:

   ```console
   ./deploy.sh -u jane.doe@company.com -h https://company.cloud.databricks.com -l _jd -c 1
   ```

4. Once deployment is complete, you can find the deployed bundles under `/Users/<username>/.bundle/`

## Using the Samples

### feature-samples

The `feature-samples` bundle deploys a single job that runs all feature pipelines end-to-end:

**Job:** `Lakeflow Framework - Feature Samples - Run ({logical_env})`

This will be prefixed with the bundle target and your username, for example:
`[dev jane_doe] Lakeflow Framework - Feature Samples - Run (_jd)`

The job runs in three tiers:

1. **Schema initialisation and staging load** — creates the `{namespace}_feature` schema and loads test data
2. **Tier 1 (parallel)** — all independent feature pipelines (general, python, snapshots, data quality, table migration bronze, libraries, templates)
3. **Tier 2** — DPM pipeline (depends on Tier 1 general + python outputs)
4. **Tier 3** — table migration silver (depends on Tier 2 DPM output)

**Kafka samples** are deployed as a separate job: `Lakeflow Framework - Kafka Samples - Run ({logical_env})`

### pattern-samples

The `pattern-samples` bundle simulates a 4-day incremental data load across four sequential jobs:

* `Lakeflow Framework - Pattern Samples - Run 1 - Load and Schema Initialization ({logical_env})`
* `Lakeflow Framework - Pattern Samples - Run 2 - Load ({logical_env})`
* `Lakeflow Framework - Pattern Samples - Run 3 - Load ({logical_env})`
* `Lakeflow Framework - Pattern Samples - Run 4 - Load ({logical_env})`

These will be prefixed with the target and your username, for example:
`[dev jane_doe] Lakeflow Framework - Pattern Samples - Run 1 - Load and Schema Initialization (_jd)`

Execute the jobs in order to simulate an end-to-end incremental run of the medallion patterns over multiple days of test data.

Individual pipelines can also be executed directly — they follow the naming convention `Lakeflow Framework - Pattern - <Pipeline Name> ({logical_env})`.

## Destroying the Samples

To destroy the samples, use the `destroy.sh` script:

```console
./destroy.sh -h <workspace_host> [-p <profile>] [-l <logical_env>]
```

Parameters:

* `-h, --host`: Databricks workspace host URL (required)
* `-p, --profile`: Databricks CLI profile (optional, defaults to DEFAULT)
* `-l, --logical_env`: Logical environment suffix (optional)

## TPC-H Sample

The TPC-H sample is the most comprehensive end-to-end example in the framework. Built on the TPC-H schema in the Databricks UC samples catalog, it turns a realistic, sample dataset into a fully streaming medallion data warehouse — from multi-source raw ingestion through conformed, history-tracked silver to a governed gold star schema with value-add aggregations.

It demonstrates a wide range of framework capabilities together, including:

* **Schema-on-read bronze** that infers and evolves the schema, ingesting Parquet from eight simulated source systems via Auto Loader.
* **Conformed, history-tracked silver** with SCD2 dimensions, SCD1 reference data, append-only facts, and data-quality expectations with quarantine.
* **Governed gold star schema** with surrogate keys and point-in-time (as-of) joins, plus two metrics approaches side by side: pre-aggregated materialized views and UC metric views.
* **Template specs** that collapse repetitive bronze and silver flows into reusable templates.
* **A three-run incremental simulation** covering SCD changes, fact growth, a backdated out-of-order correction, and ongoing quarantine.

To deploy it, use the `deploy_tpch.sh` script following the same methods described above. See the sample's own See its README.md for the full walkthrough, design choices, and demo flow.
