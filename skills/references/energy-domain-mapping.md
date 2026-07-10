# Energy Domain → Lakeflow Framework Mapping

Maps the SmartGrid Analytics Platform tables and use cases to Lakeflow Framework patterns.

## Source Tables (Raw)

| Table | Rows | Key Column(s) | Sequence Column | Recommended Pattern |
|-------|------|---------------|-----------------|---------------------|
| `raw_customers` | 50,000 | `customer_id` | `signup_date` | Basic 1:1 (SCD2) |
| `raw_meter_readings` | ~10.7M | `meter_id`, `reading_timestamp` | `reading_timestamp` | Basic 1:1 (Append) |
| `raw_billing` | ~603K | `bill_id` | `bill_date` | Basic 1:1 (SCD1) |
| `raw_outages` | 5,000 | `outage_id` | `start_time` | Basic 1:1 (SCD1) |
| `raw_weather` | 2,190 | `state`, `date` | `date` | Basic 1:1 (SCD1) |
| `raw_equipment` | 2,000 | `equipment_id` | `last_maintenance_date` | Basic 1:1 (SCD2) |
| `raw_demand_response` | 20,000 | `event_id` | `event_date` | Basic 1:1 (SCD1) |

## Bronze Layer — Data Flow Specs

All 7 tables use the **Basic 1:1 Standard** pattern with a **template** to reduce duplication.

**Template:** `energy_bronze_ingestion_template`
- 7 parameter sets → 7 data flow specs generated at runtime
- CDC enabled for all (SCD1 by default, SCD2 for customers and equipment)
- Data quality expectations per table

**Key DQ Rules:**
- Customers: valid state (6 AU states), valid email, valid customer_type
- Meter readings: non-null meter_id, positive kwh, voltage in 200–260V range
- Billing: positive amount, deduplicate (drop is_duplicate=true)
- Outages: valid cause type, positive duration, drop future-dated records

## Silver Layer — Data Flow Specs

### 1. Customer 360 (Multi-Source Streaming)
**Pattern:** Multi-Source Streaming → `flow` type
**Sources:** bronze_customers + bronze_billing
**Target:** silver_customer_360 (SCD2)
**Logic:** Merge customer demographics with billing aggregates

### 2. Meter-Weather Enriched (Stream-Static Join)
**Pattern:** Stream-Static Join → `flow` type
**Sources:** bronze_meter_readings (stream) + bronze_customers (static) + bronze_weather (static)
**Target:** silver_meter_weather
**Logic:** Enrich meter readings with customer state and weather conditions

### 3. Equipment-Outage Correlation (Multi-Source Streaming)
**Pattern:** Multi-Source Streaming → `flow` type
**Sources:** bronze_equipment + bronze_outages
**Target:** silver_equipment_outages
**Logic:** Correlate equipment conditions with outage events by location

## Gold Layer — Materialized Views

### KPI Materialized Views (single spec, 5 MVs)

| MV Name | Cluster By | Description |
|---------|-----------|-------------|
| `mv_revenue_by_state` | state, month | Monthly revenue and consumption by AU state |
| `mv_grid_reliability` | state | SAIDI contribution by cause and state |
| `mv_demand_response_effectiveness` | event_type, state | DR program effectiveness metrics |
| `mv_equipment_risk_score` | state, equipment_type | Composite risk scores for predictive maintenance |
| `mv_solar_ev_adoption` | state | Solar/EV adoption rates by state and segment |

### Additional MVs (via sqlPath)

| MV Name | SQL File | Description |
|---------|----------|-------------|
| `mv_consumption_heatmap` | `dml/mv_consumption_heatmap.sql` | Hourly consumption patterns by state |

## Substitution Tokens

| Token | Dev Value | Prod Value |
|-------|-----------|------------|
| `{bronze_schema}` | `main.bronze_energy` | `main.bronze_energy_prod` |
| `{silver_schema}` | `main.silver_energy` | `main.silver_energy_prod` |
| `{gold_schema}` | `main.gold_energy` | `main.gold_energy_prod` |
| `{landing_path}` | `/Volumes/main/energy/landing` | `/Volumes/main/energy_prod/landing` |

## Pipeline Definitions

| Pipeline | Layer | Filter | Tables |
|----------|-------|--------|--------|
| `energy_bronze_pipeline` | bronze | `pipeline.dataFlowGroupFilter: energy_bronze` | All 7 raw tables |
| `energy_silver_pipeline` | silver | `pipeline.dataFlowGroupFilter: energy_silver` | customer_360, meter_weather, equipment_outages |
| `energy_gold_pipeline` | gold | `pipeline.dataFlowGroupFilter: energy_gold` | All materialized views |

## Recommended Extensions

| Extension | Type | Use Case |
|-----------|------|----------|
| `transforms.clean_and_deduplicate` | Transform | Remove duplicate meter readings |
| `transforms.add_hash_key` | Transform | Generate surrogate keys for silver tables |
| `sources.get_cdf_source` | Source | Custom CDF reading with filters |
