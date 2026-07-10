# Nodespec Feature Samples — Changes, Design & Considerations

> **Note:** this is a historical design/implementation record. Some field names
> shown below reflect an earlier iteration; the current authoring syntax is in
> `docs/source/dataflow_spec_ref_main_nodespec.rst`. In particular: targets wire
> inputs via **`input_flows`**; data quality is a nested **`data_quality`** object;
> quarantine is a nested **`quarantine`** object; and `data_flow_type` is optional
> (nodespec is the default).

## Overview

The Nodespec dataflow spec type introduces a **node-based graph architecture** for defining data pipelines. Instead of the traditional flat (standard) or pre-built flow (flow) spec formats, Nodespec expresses pipelines as directed graphs of **source**, **transformation**, and **target** nodes connected through `input_flows` arrays (on target nodes).

This document covers the changes made to support all 33 feature samples from the bronze_sample in the Nodespec format, the migration tooling created, and the design decisions and assumptions behind the implementation.

---

## What Changed

### 1. Transformer Extensions (`src/dataflow_spec_builder/transformer/nodespec.py`)

The Nodespec transformer was extended to support all feature types:

| Feature | Change |
|---------|--------|
| **Removed `isPrimary`** | No primary/secondary target concept. The transformer auto-selects one target for backend `targetDetails` from graph topology (terminal node detection). This is an internal detail invisible to spec authors. |
| **`targetFormat` on targets** | Targets can specify `targetFormat: "foreach_batch_sink"`, `"delta_sink"`, or `"custom_python_sink"` alongside `sinkType` and `sinkConfig` for non-delta outputs. |
| **`tableMigrationDetails`** | Targets can include table migration config, which the transformer copies to the spec level for the backend. |
| **`configFlags`** | Targets can specify `configFlags: ["disableOperationalMetadata"]`, propagated to `targetDetails`. |
| **`once` flag** | Targets can set `once: true` to execute the flow only once (batch mode). Added to `flowDetails` in the output. |
| **`append_sql` flow type** | When a source node has `sourceType: "sql"`, the transformer creates an `append_sql` flow with the SQL directly in `flowDetails` (no intermediate view). |
| **`cdcSnapshotSettings`** | Snapshot targets (periodic and historical) now correctly trigger MERGE flow type. Historical file/table snapshots work without source nodes since the CDC snapshot system reads files/tables directly. |
| **`cdcApplyChanges` alias** | Treated identically to `cdcSettings` for backward compatibility with version mapping specs. |
| **`dataFlowVersion`** | Passed through from spec level to output. |
| **Materialized view targets** | Targets with `tableType: "mv"` produce separate MV flow specs. Source views for MVs are forced to batch mode (MVs use `spark.sql()` which can't read streaming views). Returns `List[Dict]` for multi-MV specs. |
| **Targets without inputs** | Targets with `cdcSnapshotSettings` and no `inputs` create a placeholder MERGE flow. The snapshot system handles file/table reading directly. |

### 2. Schema Extensions (`src/schemas/spec_nodespec.json`)

- Removed `isPrimary` from the node schema
- Added to `targetNodeConfig`: `targetFormat`, `tableType`, `tableMigrationDetails`, `configFlags`, `once`, `name`, `sinkType`, `sinkConfig`, `sinkOptions`, `sqlPath`, `sqlStatement`, `sourceView`, `refreshPolicy`, `tableDetails`, `cdcApplyChanges`
- Added to `sourceNodeConfig`: `functionPath`, `pythonModule`, `tokens`, `sqlPath`, `sqlStatement`, `startingVersionFromDLTSetup`, `cdfChangeTypeOverride`

### 3. Migration Script (`scripts/migrate_to_nodespec.py`)

CLI tool that converts any existing spec to Nodespec format:

```bash
# Single file
python scripts/migrate_to_nodespec.py spec_main.json --output nodespec_spec.json

# Entire directory
python scripts/migrate_to_nodespec.py ./dataflowspec/ --output-dir ./nodespec_dataflowspec/
```

Handles all three spec types:
- **Standard** → source node (from sourceDetails) + target node (from targetDetails + spec-level CDC/DQ/quarantine)
- **Flow** → source nodes (from views) + target nodes (from staging tables + main target) with connections from flow inputs
- **Materialized View** → target nodes with `tableType: "mv"`, optional source nodes for sourceView patterns

### 4. Feature Samples (`samples/nodespec_sample/src/dataflows/feature_samples/`)

All 33 specs translated with supporting files (schemas, expectations, SQL, Python functions) copied from `bronze_sample`. Each spec uses `dataFlowGroup: "nodespec_feature_samples_*"` prefixes.

### 5. Pipeline Resources (`samples/nodespec_sample/resources/serverless/`)

Six new pipeline definitions:
- `nodespec_feature_samples_general_pipeline.yml` — 9 specs
- `nodespec_feature_samples_data_quality_pipeline.yml` — 2 specs
- `nodespec_feature_samples_snapshots_pipeline.yml` — 11 specs
- `nodespec_feature_samples_python_pipeline.yml` — 4 specs
- `nodespec_feature_samples_table_migration_pipeline.yml` — 2 specs
- `nodespec_feature_samples_materialized_views_pipeline.yml` — 6 MVs

### 6. Framework Bug Fix (`src/dlt_pipeline_builder.py`)

`table_migration_state_volume_path` in `global.json` was hardcoded with `_es` suffix. Changed to use `{logical_env}` token and moved the initialization to after the `SubstitutionManager` is ready so the token gets resolved.

---

## How Nodespec Works

### Node Graph Model

A Nodespec spec defines a pipeline as a graph of nodes:

```
Source Nodes ──→ Transformation Nodes ──→ Target Nodes
(data origins)    (SQL/Python logic)      (output tables)
```

Each node has:
- `id` — unique identifier
- `type` — `source`, `transformation`, or `target`
- `inputs` — array of node IDs this node reads from (source nodes have none)
- `config` — type-specific configuration

### Transformation Pipeline

```
Nodespec JSON Spec
       │
       ▼
NodespecSpecTransformer._process_spec()
       │
       ├─ Categorize nodes by type
       ├─ Validate graph (references, cycles, required nodes)
       ├─ Detect internal sources (source reading from target in same spec)
       ├─ Auto-select spec target (terminal node in graph)
       ├─ Build flow spec:
       │   ├─ targetDetails from spec target
       │   ├─ CDC/DQ/quarantine from spec target → spec level
       │   ├─ Other targets → stagingTables
       │   └─ Flows from node connections → flowGroups
       ▼
Lakeflow Framework Flow Spec (same format as standard/flow transformers)
       │
       ▼
Backend (DataFlow, FlowGroup, CDC, etc.)
```

### Spec Target Selection

With no `isPrimary` flag, the transformer auto-selects which target becomes `targetDetails`:

1. Build set of "consumed" targets — any target whose ID appears in another node's inputs, or whose table name is referenced by a source node
2. Terminal targets = targets that are NOT consumed
3. If multiple terminal targets exist, use the last one (with a warning)
4. All other targets become staging tables

For single-target specs (the majority), the only target is automatically selected.

### Internal Source Detection

When a source node reads from a table that's also a target in the same spec, it's treated as "internal":
- The source references the staging table directly (no view created)
- Database is forced to `live` so DLT resolves it during pipeline analysis
- This enables staging patterns: source → staging_target → internal_source → final_target

### Flow Type Determination

| Condition | Flow Type |
|-----------|-----------|
| Target has `cdcSettings` or `cdcApplyChanges` | `merge` |
| Spec target has CDC and flow writes to spec target | `merge` |
| Target has `cdcSnapshotSettings` | `merge` |
| Source is SQL type (`sourceType: "sql"`) | `append_sql` |
| Otherwise | `append_view` |

---

## Design Decisions & Assumptions

### 1. No Primary Target Concept

**Decision:** The spec author never needs to think about which target is "primary." All targets are equal — they each specify their own CDC, DQ, quarantine, and table migration settings directly on the target node config.

**Why:** The "primary target" was a backend implementation detail leaking into the spec format. The backend requires `targetDetails` at the spec level, but this is now handled transparently by the transformer.

**Trade-off:** The auto-selection heuristic (terminal node detection) could pick the wrong target in ambiguous multi-target specs. A warning is logged in this case.

### 2. Per-Target Settings at Spec Level

**Decision:** The spec target's CDC/DQ/quarantine settings are duplicated at the spec level for backend compatibility.

**Assumption:** The backend reads these settings from the spec level for the main target. This duplication is an interim measure — the backend should eventually read all settings from target nodes directly.

### 3. Materialized Views as Target Nodes

**Decision:** MVs are target nodes with `tableType: "mv"`. Each MV target in a spec becomes a separate flow spec (the transformer returns `List[Dict]`).

**Why:** MVs are fundamentally different from streaming tables — they use `spark.sql()` batch reads and have different creation ordering (flows first, then MV). Treating them as a target type keeps the node graph model consistent.

**Constraint:** MV source views are forced to batch mode because DLT's `spark.sql()` cannot read from streaming views.

### 4. SQL Sources → `append_sql` Flow Type

**Decision:** When a source node has `sourceType: "sql"`, the transformer creates an `append_sql` flow with the SQL directly in `flowDetails`, bypassing view creation.

**Why:** `append_sql` is a distinct flow type in the framework that handles DLT-specific SQL (like `STREAM()` functions) directly. Using `append_view` with an SQL source view would work for simple cases but wouldn't match the original spec behavior.

### 5. Snapshot Targets Without Source Nodes

**Decision:** Targets with `cdcSnapshotSettings` don't require source nodes. Historical file/table snapshots define their data source entirely within the snapshot settings.

**Why:** The CDC snapshot system reads files/tables directly based on `cdcSnapshotSettings.source`. A traditional source node would create a view with nothing to read from. The transformer creates a placeholder MERGE flow with no `sourceView`.

### 6. Migration Script Assumptions

- The script preserves `dataFlowId` and `dataFlowGroup` from the original spec (the group is prefixed with `nodespec_` separately)
- Source node IDs are derived from `sourceViewName` (stripping `v_` prefix)
- Target node IDs follow the pattern `target_{table_name}`
- For flow specs, view names from the original spec become source node IDs directly
- The script doesn't validate the output against the JSON schema — the transformer handles validation at runtime

---

## Known Limitations

### 1. CDC Merge + Quarantine "table" Mode

**Status:** Fixed. The `_get_exclude_columns` method in `dataflow.py` no longer adds `is_quarantined` to the exclude list for TABLE quarantine mode.

**Root Cause (was):** When `quarantineMode: "table"` and `cdcSettings` coexist, the framework added `is_quarantined` to the flow's `exclude_columns` list. However, in table quarantine mode, the `is_quarantined` column is NOT added to the source view (only a separate quarantine view gets it). This created a column resolution failure when the CDC merge flow tried to reference it via `except_column_list`.

**Fix:** Removed the logic that added `is_quarantined` to `exclude_columns` for TABLE mode. In table quarantine mode, the column never exists in the source view — the separate quarantine view/flow handles it independently. In FLAG mode, the column is part of the target schema and written through, so no exclusion is needed there either.

### 2. Delta Sink Specs

**Status:** Not tested (disabled in the original bronze_sample too).

The `sink_delta_path_table` and `sink_delta_uc_table` specs have `dataFlowGroup: "nodespec_feature_samples_general_DISABLED"` — they're excluded from all pipelines, matching the original behavior.

---

## Test Results

| Pipeline | Flows | Status |
|----------|-------|--------|
| General | append_sql, append_view, append_view_once, ddl_schema, version_mapping (standard+flows), foreach_batch (sql+python) | 9/9 passed |
| Data Quality | quarantine_flag, quarantine_table | 3/3 passed |
| Snapshots | 7 historical file, 2 historical table, 1 historical flow, 2 periodic | 13/13 passed |
| Python | python_source, python_source_extension, python_transform, python_transform_extension | 4/4 passed |
| Table Migration | append_only, scd2 (with import flows) | 4/4 passed |
| Materialized Views | 6 MVs (source_view, sql_path, sql_statement, quarantine, chained, refresh_policy) | 8/8 passed |

---

## Files Changed

| File | Action |
|------|--------|
| `src/dataflow_spec_builder/transformer/nodespec.py` | Extended transformer with all feature support |
| `src/schemas/spec_nodespec.json` | Extended schema, removed isPrimary |
| `src/dlt_pipeline_builder.py` | Moved table_migration init after SubstitutionManager |
| `samples/bronze_sample/src/pipeline_configs/global.json` | Changed hardcoded `_es` to `{logical_env}` token |
| `scripts/migrate_to_nodespec.py` | New migration script |
| `samples/nodespec_sample/src/dataflows/feature_samples/` | 33 translated specs + supporting files |
| `samples/nodespec_sample/src/extensions/` | Copied Python extension modules |
| `samples/nodespec_sample/src/pipeline_configs/global.json` | Added table_migration_state_volume_path |
| `samples/nodespec_sample/resources/serverless/` | 6 new pipeline resource YAMLs |
| `samples/nodespec_sample/databricks.yml` | Added serverless resource includes |
