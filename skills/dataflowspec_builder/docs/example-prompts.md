# Example Prompts

A comprehensive list of example prompts you can use with the Data Flow Spec Builder skill in Genie Code. Each section includes the prompt, what gets generated, and when to use it.

> **Tip:** Always include "Data Flow Spec" or "dataflow-spec-builder" in your prompt to ensure Genie Code routes to this skill rather than native Lakeflow Declarative Pipelines.

---

## Bronze Layer — Ingestion

### Basic Delta-to-Delta Ingestion

```
Use the dataflow-spec-builder to create a bronze Data Flow Spec that ingests
the raw_customers table from main.energy_workshop with SCD Type 1 CDC,
using account_id as the primary key and signup_date as the sequence column.
```

**Generates:** Standard Data Flow Spec with `sourceType: delta`, `cdcSettings` with SCD1.

### Multiple Tables with Template

```
Generate a Data Flow Spec template for bronze ingestion of 7 tables:
raw_customers, raw_billing, raw_meter_readings, raw_outages, raw_weather,
raw_equipment, raw_demand_response. All from main.energy_workshop.
Use SCD1 CDC for each. Create a reusable template with parameter sets.
```

**Generates:** Template definition JSON + template usage JSON with 7 parameter sets.

### CloudFiles / Auto Loader Ingestion

```
Create a Data Flow Spec for ingesting CSV files from /Volumes/main/landing/customers/
using CloudFiles (Auto Loader) into bronze_customers in main.energy_workshop.
Include schema enforcement with a JSON schema file.
```

**Generates:** Standard Data Flow Spec with `sourceType: cloudFiles`, reader options for CSV, and schema path reference.

### Kafka Source Ingestion

```
Generate a Data Flow Spec for streaming from a Kafka topic called "meter-events"
into bronze_meter_events. Use Databricks secrets for the Kafka bootstrap servers
and SASL credentials.
```

**Generates:** Standard Data Flow Spec with `sourceType: kafka`, secrets references in reader options.

### SCD Type 2 with History Tracking

```
Create a bronze Data Flow Spec for the raw_customers table with SCD Type 2.
Track history on customer_name, rate_plan, and has_solar columns.
Use account_id as the key and signup_date as the sequence column.
```

**Generates:** Standard Data Flow Spec with `cdcSettings.scd_type: "2"` and `track_history_column_list`.

### CDC from Historical Snapshots

```
Generate a Data Flow Spec for CDC ingestion from daily Parquet snapshot files
at /Volumes/main/raw/equipment_snapshots/{date}/ into bronze_equipment.
Use datetime-based versioning with format yyyyMMdd starting from 20240101.
```

**Generates:** Standard Data Flow Spec with `cdcSnapshotSettings` for file-based snapshots.

---

## Silver Layer — Transforms & Joins

### Multi-Source Streaming (Customer 360)

```
Create a Data Flow Spec that merges bronze_customers and bronze_billing
into a silver_customer_360 table using the multi-source streaming pattern.
Stream both sources into a shared staging table, then CDC merge into the target
with SCD2 on account_id. Use the dataflow-spec-builder.
```

**Generates:** Flows Data Flow Spec with two `append_view` flows into a staging table, then a `merge` flow to the target.

### Stream-Static Join

```
Generate a Data Flow Spec for enriching bronze_meter_readings (streaming)
with bronze_customers (static lookup) and bronze_weather (static lookup).
Join on customer_id and date/state. Output to silver_enriched_readings.
```

**Generates:** Flows Data Flow Spec with deltaJoin views combining stream and static sources.

### SQL-Based Transform

```
Create a silver Data Flow Spec that applies a SQL transform to aggregate
hourly meter readings into daily summaries. Group by customer_id and date,
sum kwh_consumed, and calculate peak vs off-peak ratios.
```

**Generates:** Flows Data Flow Spec with `flowType: append_sql` referencing a SQL file.

### Python Extension Transform

```
Generate a Data Flow Spec for silver_clean_customers that reads from
bronze_customers and applies a Python transform to standardize addresses,
validate emails, and deduplicate by account_id.
```

**Generates:** Standard or Flows Data Flow Spec with `pythonTransform` referencing a Python extension module.

---

## Gold Layer — Materialized Views

### Revenue KPIs

```
Create a gold materialized view Data Flow Spec for mv_revenue_by_state that
aggregates monthly revenue, active customer counts, and average bill amounts
by Australian state. Join raw_customers and raw_billing.
```

**Generates:** Materialized View Data Flow Spec with inline SQL aggregation.

### Multiple Gold MVs in One Spec

```
Generate a Data Flow Spec with 3 gold materialized views:
1. mv_revenue_by_state — monthly revenue by state
2. mv_grid_reliability — outage counts and SAIDI by state and cause
3. mv_equipment_risk_score — risk scores based on age, failures, and load
All reading from main.energy_workshop tables.
```

