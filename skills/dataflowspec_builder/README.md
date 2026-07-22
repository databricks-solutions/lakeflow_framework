# Data Flow Spec Builder — Genie Code Agent Skill for the Lakeflow Framework

A comprehensive [Databricks Genie Code](https://docs.databricks.com/en/notebooks/genie-code.html) Agent Skill that generates production-ready pipeline bundles using the [Data Flow Spec Framework](https://github.com/databricks-solutions/lakeflow_framework) (`databricks-solutions/lakeflow_framework`) from natural language prompts.

> **Important:** This skill generates pipelines using the **Data Flow Spec Framework** — a metadata-driven wrapper around Spark Declarative Pipelines (SDP). It is **not** the same as native Lakeflow Declarative Pipelines (DLT). The Data Flow Spec Framework uses JSON/YAML configuration files to define pipelines declaratively, without writing `@dlt.table` decorators or `CREATE STREAMING TABLE` SQL.

## What It Does

From a prompt like:

> "Use the dataflow-spec-builder to create bronze Data Flow Specs for ingesting customer and billing tables with SCD1 CDC and data quality checks"

Genie Code generates a **complete, deployable pipeline bundle**:

- Data Flow Spec JSON files (standard, flows, or materialized views)
- StructType schema JSON files
- Data quality expectation files
- SQL transform files
- Pipeline resource YAMLs
- `databricks.yml` DABs configuration
- Environment substitutions (dev/staging/prod)
- Reusable templates for similar tables
- Python extension stubs (sources, transforms, sinks)

## Framework Features Covered

| Category | Features |
|----------|----------|
| **Data Flow Types** | Standard (1:1), Flows (multi-source), Materialized Views |
| **Source Types** | Delta, CloudFiles (Auto Loader), Delta Join, Kafka, Python, SQL |
| **CDC** | SCD Type 1, SCD Type 2, CDC from Snapshots (file + table based) |
| **Data Quality** | Expectations (expect / expect_or_drop / expect_or_fail), Quarantine (off/flag/table) |
| **Table Features** | Liquid Clustering (manual + auto), Partition Columns, Table Properties |
| **Pipeline Patterns** | Basic 1:1, Stream-Static Join, Multi-Source Streaming, CDC Snapshots, MVs |
| **Extensibility** | Python Extensions (sources, transforms, sinks), Python Function Transforms |
| **Environment** | Substitutions (token + prefix/suffix), Logical Environments, Multi-target DABs |
| **Templates** | Parameterized specs, parameter sets, template processing |
| **Operations** | Operational Metadata, Mandatory Table Properties, Logging, Versioning |
| **Advanced** | Soft Deletes, Secrets Management, Table Migration (HMS→UC), CDF, Spark Config |
| **Deployment** | DABs validate/deploy/run/destroy, CI/CD scripts, Pipeline Filters |

## Quick Start

### 1. Deploy the Framework Engine

```bash
git clone https://github.com/databricks-solutions/lakeflow_framework.git
cd lakeflow_framework
databricks bundle deploy -t dev
```

### 2. Install the Skill

Upload this skill folder to your workspace's `.assistant/skills/` directory:

```bash
databricks workspace import-dir \
  ./skills/dataflowspec_builder \
  "/Workspace/Users/<your-email>/.assistant/skills/dataflow-spec-builder"
```

### 3. Use in Genie Code

Open a notebook, enter Genie Code Agent mode, and ask:

```
Use the dataflow-spec-builder to create a bronze Data Flow Spec for ingesting
raw_customers from main.my_schema with SCD Type 1 CDC.
```

See [docs/example-prompts.md](docs/example-prompts.md) for 30+ tested prompts.

## Example Prompts

| Prompt | What Gets Generated |
|--------|-------------------|
| "Create bronze Data Flow Specs for 7 energy tables using a template" | Template definition + 7 parameter sets + schemas |
| "Generate a silver Data Flow Spec merging customers and billing with SCD2" | Flows spec with multi-source streaming pattern |
| "Create gold materialized view Data Flow Specs for revenue KPIs" | MV spec with inline SQL |
| "Add data quality expectations to drop null IDs and negative amounts" | Expectations JSON with expect_or_drop rules |
| "Generate a stream-static join Data Flow Spec for meter + weather" | Flows spec with deltaJoin |
| "Set up dev/staging/prod substitutions for different catalogs" | 3 environment config files |

> **Tip:** Always include "Data Flow Spec" or "dataflow-spec-builder" in your prompt to ensure Genie Code routes to this skill instead of native Lakeflow Declarative Pipelines.

## Repository Structure

```
skills/dataflowspec_builder/
├── README.md                                    # This file
├── SKILL.md                                     # Agent Skill definition (Genie Code reads this)
│
├── docs/
│   ├── getting-started.md                       # Setup and installation guide
│   ├── example-prompts.md                       # 30+ tested prompts with explanations
│   ├── architecture.md                          # How the framework and skill work
│   ├── tested-medallion-example.md              # Verified end-to-end example with results
│   └── skill-development.md                     # How to customize the skill
│
├── scripts/
│   ├── scaffold_lakeflow_bundle.py              # Auto-generate pipeline bundles
│   ├── validate_specs.py                        # Validate Data Flow Spec files
│   ├── deploy_framework.sh                      # Deploy framework to workspace
│   └── deploy_pipeline_bundle.sh                # Deploy pipeline bundles
│
├── assets/
│   ├── dataflowspec-templates/                  # Reusable Data Flow Spec templates
│   │   ├── standard_bronze_ingestion.json
│   │   ├── standard_cloudfiles_ingestion.json
│   │   ├── flows_multi_source_silver.json
│   │   ├── flows_stream_static_join.json
│   │   └── materialized_view_gold.json
│   ├── pipeline-resource-templates/             # Pipeline YAML templates
│   │   ├── single_pipeline.yml
│   │   └── filtered_pipeline.yml
│   ├── substitution-templates/                  # Environment configs
│   │   ├── dev_substitutions.json
│   │   └── prod_substitutions.json
│   └── extension-templates/                     # Python extension stubs
│       ├── sources.py
│       ├── transforms.py
│       └── sinks.py
│
├── examples/
│   ├── energy-bronze/                           # Tested bronze ingestion example
│   │   ├── dataflowspec/energy_bronze_main.json
│   │   ├── schemas/                             # 7 StructType schema files
│   │   └── expectations/                        # 4 DQ expectation files
│   ├── energy-silver/                           # Tested silver transform examples
│   │   ├── dataflowspec/customer_360_main.json
│   │   ├── dataflowspec/meter_weather_join_main.json
│   │   └── expectations/
│   ├── energy-gold/                             # Tested gold MV examples
│   │   ├── dataflowspec/energy_kpis_main.json
│   │   └── dml/mv_consumption_heatmap.sql
│   └── energy-templates/                        # Template example
│       └── dataflowspec/energy_bronze_ingestion_template.json
│
└── references/
    ├── patterns-guide.md                        # Pattern selection quick reference
    ├── dataflow-spec-schema-reference.md        # Complete field-by-field reference
    └── energy-domain-mapping.md                 # Energy tables → patterns mapping
```

## Tested and Verified

This skill was tested end-to-end on a live Databricks workspace with:

- **Bronze pipeline:** 7 streaming tables ingesting 10.7M+ rows with SCD1 CDC and operational metadata
- **Gold pipeline:** 3 materialized views with SQL aggregations (revenue by state, grid reliability, equipment risk)
- **Framework:** Data Flow Spec Framework v0.4.0 deployed via DABs
- **Compute:** Serverless pipelines on Unity Catalog

See [docs/tested-medallion-example.md](docs/tested-medallion-example.md) for full details and results.

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Setup, installation, and first pipeline |
| [Example Prompts](docs/example-prompts.md) | 30+ tested prompts organized by layer and feature |
| [Architecture](docs/architecture.md) | How the framework and skill work together |
| [Tested Example](docs/tested-medallion-example.md) | Verified medallion architecture with real results |
| [Skill Development](docs/skill-development.md) | How to customize for your domain |
| [Patterns Guide](references/patterns-guide.md) | Quick reference for selecting the right pattern |
| [Schema Reference](references/dataflow-spec-schema-reference.md) | Complete field reference for all spec types |

## Prerequisites

- Databricks workspace with Unity Catalog enabled
- Databricks CLI installed and configured
- Genie Code enabled on the workspace
- Data Flow Spec Framework v0.4.0+ deployed ([instructions](docs/getting-started.md#step-1-deploy-the-data-flow-spec-framework))
- Python 3.9+ (for scaffolding and validation scripts)

## Related

- [Data Flow Spec Framework](https://github.com/databricks-solutions/lakeflow_framework) — the underlying framework
- [Framework Documentation](https://databricks-solutions.github.io/lakeflow_framework/) — official docs
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html) — DABs reference
- [Spark Declarative Pipelines](https://docs.databricks.com/en/delta-live-tables/index.html) — SDP/DLT docs
