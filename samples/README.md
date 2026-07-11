# The Samples

The Framework comes with extensive samples that demonstrate the use of the framework and Lakeflow concepts. Samples are organised into the following bundles:

| Bundle | Description |
|--------|-------------|
| **`feature-samples`** | Demonstrates every framework feature in isolation using a single `{namespace}_feature` schema. The simplest entry point. |
| **`pattern-samples`** | End-to-end medallion architecture patterns (bronze → silver → gold) across multiple schemas. Includes multi-source streaming, stream-static joins, CDC from snapshot sources, and gold-layer materialized views. |
| **`yaml_sample`** | Demonstrates that data flow specs can be written in YAML format instead of JSON. Contains YAML equivalents of basic specs. |
| **`tpch-sample`** *(under development)* | Full end-to-end reference implementation based on the TPC-H schema in the UC samples catalog — raw ingestion through to gold-layer aggregations at scale. |

## Deploying the Samples

Samples require the framework already deployed to your workspace (see {doc}`deploy` or {doc}`quick_start`).
The target **UC catalog must already exist** (default `main`, or pass another with `--catalog`) — the deploy scripts create schemas in that catalog, not the catalog itself.

Scripts in the `samples/` directory:

* `deploy.sh`: Deploys all the samples (feature-samples + pattern-samples). Prefer this for a full walkthrough.
* `deploy_feature_samples.sh`: Deploys only the feature-samples bundle.
* `deploy_pattern_samples.sh`: Deploys only the pattern-samples bundle.
* `deploy_tpch.sh`: Deploys only the TPC-H sample.

From the **`samples/`** directory:

```{code-block} console
:class: lf-command-block

cd samples
```

Choose either interactive or full command-line deploy.

### Option A — Interactive deploy

Run with no flags and answer the prompts:

```{code-block} console
:class: lf-command-block

./deploy.sh
```

| Prompt | Purpose | Default / notes |
| ------ | ------- | --------------- |
| Databricks username | Your workspace user (e.g. `jane.doe@company.com`) | — |
| Workspace host | Full workspace URL (e.g. `https://company.cloud.databricks.com`) | — |
| CLI profile | Named CLI profile | `DEFAULT` |
| Compute | `0` = classic/enhanced, `1` = serverless | `1` |
| UC catalog | Existing target catalog | `main` |
| Schema namespace | Prefix for sample schemas | `lakeflow_samples` |
| Logical environment | Isolation suffix (e.g. `_jd`) | — |

Schema namespaces created:

* `feature-samples`: `{namespace}_feature{logical_env}`
* `pattern-samples`: `{namespace}_staging{logical_env}`, `{namespace}_bronze{logical_env}`, `{namespace}_silver{logical_env}`, `{namespace}_gold{logical_env}`

```{admonition} Always set a logical environment
:class: warning

Use a unique logical environment suffix so your sample schemas and jobs do not overwrite another user's deployment in a shared workspace.

Suggested naming: your initials (`_jd`), a story ID (`_123456`), a client or team name, or a project name.
```

### Option B — Full command-line deploy

Pass all required parameters in one command (no prompts):

```{code-block} console
:class: lf-command-block

./deploy.sh -u <databricks_username> -h <workspace_host> [-p <profile>] [-c <compute>] [-l <logical_env>] [--catalog <catalog>] [--schema_namespace <schema_namespace>]
```

| Flag | Purpose | Default |
| ---- | ------- | ------- |
| `-u` / `--user` | Workspace user (required) | — |
| `-h` / `--host` | Workspace URL (required) | — |
| `-p` / `--profile` | CLI profile | `DEFAULT` |
| `-c` / `--compute` | `0` = classic/enhanced, `1` = serverless | `1` |
| `-l` / `--logical_env` | Isolation suffix | `_test` |
| `--catalog` | Existing UC catalog | `main` |
| `--schema_namespace` | Schema name prefix | `lakeflow_samples` |

Example:

```{code-block} console
:class: lf-command-block

./deploy.sh -u jane.doe@company.com -h https://company.cloud.databricks.com -l _jd -c 1
```

Once deployment is complete, the deployed bundles are under `/Users/<username>/.bundle/`.

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

```{code-block} console
:class: lf-command-block

./destroy.sh -h <workspace_host> [-p <profile>] [-l <logical_env>]
```

Parameters:

* `-h, --host`: Databricks workspace host URL (required)
* `-p, --profile`: Databricks CLI profile (optional, defaults to DEFAULT)
* `-l, --logical_env`: Logical environment suffix (optional)

## TPC-H Sample

> **Note:** The TPC-H sample is currently under development.

The TPC-H sample is intended to be the most comprehensive end-to-end example in the framework. Based on the TPC-H schema available in the Databricks UC samples catalog, it reverse engineers the schema into a fully streaming data warehouse — demonstrating how to use the framework at scale across a realistic, industry-standard dataset from raw ingestion through to gold-layer aggregations.

When complete, this bundle will serve as the reference implementation for production-grade Lakeflow Framework deployments.

To deploy the TPC-H sample once available, use the `deploy_tpch.sh` script following the same methods described above.
