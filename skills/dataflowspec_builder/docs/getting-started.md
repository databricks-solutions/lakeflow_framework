# Getting Started

This guide walks you through deploying the **Lakeflow Framework** and installing the Data Flow Spec Builder skill for use with **Cursor**, **Claude Code**, **Databricks Genie Code**, and other Agent Skills-compatible assistants.

## Prerequisites

- A Databricks workspace with Unity Catalog enabled
- Databricks CLI installed and configured (`databricks auth login`)
- Python 3.9+ (for skill scaffolding and validation scripts)
- An Agent Skills-compatible coding assistant (see Step 2)

## Step 1: Deploy the Lakeflow Framework

The Lakeflow Framework engine must be deployed to your workspace before the skill can generate working pipelines.

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

Copy or symlink the `skills/dataflowspec_builder/` folder into the skills directory for your assistant.

### Cursor

Personal (all projects):

```bash
mkdir -p ~/.cursor/skills
cp -R skills/dataflowspec_builder ~/.cursor/skills/dataflow-spec-builder
```

Or add to a single repo: `.cursor/skills/dataflow-spec-builder/` (copy the skill folder there).

See [Cursor Agent Skills](https://cursor.com/docs/context/skills) for the latest paths and discovery rules.

### Claude Code

```bash
mkdir -p ~/.claude/skills
cp -R skills/dataflowspec_builder ~/.claude/skills/dataflow-spec-builder
```

Claude Code discovers skills from `~/.claude/skills/` and project `.claude/skills/`. See [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills).

### Databricks Genie Code

Upload the skill to your workspace `.assistant/skills/` folder (workspace-wide or user scope):

```bash
databricks workspace import-dir \
  ./skills/dataflowspec_builder \
  "/Workspace/Users/<your-email>/.assistant/skills/dataflow-spec-builder"
```

Alternatively, open Genie Code settings in a notebook and add the skill path manually. See [Extend Genie Code with agent skills](https://docs.databricks.com/aws/en/genie-code/skills).

### Other assistants

If your tool supports the [Agent Skills](https://agentskills.io/specification) layout, install the folder so the assistant can read `SKILL.md` at the skill root. Each skill is a directory with a required `SKILL.md` file.

## Step 3: Verify the Skill

Ask your assistant:

> "What Data Flow Spec patterns are available?"

If the skill is loaded correctly, the response should include the pattern list from the skill definition.

In **Genie Code**, use Agent mode in a notebook. In **Cursor** or **Claude Code**, invoke the skill explicitly if needed (for example `@dataflow-spec-builder` or by naming the skill in your prompt).

## Step 4: Generate Your First Pipeline

Try this prompt:

> "Use the dataflow-spec-builder to create a bronze Data Flow Spec that ingests the `raw_customers` table from `main.my_schema` with SCD Type 1 CDC"

The assistant should generate:

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

- Ensure `SKILL.md` is in the root of the skill directory
- Confirm the skill is in the correct directory for your assistant (see Step 2)
- Try mentioning `dataflow-spec-builder` or `Data Flow Spec` explicitly in your prompt

### Assistant generates native DLT instead

If the assistant generates `@dlt.table` decorators or `CREATE STREAMING TABLE` SQL, it may be using native Lakeflow Declarative Pipelines instead of this skill. Use these trigger phrases:

- "Use the **dataflow-spec-builder** skill..."
- "Generate a **Data Flow Spec** for..."
- "Create a pipeline using the **metadata-driven framework**..."

### Framework bundle not found

Ensure you have deployed the framework:

```bash
cd lakeflow_framework
databricks bundle deploy -t dev
```

Verify the deployment:

```bash
databricks workspace list "/Workspace/Users/<your-email>/.bundle/lakeflow_framework/dev/current/files/src"
```
