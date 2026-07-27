# Data Flow Spec — Complete Field Reference

All fields used across Standard, Flows, and Materialized View data flow specs.

## Common Metadata (All Types)

| Field | Type | Required | Values | Description |
|-------|------|----------|--------|-------------|
| `dataFlowId` | string | Yes | — | Unique identifier for this data flow |
| `dataFlowGroup` | string | Yes | — | Logical group (used for pipeline filters) |
| `dataFlowType` | string | Yes | `standard`, `flow`, `materialized_view` | Determines which spec schema applies |

## Standard-Only Fields

| Field | Type | Required | Values | Description |
|-------|------|----------|--------|-------------|
| `sourceType` | string | Yes | `cloudFiles`, `delta`, `deltaJoin`, `kafka` | Source connector type |
| `sourceSystem` | string | Yes | — | Descriptive name of origin system |
| `sourceViewName` | string | Yes | `v_<name>` pattern | Name for the auto-created source view |
| `sourceDetails` | object | Yes | — | Source-specific configuration (see below) |
| `mode` | string | Yes | `stream`, `batch` | Pipeline execution mode |
| `targetFormat` | string | Yes | `delta`, `foreach_batch_sink` | Target write format |
| `targetDetails` | object | Yes | — | Target table configuration (see below) |

## Source Details — By Source Type

### delta
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `database` | string | Yes | `catalog.schema` reference |
| `table` | string | Yes | Source table name |
| `cdfEnabled` | boolean | No | Enable Change Data Feed reading |
| `schemaPath` | string | No | Path to schema JSON file |
| `selectExp` | list | No | Column expressions (`["*"]` or `["col1", "CAST(col2 AS DATE)"]`) |
| `whereClause` | list | No | Filter expressions |
| `readerOptions` | object | No | Spark reader options |
| `pythonTransform.module` | string | No | Extension module path (`transforms.func_name`) |
| `pythonTransform.path` | string | No | File path to Python function |

### cloudFiles
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | Volume or cloud storage path |
| `readerOptions` | object | Yes | Must include `cloudFiles.format` |
| `schemaPath` | string | No | Path to schema JSON |
| `selectExp` | list | No | Column expressions |

### deltaJoin
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sources` | list | Yes | Array of source objects (alias, database, table, mode, cdfEnabled) |
| `joinType` | string | Yes | `inner` or `left` |
| `joinCondition` | string | Yes | SQL join expression |
| `selectExp` | list | No | Columns to select from joined result |

### kafka
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `readerOptions` | object | Yes | Must include `kafka.bootstrap.servers`, `subscribe` |
| `schemaPath` | string | No | Path to value schema |

### python
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pythonModule` | string | Yes | Extension module path (`sources.func_name`) |
| `tokens` | object | No | Key-value pairs passed to the Python function |

### sql
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sqlPath` | string | Yes | Path to `.sql` file in `dml/` directory |

## Target Details

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table` | string | Yes | Target table name |
| `schemaPath` | string | No | Path to target schema JSON |
| `tableProperties` | object | No | Delta table properties |
| `partitionColumns` | list | No | Partition columns |
| `clusterByColumns` | list | No | Liquid clustering columns |
| `clusterByAuto` | boolean | No | Let Databricks choose clustering keys |
| `path` | string | No | External storage path |
| `operationalMetadata` | boolean | No | Disable operational metadata columns |

## CDC Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `keys` | list | Yes | Primary key column(s) |
| `sequence_by` | string | Yes | Ordering column |
| `scd_type` | string | Yes | `"1"` or `"2"` |
| `where` | string | No | Row filter |
| `ignore_null_updates` | boolean | No | Skip null values in updates |
| `except_column_list` | list | No | Columns excluded from upsert |
| `apply_as_deletes` | string | No | SQL expression for delete detection |
| `track_history_column_list` | list | No | Explicit history columns (SCD2) |
| `track_history_except_column_list` | list | No | Exclude from history (SCD2) |
| `soft_delete` | boolean | No | Flag instead of physical delete |

