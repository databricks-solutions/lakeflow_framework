# Getting Started

This guide walks you through setting up the Data Flow Spec Builder skill with Databricks Genie Code.

## Prerequisites

- A Databricks workspace with Unity Catalog enabled
- Databricks CLI installed and configured (`databricks auth login`)
- Genie Code enabled on your workspace (ask your admin)
- Python 3.9+

## Step 1: Deploy the Data Flow Spec Framework

The framework engine must be deployed to your workspace before the skill can generate working pipelines.

```bash
# Clone the framework
git clone https://github.com/databricks-solutions/lakeflow_framework.git
cd lakeflow_framework

# Validate the bundle
databricks bundle validate -t dev

# Deploy to your workspace
databricks bundle deploy -t dev
```

After deployment, the framework code will be at:
```
/Workspace/Users/<your-email>/.bundle/lakeflow_framework/dev/current/files/src
```

## Step 2: Install the Skill

### Option A: Copy to `.assistant/skills/` (recommended)

Upload the skill directory to your workspace's `.assistant/skills/` folder. Genie Code automatically discovers skills in this location.

```bash
databricks workspace import-dir \
  ./path-to-this-repo \
  "/Workspace/Users/<your-email>/.assistant/skills/dataflow-spec-builder"
```

### Option B: Manual skill path

In your notebook, open Genie Code settings (gear icon in the Genie Code panel) and add the skill path manually:
```
/Workspace/Users/<your-email>/skills/dataflow-spec-builder
```

## Step 3: Verify the Skill

Open any Python notebook on your workspace and enter Genie Code Agent mode. Ask:

> "What Data Flow Spec patterns are available?"

If the skill is loaded correctly, Genie Code will respond with the pattern list from the skill definition.

## Step 4: Generate Your First Pipeline

Try this prompt:

> "Use the dataflow-spec-builder to create a bronze Data Flow Spec that ingests the `raw_customers` table from `main.my_schema` with SCD Type 1 CDC"

Genie Code should generate:
1. A `customers_main.json` Data Flow Spec file
2. A pipeline resource YAML
3. A `databricks.yml` configuration

## Step 5: Deploy the Generated Pipeline

```bash
cd <generated_bundle_directory>
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run -t dev <pipeline_name>
```

## Troubleshooting

### Skill not being picked up

- Ensure the `SKILL.md` file is in the root of the skill directory
- Check that the directory is under `.assistant/skills/` in your workspace
- Try mentioning "dataflow-spec-builder" or "Data Flow Spec" explicitly in your prompt

### Genie Code generates native DLT instead

If Genie Code generates `@dlt.table` decorators or `CREATE STREAMING TABLE` SQL, it's using native Lakeflow Declarative Pipelines instead of this skill. Use these trigger phrases:
- "Use the **dataflow-spec-builder** skill..."
- "Generate a **Data Flow Spec** for..."
- "Create a pipeline using the **metadata-driven framework**..."

### Framework bundle not found

Ensure you've deployed the framework:
```bash
cd lakeflow_framework
databricks bundle deploy -t dev
```

Verify the deployment:
```bash
databricks workspace list "/Workspace/Users/<your-email>/.bundle/lakeflow_framework/dev/current/files/src"
```
