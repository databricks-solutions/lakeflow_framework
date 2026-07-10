# Architecture

## How the Data Flow Spec Framework Works

The Data Flow Spec Framework (`databricks-solutions/lakeflow_framework`) is a metadata-driven data engineering framework that sits on top of Databricks Spark Declarative Pipelines (SDP, formerly DLT). Instead of writing Python/SQL pipeline code directly, engineers define pipelines through JSON/YAML configuration files called **Data Flow Specs**.

```
┌─────────────────────────────────────────────────────────┐
│                   Pipeline Bundle                        │
│  (Your project — Data Flow Specs, schemas, expectations) │
│                                                          │
│   databricks.yml                                         │
│   resources/*.yml (pipeline definitions)                 │
│   src/dataflows/*/dataflowspec/*.json                   │
│   src/dataflows/*/schemas/*.json                        │
│   src/dataflows/*/expectations/*.json                   │
│   src/extensions/*.py                                    │
│   src/pipeline_configs/*_substitutions.json              │
└──────────────────────┬──────────────────────────────────┘
                       │ references
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Framework Bundle                         │
│  (Deployed once per workspace — engine code)             │
│                                                          │
│   src/dlt_pipeline       (entry point notebook)          │
│   src/dataflow_spec_builder/  (spec parser & validator)  │
│   src/dataflow/targets/       (target writers)           │
│   src/dataflow/sources/       (source readers)           │
│   src/schemas/                (JSON Schema definitions)  │
└──────────────────────┬──────────────────────────────────┘
                       │ generates
                       ▼
┌─────────────────────────────────────────────────────────┐
│           Spark Declarative Pipeline (SDP)                │
│  (Managed by Databricks — serverless compute)            │
│                                                          │
│   Streaming Tables, Materialized Views, CDC Merges       │
│   Auto-managed checkpoints, retries, scaling             │
└─────────────────────────────────────────────────────────┘
```

## Two Bundle Architecture

### Framework Bundle (deploy once)

Contains the core engine — the Python code that reads Data Flow Specs, validates them against JSON Schemas, and generates SDP pipeline code at runtime.

```bash
git clone https://github.com/databricks-solutions/lakeflow_framework.git
cd lakeflow_framework
databricks bundle deploy -t dev
```

Deployed to: `/Workspace/Users/<email>/.bundle/lakeflow_framework/dev/current/files/src`

### Pipeline Bundle (one per project)

Contains your project-specific configuration — Data Flow Specs, schemas, expectations, and pipeline definitions. This is what the skill generates.

```
my_pipeline/
├── databricks.yml
├── resources/
│   └── bronze_pipeline.yml
└── src/
    └── dataflows/
        └── bronze/
            ├── dataflowspec/
            │   └── customers_main.json
            ├── schemas/
            │   └── customers_schema.json
            └── expectations/
                └── customers_dqe.json
```

## Data Flow Types

### Standard (1:1)

Single source → single target. Best for bronze ingestion.

```
Source Table ──[stream/batch]──> Target Table
                                 (with CDC merge)
```

### Flows (Multi-Source)

Multiple sources → staging → target. Best for silver/gold.

```
Source A ──[append_view]──┐
                          ├──> Staging Table ──[merge]──> Target Table
Source B ──[append_view]──┘                               (with CDC)
```

### Materialized Views

SQL-defined precomputed views. Best for gold KPIs.

```
Source Tables ──[SQL query]──> Materialized View
                               (auto-refreshed)
```

## Pipeline Execution Flow

```
1. databricks bundle run -t dev my_pipeline
        │
2. SDP launches dlt_pipeline notebook (from framework bundle)
        │
3. Framework reads Data Flow Specs from pipeline bundle's src/ directory
        │
4. DataflowSpecBuilder validates specs against JSON Schemas
        │
5. Substitutions are applied ({tokens} replaced with env values)
        │
6. Templates are expanded (parameterSets → individual specs)
        │
7. Specs are filtered by pipeline config (dataFlowGroupFilter, etc.)
        │
8. For each spec:
   ├── Source view is created (streaming or batch)
   ├── Data quality expectations are applied (if enabled)
   ├── Quarantine routing is configured (if enabled)
   ├── Python transforms are applied (if configured)
   └── Target table is written (CDC merge or append)
        │
9. Operational metadata columns are added automatically
        │
10. Pipeline runs continuously (streaming) or completes (batch)
```

## Skill Architecture

The Genie Code Agent Skill works as follows:

```
User Prompt ──> Genie Code reads SKILL.md
                     │
                     ├── Understands Data Flow Spec schema
                     ├── Knows available patterns
                     ├── Has example specs from assets/
                     └── Has reference docs from references/
                     │
                     ▼
              Genie Code generates:
                ├── Data Flow Spec JSON files
                ├── Schema JSON files
                ├── Expectation JSON files
                ├── Pipeline resource YAMLs
                ├── databricks.yml
                └── (optionally) deploy commands
```

The `SKILL.md` file is the core — it contains the complete schema reference, all patterns, feature documentation, and examples that Genie Code needs to generate correct configuration files.
