# Quick Start

Get the Lakeflow Framework deployed and running sample pipelines in your Databricks workspace in about **15–20 minutes**.

---

## Prerequisites

Before you begin, verify:

- [ ] **Databricks CLI** installed and configured — required for local Asset Bundle deployment ([CLI documentation](https://docs.databricks.com/dev-tools/cli/index.html))
- [ ] **Databricks workspace** access with permission to deploy bundles and run Lakeflow Spark Declarative Pipelines
- [ ] **Unity Catalog** enabled in your workspace
- [ ] **VS Code** installed — used for Data Flow Spec IntelliSense (optional but recommended)

```{admonition} New to Asset Bundles?
:class: tip

The framework ships as a Databricks Asset Bundle (DAB). Configure your workspace host and CLI profile in `databricks.yml` before deploying. See {doc}`deploy_framework_bundle` for full configuration options.
```

---

## Step 1 — Clone the repository

1. Open a terminal on your local machine
2. Clone the repository and enter the project directory:

```console
git clone https://github.com/databricks-solutions/lakeflow_framework.git
```

```console
cd lakeflow_framework
```

---

## Step 2 — Deploy the framework

From the **repository root**:

1. Validate the framework bundle

```console
databricks bundle validate
```

2. Deploy to your workspace

```console
databricks bundle deploy
```

| Step | What happens |
| ---- | ------------ |
| 1 | `bundle validate` — checks bundle configuration and workspace connectivity |
| 2 | `bundle deploy` — publishes the framework bundle to your workspace under `.bundle/` |

```{admonition} Target workspace and profile
:class: note

By default the CLI deploys to the `dev` target in `databricks.yml`. Use `-t <target>` to deploy elsewhere and `-p <profile>` to select a different CLI profile.
```

**Full reference:** {doc}`deploy_framework_bundle`

---

## Step 3 — Deploy the samples

1. Open a terminal in the **`samples/`** directory
2. Run the deploy script:

   ```console
   cd samples
   ./deploy.sh
   ```

3. Follow the prompts (or pass flags for non-interactive use):

| Prompt | Purpose | Default |
| ------ | ------- | ------- |
| Databricks username | Your workspace user | — |
| Workspace host | Full workspace URL | — |
| CLI profile | Named CLI profile | `DEFAULT` |
| Compute | `0` = classic, `1` = serverless | `1` |
| UC catalog | Target catalog | `main` |
| Schema namespace | Prefix for sample schemas | `lakeflow_samples` |
| Logical environment | Isolation suffix (e.g. `_jd`) | — |

```{admonition} Always set a logical environment
:class: warning

Use a unique logical environment suffix (initials, story ID, or project name) so your sample schemas and jobs do not overwrite another user's deployment in a shared workspace.
```

Deploy only feature samples (fastest path):

```console
./deploy_feature_samples.sh -u <user> -h <workspace_host> -l _<your_suffix>
```

---

## Step 4 — Run the feature samples

1. In the Databricks workspace, open **Workflows** and locate the job:

   **`Lakeflow Framework - Feature Samples - Run (<logical_env>)`**

   Or run from the CLI (from the `samples/feature-samples` bundle directory after deploy):

   ```console
   databricks bundle run feature_samples_run_job -t dev
   ```

2. When the job completes, inspect tables in the **`{namespace}_feature{logical_env}`** schema (for example `lakeflow_samples_feature_jd`).

This is the simplest entry point — every framework feature runs in a single schema.

---

## Step 5 — Enable VS Code IntelliSense

Add the framework JSON schemas to your VS Code `settings.json` so Data Flow specs get auto-complete and validation.

1. Open **Command Palette** → **Preferences: Open User Settings (JSON)**
2. Register schemas for `*_main.json`, `*_flow.json`, and related spec files

**Full configuration and examples:** {doc}`feature_auto_complete`

---

## Step 6 — Understand the framework

| Topic | Start here |
| ----- | ---------- |
| Operating model (centralized vs domain-oriented) | {doc}`concepts` |
| Medallion and streaming patterns | {doc}`patterns` |
| Feature catalogue | {doc}`features` |
| Product overview | {doc}`what_is_lakeflow_framework` |

---

## What's next?

- **Build your first pipeline** — {doc}`build_pipeline_bundle` (select a pattern from {doc}`patterns`, then follow the build steps)
- **Deploy via CI/CD** — {doc}`deploy_ci_cd`
- **Data Flow Spec reference** — {doc}`dataflow_spec_reference`
