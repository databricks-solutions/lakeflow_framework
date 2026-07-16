# Lakeflow Framework — Patterns Quick Reference

## Pattern Selection Guide

| Your Scenario | Pattern | Data Flow Type | Layer |
|---------------|---------|---------------|-------|
| Ingesting raw data from a source table | Basic 1:1 | `standard` | Bronze |
| Ingesting files from cloud storage / Volumes | CloudFiles 1:1 | `standard` | Bronze |
| Ingesting periodic snapshot exports | CDC from Snapshots | `standard` | Bronze |
| Joining a streaming fact with a static dimension | Stream-Static | `flow` | Silver |
| Merging multiple sources into one target | Multi-Source Streaming | `flow` | Silver |
| Building a full streaming data warehouse | Stream-Static DWH | `flow` | Silver/Gold |
| Creating precomputed KPI aggregations | Materialized Views | `materialized_view` | Gold |

---

## Pattern 1: Basic 1:1 (Bronze Ingestion)

**Use when:** Ingesting data from a single source table to a single target.

```
Source Table ──▶ [Source View] ──▶ Target Table
                  (streaming)       (SCD0/1/2)
```

**Supports:** Append-only, SCD Type 1 (overwrite), SCD Type 2 (history)
**Transforms:** Basic single-row only (type conversion, formatting, concatenation)

**Data Flow Spec type:** `standard`
**Key fields:** `sourceType: delta`, `mode: stream`, `cdcSettings` for SCD

**When NOT to use:** Complex joins, multiple sources, window functions, aggregations.

---

## Pattern 2: CloudFiles Ingestion (Bronze from Files)

**Use when:** Ingesting CSV/JSON/Parquet files from UC Volumes or cloud storage.

```
Cloud Storage ──▶ [Auto Loader] ──▶ Target Table
 /Volumes/...       (cloudFiles)      (streaming)
```

**Data Flow Spec type:** `standard`
**Key fields:** `sourceType: cloudFiles`, reader options for format

```json
"sourceDetails": {
    "path": "/Volumes/main/raw/data_landing/customers/",
    "readerOptions": {
        "cloudFiles.format": "csv",
        "header": "true",
        "cloudFiles.inferColumnTypes": "true"
    }
}
```

---

## Pattern 3: CDC from Historical Snapshots

**Use when:** You receive periodic full snapshots and need to derive CDC events.

```
Snapshot Files ──▶ [CDC from Snapshot] ──▶ Target Table
 (daily exports)     (automatic diff)       (SCD1/2)
```

**Data Flow Spec type:** `standard` with `cdcSnapshotSettings`

File-based snapshots:
```json
"cdcSnapshotSettings": {
    "source": {
        "format": "parquet",
        "path": "/Volumes/main/raw/snapshots/{version}/",
        "versionType": "datetime",
        "datetimeFormat": "yyyyMMdd",
        "startingVersion": "20240101"
    }
}
```

Table-based snapshots:
```json
"cdcSnapshotSettings": {
    "source": {
        "table": "main.staging.daily_customer_snapshot",
        "versionColumn": "snapshot_date",
        "startingVersion": "2024-01-01"
    }
}
```

---

## Pattern 4: Stream-Static Join (Silver)

**Use when:** Joining a streaming fact table with one or more static dimension tables.

```
Streaming Fact ──┐
                 ├──▶ [deltaJoin View] ──▶ [merge] ──▶ Target Table
Static Dimension ┘     (stream + static)                 (SCD1/2)
```

**Data Flow Spec type:** `flow`
**Key fields:** View with `sourceType: deltaJoin`, sources with `mode: stream/static`

```json
"sourceDetails": {
    "sources": [
        {"alias": "fact", "database": "...", "table": "meter_readings", "mode": "stream", "cdfEnabled": true},
        {"alias": "dim", "database": "...", "table": "customers", "mode": "static"}
    ],
    "joinType": "left",
    "joinCondition": "fact.customer_id = dim.customer_id",
    "selectExp": ["fact.*", "dim.state", "dim.customer_type"]
}
```

---

## Pattern 5: Multi-Source Streaming (Silver Merge)

**Use when:** Multiple streaming sources need to converge into a single target table.

```
Source A ──▶ [append_view] ──┐
                              ├──▶ Staging Table ──▶ [merge] ──▶ Target Table
Source B ──▶ [append_view] ──┘                                    (SCD1/2)
```

**Data Flow Spec type:** `flow` with `flowGroups`
**Key benefit:** Add/remove sources (flow groups) without full pipeline refresh.

Flow structure:
1. Multiple `append_view` flows write into a shared staging table (`type: ST`)
2. A single `merge` flow CDC-merges the staging table into the final target

**Evolving over time:** Add a new `flowGroup` with new sources → pipeline picks it up without affecting existing data.

---

## Pattern 6: Materialized Views (Gold KPIs)

**Use when:** Building precomputed aggregations, KPIs, or reporting tables.

```
Source Table(s) ──▶ [SQL Query / View] ──▶ Materialized View
                                            (auto-refreshed)
```

**Data Flow Spec type:** `materialized_view`
**Source options (pick one per MV):**
1. `sourceView` — Delta table source with optional Python transform
2. `sqlPath` — Path to a `.sql` file
3. `sqlStatement` — Inline SQL string

Multiple MVs can be defined in a single spec:
```json
{
    "dataFlowType": "materialized_view",
    "materializedViews": {
        "mv_revenue": {"sqlStatement": "SELECT ..."},
        "mv_reliability": {"sqlPath": "./dml/reliability.sql"},
        "mv_adoption": {"sourceView": {"sourceViewName": "v_adoption", ...}}
    }
}
```

---

## Combining Patterns in a Single Bundle

A pipeline bundle can contain multiple data flow specs of different types. Use pipeline filters to control which data flows each pipeline executes:

```
my_energy_bundle/
├── src/dataflows/
│   ├── bronze/          ← Standard specs (Pattern 1)
│   ├── silver/          ← Flow specs (Patterns 4 & 5)
│   └── gold/            ← Materialized view specs (Pattern 6)
├── resources/
│   ├── bronze_pipeline.yml   ← pipeline.layer: bronze
│   ├── silver_pipeline.yml   ← pipeline.layer: silver
│   └── gold_pipeline.yml     ← pipeline.layer: gold
```

Or use data flow group filters:
```yaml
configuration:
  pipeline.dataFlowGroupFilter: energy_bronze
```

---

## Feature Compatibility Matrix

| Feature | Standard | Flows | Materialized View |
|---------|----------|-------|-------------------|
| CDC (SCD1/2) | ✅ | ✅ | ❌ |
| CDC from Snapshots | ✅ | ❌ | ❌ |
| Data Quality Expectations | ✅ | ✅ | ✅ |
| Quarantine (flag/table) | ✅ | ✅ | ✅ |
| Liquid Clustering | ✅ | ✅ | ✅ |
| Multi-Source Streaming | ❌ | ✅ | ❌ |
| Stream-Static Joins | ❌ | ✅ | ❌ |
| SQL Transforms | ✅ | ✅ | ✅ |
| Python Transforms | ✅ | ✅ | ✅ |
| Python Extensions | ✅ | ✅ | ✅ |
| Templates | ✅ | ✅ | ✅ |
| Substitutions | ✅ | ✅ | ✅ |
| Table Migration | ✅ | ✅ | ❌ |
| Soft Deletes | ✅ | ✅ | ❌ |
| Operational Metadata | ✅ | ✅ | ❌ |
| Secrets | ✅ | ✅ | ✅ |
| Foreach Batch Sink | ✅ | ❌ | ❌ |