## CDC Snapshot Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source.format` | string | File | `parquet`, `csv`, `json`, `table` |
| `source.path` | string | File | Path with `{version}` placeholder |
| `source.versionType` | string | File | `int` or `datetime` |
| `source.datetimeFormat` | string | Conditional | Format for datetime versions |
| `source.startingVersion` | string/int | No | First version to process |
| `source.table` | string | Table | Source table name |
| `source.versionColumn` | string | Table | Column for versioning |

## Data Quality

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dataQualityExpectationsEnabled` | boolean | No | Enable DQ checks |
| `dataQualityExpectationsPath` | string | No | Path to expectations JSON file |
| `quarantineMode` | string | No | `off`, `flag`, `table` |
| `quarantineTargetDetails.targetFormat` | string | Conditional | `delta` |
| `quarantineTargetDetails.table` | string | Conditional | Quarantine table name |
| `quarantineTargetDetails.tableProperties` | object | Conditional | Properties |

## Expectations File Schema

```json
{
    "expect": [{"name": "...", "constraint": "SQL", "tag": "...", "enabled": true}],
    "expect_or_drop": [...],
    "expect_or_fail": [...]
}
```

## Flow-Specific Fields

### flowGroups (array)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `flowGroupId` | string | Yes | Unique flow group identifier |
| `stagingTables` | object | No | Named staging table definitions |
| `flows` | object | Yes | Named flow definitions |

### Staging Table
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | `ST` (Streaming Table) or `MV` (Materialized View) |
| `schemaPath` | string | No | Schema file path |
| `partitionColumns` | list | No | Partition columns |
| `tableProperties` | object | No | Delta properties |
| `cdcSettings` | object | No | CDC config for the staging table |

### Flow
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | No | Enable/disable this flow |
| `flowType` | string | Yes | `append_view`, `append_sql`, `merge` |
| `flowDetails` | object | Yes | Source and target references |
| `views` | object | No | Named view definitions |

### Flow Details (by type)
- **append_view:** `targetTable`, `sourceView`, optional `column_prefix`/`column_prefix_exceptions`
- **append_sql:** `targetTable`, `sqlPath`
- **merge:** `targetTable`, `sourceView`

### View
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `stream` or `batch` |
| `sourceType` | string | Yes | `cloudFiles`, `delta`, `deltaJoin`, `sql`, `python` |
| `sourceDetails` | object | Yes | Same as standard source details |
| `columnsToUpdate` | list | No | Columns to update |

## Materialized View Fields

### materializedViews (object of named MVs)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sourceView` | object | Pick one | Source view definition |
| `sqlPath` | string | Pick one | Path to SQL file |
| `sqlStatement` | string | Pick one | Inline SQL |
| `tableDetails` | object | No | Target table config |
| `tableDetails.database` | string | No | Target schema override |
| `tableDetails.schemaPath` | string | No | Schema file path |
| `tableDetails.tableProperties` | object | No | Delta properties |
| `tableDetails.clusterByColumns` | list | No | Clustering columns |
| `tableDetails.clusterByAuto` | boolean | No | Auto clustering |
| `tableDetails.comment` | string | No | Table description |
| `tableDetails.spark_conf` | object | No | Spark configs for this MV |
| `tableDetails.private` | boolean | No | Don't publish to metastore |

## Table Migration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tableMigrationDetails.enabled` | boolean | Yes | Enable migration |
| `tableMigrationDetails.catalogType` | string | Yes | `hms` or `uc` |
| `tableMigrationDetails.autoStartingVersionsEnabled` | boolean | No | Auto-track versions |
| `tableMigrationDetails.sourceDetails.sourceMigrateDelta.database` | string | Yes | Old database |
| `tableMigrationDetails.sourceDetails.sourceMigrateDelta.table` | string | Yes | Old table |
| `tableMigrationDetails.sourceDetails.sourceMigrateDelta.selectExp` | list | No | Columns |
| `tableMigrationDetails.sourceDetails.sourceMigrateDelta.whereClause` | list | No | Filters |
| `tableMigrationDetails.sourceDetails.sourceMigrateDelta.exceptColumns` | list | No | Exclude columns |
