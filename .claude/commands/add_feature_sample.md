Add a new feature sample and its validations to the Lakeflow Framework samples.

## Context

You are helping add a new feature sample to the Lakeflow Framework. A feature sample demonstrates a specific framework capability end-to-end — from a dataflowspec JSON/YAML file through to validated output tables.

The framework root is the current working directory (the repo root).

## Your Task

The user will describe what feature they want to add a sample for (e.g. "add a sample for the new append_dedup flow type" or "add a sample for custom Python aggregation transforms"). Follow all steps below.

---

## Step 1 — Understand the Feature

1. Read the relevant framework source code in `src/` to understand what the feature does, its configuration keys, and what output tables it produces.
2. Read at least 2 similar existing dataflowspecs in `samples/bronze_sample/src/dataflows/feature_samples/dataflowspec/` to understand the naming convention (`{feature_name}_main.json`) and structure.
3. Decide which pipeline group the new sample belongs to:
   - `feature_samples_general` → goes in the General Pipeline
   - `feature_samples_data_quality` → goes in the Data Quality Pipeline
   - `feature_samples_snapshots` → goes in the Snapshots Pipeline
   - `feature_samples_table_migration` → goes in the Table Migration Pipeline
   - `feature_samples_python` → goes in the Python Pipeline
   - If it's a new group, you'll also need to create a new pipeline resource YAML (see Step 4).

---

## Step 2 — Create the Dataflowspec

Create `samples/bronze_sample/src/dataflows/feature_samples/dataflowspec/{feature_name}_main.json` (or `.yaml`).

Follow the exact naming pattern: `{feature_name}_main.json`.

Rules:
- Set `dataFlowGroup` to the correct pipeline group from Step 1
- Use `{staging_schema}`, `{bronze_schema}`, `{silver_schema}` etc. as placeholders (these are substituted at runtime)
- Use a descriptive `dataFlowId` that starts with `feature_` to distinguish it as a sample
- Set `targetDetails.table` to `feature_{feature_name}` or a similarly descriptive name
- Enable `delta.enableChangeDataFeed` in tableProperties where applicable
- Validate the spec using: `python scripts/validate_dataflows.py samples/bronze_sample/src/dataflows/feature_samples/dataflowspec/{feature_name}_main.json`

---

## Step 3 — Add Test Data (if needed)

If the feature requires specific source data that doesn't already exist:
1. Check `samples/test_data_and_orchestrator/src/create_schemas_and_tables.ipynb` — add DDL if a new staging table is needed
2. Check `samples/test_data_and_orchestrator/src/run_1_staging_load.ipynb` — add initial data inserts
3. Check `run_2_staging_load.ipynb`, `run_3_staging_load.ipynb`, `run_4_staging_load.ipynb` — add incremental data to exercise SCD2 history, updates, deletes, snapshot changes, etc.

Data loading conventions:
- Run 1: initial state (all active, no history)
- Run 2: first set of changes (updates, new records, deletions via flag)
- Run 3: second set of changes (more updates, snapshot overwrites)
- Run 4: final changes (additional updates to test multiple SCD2 versions)

---

## Step 4 — Register in a Pipeline (only if new pipeline group)

If the feature uses a new `dataFlowGroup` that doesn't map to an existing pipeline, create pipeline resource YAMLs:
- `samples/bronze_sample/resources/serverless/{pipeline_name}.yml`
- `samples/bronze_sample/resources/classic/{pipeline_name}.yml`

Copy the structure from an existing pipeline YAML (e.g. `bronze_feature_samples_pipeline_general.yml`) and set `pipeline.dataFlowGroupFilter` to the new group.

Then add the pipeline lookup variable to `samples/test_data_and_orchestrator/databricks.yml`:
```yaml
lakeflow_samples_{pipeline_key}_id:
  lookup:
    pipeline: "${var.name_prefix}Lakeflow Framework - {Pipeline Display Name} (${var.logical_env})"
```

---

## Step 5 — Add Pipeline Tasks to Orchestrator Jobs