**Generates:** Single Materialized View Data Flow Spec with 3 MV definitions.

### SQL File-Based MV

```
Create a materialized view Data Flow Spec for mv_consumption_heatmap
that references an external SQL file at dml/mv_consumption_heatmap.sql.
```

**Generates:** Materialized View Data Flow Spec with `sqlPath` reference instead of inline SQL.

---

## Data Quality

### Add Expectations to Bronze

```
Add data quality expectations to the bronze_customers Data Flow Spec:
- Expect account_id is not null (log only)
- Drop rows where state is not a valid Australian state
- Fail the pipeline if any postcode is null
```

**Generates:** Expectations JSON file with `expect`, `expect_or_drop`, and `expect_or_fail` rules.

### Quarantine Bad Records

```
Create a Data Flow Spec for bronze_billing with quarantine mode set to "table".
Bad records (negative amounts, null bill_ids) should go to bronze_billing_quarantine.
Good records go to bronze_billing.
```

**Generates:** Standard Data Flow Spec with `quarantineMode: "table"` and `quarantineTargetDetails`.

---

## Templates & Reuse

### Create a Reusable Template

```
Create a Data Flow Spec template called "bronze_delta_ingestion" that is
parameterized on: dataFlowId, sourceTable, targetTable, keyColumns, and
sequenceBy. Use main.energy_workshop as the database.
```

**Generates:** Template definition JSON with parameter definitions and a template body.

### Apply Template to Multiple Tables

```
Using the bronze_delta_ingestion template, generate parameter sets for:
- raw_customers → bronze_customers (key: account_id, seq: signup_date)
- raw_billing → bronze_billing (key: bill_id, seq: billing_period)
- raw_outages → bronze_outages (key: outage_id, seq: start_time)
```

**Generates:** Template usage JSON with `parameterSets` array.

---

## Environment Configuration

### Multi-Environment Substitutions

```
Create environment substitution configs for dev, staging, and prod.
Dev uses main.energy_dev, staging uses main.energy_staging,
prod uses main.energy_prod. Landing path varies by environment.
```

**Generates:** Three substitution JSON files with environment-specific tokens.

### Full DABs Configuration

```
Generate a complete databricks.yml for a bronze pipeline bundle targeting
main.energy_workshop on the e2-demo-west workspace, with dev and prod targets.
```

**Generates:** `databricks.yml` with variables, targets, and workspace configuration.

---

## Advanced Features

### Soft Deletes

```
Create a Data Flow Spec for bronze_customers with soft deletes enabled.
When the source sends a record with operation='DELETE', mark the record
as deleted instead of physically removing it.
```

**Generates:** Standard Data Flow Spec with `cdcSettings.apply_as_deletes` and `soft_delete: true`.

### Table Migration from HMS

```
Generate a Data Flow Spec that migrates the legacy Hive Metastore table
legacy_db.old_customers into main.energy_workshop.bronze_customers.
Select only customer_id, name, email, and state columns. Filter active=true.
```

**Generates:** Standard Data Flow Spec with `tableMigrationDetails` configured.

### Liquid Clustering

```
Create a Data Flow Spec for silver_meter_readings with liquid clustering
on customer_id and reading_date columns.
```

**Generates:** Data Flow Spec with `targetDetails.clusterByColumns` set.

### Auto Clustering

```
Generate a Data Flow Spec for gold_revenue with automatic liquid clustering
enabled (let Databricks choose optimal keys).
```

**Generates:** Data Flow Spec with `targetDetails.clusterByAuto: true`.

### Custom Python Sink

```
Create a Data Flow Spec that writes processed data to an external REST API
using a custom Python sink function. The API endpoint is configurable via tokens.
```

**Generates:** Standard Data Flow Spec with `targetFormat: "foreach_batch_sink"` and Python function sink config.

---

## Deployment & Operations

### Scaffold and Deploy End-to-End

```
Use the dataflow-spec-builder to scaffold a complete bronze pipeline bundle
for the energy tables, validate it, and show me the deploy commands.
```

**Generates:** Full bundle structure + deploy instructions.

### Pipeline Filters

```
Create a pipeline resource YAML that runs only the billing and customers
Data Flow Specs, filtering by dataFlowId.
```

**Generates:** Pipeline YAML with `pipeline.dataFlowIdFilter` configuration.

---

## Informational Queries

These prompts ask for guidance rather than generating files:

```
What Data Flow Spec pattern should I use for joining meter readings with weather data?
```

```
Explain the difference between standard and flows Data Flow Spec types.
```

```
What quarantine modes are available in the Data Flow Spec Framework?
```

```
How do substitutions work across environments in Data Flow Specs?
```

```
What's the directory structure for a Data Flow Spec pipeline bundle?
```
