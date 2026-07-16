# Tested Medallion Architecture Example

This document describes a complete end-to-end medallion architecture that was tested and verified on a live Databricks workspace (`e2-demo-west.cloud.databricks.com`) using the Data Flow Spec Framework.

## Dataset — SmartGrid Analytics Platform (Australia)

The test uses 7 synthetic energy tables in `main.sourabh_energy_workshop`:

| Table | Rows | Description |
|-------|------|-------------|
| `raw_customers` | 50,000 | Residential/commercial energy customers across 6 Australian states |
| `raw_billing` | 600,000 | Monthly billing records with kWh consumption and charges |
| `raw_meter_readings` | 10,685,000 | Smart meter telemetry (voltage, power factor, kWh) |
| `raw_outages` | 5,000 | Grid outage events with cause, duration, affected meters |
| `raw_equipment` | 2,000 | Grid equipment (transformers, switchgear) with condition metrics |
| `raw_weather` | 2,190 | Daily weather data by state (temp, humidity, wind) |
| `raw_demand_response` | 20,000 | Demand response events and customer participation |

## Bronze Layer — 7 Streaming Tables

Each raw table gets a corresponding bronze streaming table via a standard Data Flow Spec with SCD Type 1 CDC.

### Data Flow Spec (example — customers)

```json
{
    "dataFlowId": "customers_bronze",
    "dataFlowGroup": "energy_bronze",
    "dataFlowType": "standard",
    "sourceSystem": "smartgrid",
    "sourceType": "delta",
    "sourceViewName": "v_raw_customers",
    "sourceDetails": {
        "database": "main.sourabh_energy_workshop",
        "table": "raw_customers",
        "cdfEnabled": false
    },
    "mode": "stream",
    "targetFormat": "delta",
    "targetDetails": {
        "table": "bronze_customers",
        "tableProperties": {
            "delta.enableChangeDataFeed": "true"
        }
    },
    "cdcSettings": {
        "keys": ["account_id"],
        "sequence_by": "signup_date",
        "scd_type": "1",
        "ignore_null_updates": true,
        "except_column_list": []
    }
}
```

### Pipeline Resource YAML

```yaml
resources:
  pipelines:
    energy_bronze_pipeline:
      name: energy_bronze_pipeline
      catalog: ${var.catalog}
      schema: ${var.schema}
      channel: CURRENT
      serverless: true
      libraries:
        - notebook:
            path: ${var.framework_source_path}/dlt_pipeline
      configuration:
        bundle.sourcePath: ${workspace.file_path}/src
        framework.sourcePath: /Workspace/${var.framework_source_path}
        workspace.host: ${workspace.host}
        bundle.target: ${bundle.target}
        pipeline.layer: bronze
        pipeline.dataFlowGroupFilter: energy_bronze
```

### Results

All 7 bronze tables created successfully with the framework's automatic operational metadata:

| Bronze Table | Rows | Meta Columns |
|-------------|------|-------------|
| `bronze_customers` | 50,000 | `meta_load_details` (record_insert_timestamp, record_update_timestamp, pipeline_start_timestamp) |
| `bronze_billing` | 600,000 | ✓ |
| `bronze_meter_readings` | 10,685,000 | ✓ |
| `bronze_outages` | 5,000 | ✓ |
| `bronze_equipment` | 2,000 | ✓ |
| `bronze_weather` | 2,190 | ✓ |
| `bronze_demand_response` | 20,000 | ✓ |

## Gold Layer — 3 Materialized Views

### Data Flow Spec

```json
{
    "dataFlowId": "energy_gold_kpis",
    "dataFlowGroup": "energy_gold",
    "dataFlowType": "materialized_view",
    "materializedViews": {
        "mv_revenue_by_state": {
            "sqlStatement": "SELECT c.state, DATE_TRUNC('month', b.billing_period) AS month, COUNT(DISTINCT b.customer_id) AS active_customers, SUM(b.amount_charged) AS total_revenue_aud, AVG(b.amount_charged) AS avg_bill_aud, SUM(b.total_kwh) AS total_kwh FROM main.sourabh_energy_workshop.raw_customers c INNER JOIN main.sourabh_energy_workshop.raw_billing b ON c.account_id = b.customer_id GROUP BY c.state, DATE_TRUNC('month', b.billing_period)",
            "tableDetails": { "comment": "Monthly revenue and consumption metrics by Australian state" }
        },
        "mv_grid_reliability": {
            "sqlStatement": "SELECT state, cause, COUNT(*) AS outage_count, AVG(duration_minutes) AS avg_duration_minutes, SUM(affected_meters_count) AS total_affected_meters, ROUND(SUM(duration_minutes * affected_meters_count) / 50000.0, 4) AS saidi_contribution FROM main.sourabh_energy_workshop.raw_outages WHERE start_time <= current_timestamp() GROUP BY state, cause",
            "tableDetails": { "comment": "Grid reliability metrics with SAIDI contribution by state and cause" }
        },
        "mv_equipment_risk_score": {
            "sqlStatement": "SELECT equipment_id, equipment_type, state, install_date, last_maintenance_date, maintenance_count, failure_count, capacity_rating, current_load_pct, DATEDIFF(current_date(), install_date) AS age_days, DATEDIFF(current_date(), last_maintenance_date) AS days_since_maintenance, ROUND((failure_count * 0.3) + (current_load_pct * 0.4) + (DATEDIFF(current_date(), last_maintenance_date) / 365.0 * 0.3), 4) AS risk_score, latitude, longitude FROM main.sourabh_energy_workshop.raw_equipment",
            "tableDetails": { "comment": "Equipment risk scores for predictive maintenance" }
        }
    }
}
```

### Results

| Gold Materialized View | Rows | Sample Output |
|----------------------|------|---------------|
| `mv_revenue_by_state` | 66 | NSW, May 2024: 15,992 customers, $5.4M AUD revenue |
| `mv_grid_reliability` | 36 | QLD weather outages: 301 events, avg 136 min, SAIDI 2209 |
| `mv_equipment_risk_score` | 2,000 | EQ-00616 transformer (VIC): risk score 41.78 |

## Lessons Learned

### Schema Validation

The framework enforces strict JSON Schema validation on Data Flow Specs. Key required fields:
- `dataFlowId`, `dataFlowGroup`, `dataFlowType` (always required)
- `targetFormat`, `targetDetails` (required for standard specs)
- `sourceSystem`, `sourceType`, `sourceViewName`, `mode`, `sourceDetails` (required unless using `cdcSnapshotSettings`)
- `dataQualityExpectationsPath` (required when `dataQualityExpectationsEnabled: true`)

### Column Name Matching

Ensure CDC keys and SQL queries match actual table column names. The framework creates source views and will fail with `UNRESOLVED_COLUMN` errors if column names don't match.

### Additional Properties

The framework uses `additionalProperties: false` in its JSON Schema — do not add fields that aren't in the schema definition. Keep specs clean.

### Operational Metadata

The framework automatically adds a `meta_load_details` struct column to all target tables containing:
- `record_insert_timestamp`
- `record_update_timestamp`
- `pipeline_start_timestamp`
- `pipeline_update_id`