Add the pipeline as a task in all 4 run job YAMLs (both classic and serverless):
- `samples/test_data_and_orchestrator/resources/serverless/run_1_load_and_schema_initialization_job.yml`
- `samples/test_data_and_orchestrator/resources/serverless/run_2_load_job.yml`
- `samples/test_data_and_orchestrator/resources/serverless/run_3_load_job.yml`
- `samples/test_data_and_orchestrator/resources/serverless/run_4_load_job.yml`
- Same 4 files under `resources/classic/`

Use `full_refresh: true` in run_1 and `full_refresh: false` in run_2/3/4.

Also add the new pipeline task key to the `depends_on` list of the `validate_run_N` task in all 8 files.

---

## Step 6 — Write Validations

Add validation cells to all 4 validate notebooks:
`samples/test_data_and_orchestrator/src/validate_run_{1,2,3,4}.ipynb`

For each notebook, insert new markdown + code cells **before the final `v.print_summary()` cell**.

**Key principles for good validations:**

1. **Exact counts for deterministic tables**: Use `v.validate_row_count(table, N, description)` when you know exactly how many rows should be present after each run (e.g. append-only, SCD1 batch-overwrite, small deterministic CDC streams).

2. **Min counts for complex tables**: Use `v.validate_min_row_count(table, N, description)` for tables where exact counts are harder to predict (e.g. file-based historical snapshots, complex SCD2 with many interacting sources).

3. **SCD2 active/closed counts**: Use these validators for CDC/SCD2 tables:
   - `v.validate_active_scd2_count(table, N, end_at_col)` — records where `end_at_col IS NULL`
   - `v.validate_closed_scd2_count(table, N, end_at_col)` — records where `end_at_col IS NOT NULL`
   - `v.validate_min_closed_scd2_count(table, N, end_at_col)` — at least N closed records

4. **Value checks**: Use `v.validate_column_value(table, where_clause, column, expected_value, description)` to verify specific field values (e.g. check that John's email updated correctly across runs).

5. **Existence checks**: Use `v.validate_values_exist(table, column, [list_of_values], description)` to verify that specific IDs or keys exist.

6. **Null checks**: Use `v.validate_column_not_null(table, column_expr, description)` for operational metadata or required columns.

**Per-run validation logic:**
- **Run 1**: Initial state. All streaming tables show data from the first load. SCD2 tables show all-active records (0 closed). SCD1 tables show the first snapshot. Historical snapshot tables show SCD2 history from all pre-loaded files.
- **Run 2**: First incremental. CDC tables grow by the Run 2 inserts. SCD2 tables gain closed records for updated keys. SCD1 tables update in-place. Snapshot sources are overwritten.
- **Run 3**: Second incremental. Similar pattern; note which snapshot sources are overwritten and which tables are unchanged.
- **Run 4**: Final incremental. Verify the last expected state, including checking exact final values (e.g. latest email address).

**Add a markdown cell** before each code cell explaining what tables are being validated and the expected state.

---

## Step 7 — Verify

1. Run the dataflowspec validator to check the spec is valid:
   ```bash
   python scripts/validate_dataflows.py samples/bronze_sample/src/dataflows/feature_samples/dataflowspec/{feature_name}_main.json -v
   ```

2. If Databricks CLI is configured, you can deploy and test with a logical environment alias:
   ```bash
   cd samples
   ./deploy_and_test.sh -l "_test_{feature_name}" -u "<your-databricks-email>" -h "<your-workspace-url>" -p "<your-cli-profile>" --runs 4
   ```
   The `logical_env` parameter (e.g. `_test_my_feature`) namespaces all schemas so you don't affect the main deployment.

3. After a successful test run, review the validation notebook output to confirm all assertions pass.

---

## Checklist

Before finishing, confirm:
- [ ] Dataflowspec file created and validates cleanly with `validate_dataflows.py`
- [ ] Test data added (or confirmed that existing data covers the feature)
- [ ] Pipeline registered in orchestrator databricks.yml (if new group)
- [ ] Pipeline tasks added to all 8 run_N job YAMLs (classic + serverless) with correct depends_on
- [ ] Validation cells added to all 4 validate_run_N notebooks covering: Run 1 (initial), Run 2 (first incremental), Run 3 (second incremental), Run 4 (final state)
- [ ] Each validation uses the most appropriate validator method (exact count vs min count vs SCD2 active/closed)
- [ ] All validate task `depends_on` lists in the job YAMLs include the new pipeline task key
