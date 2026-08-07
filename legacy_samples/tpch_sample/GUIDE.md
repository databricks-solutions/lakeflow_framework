# TPC-H Sample — Deploy & Demo Guide

The detailed deployment reference (flags, jobs, one-shot script) and the Day-1/2/3 demo
walkthrough for the TPC-H sample. For the fast path see the [README](./README.md); for
background, architecture, and the design rationale ("the why") see [DESIGN.md](./DESIGN.md).

## Table of contents

1. [Setup & deployment](#1-setup--deployment)
2. [Execution](#2-execution)
3. [Demo flow / walkthrough](#3-demo-flow--walkthrough)
4. [Troubleshooting & gotchas](#4-troubleshooting--gotchas)
5. [Teardown](#5-teardown)

> Prerequisites (CLI, framework, catalog, optional SQL warehouse) are listed in the
> [README](./README.md#1-prerequisites).

---

## 1. Setup & deployment

Deploy the bundle with `deploy_tpch.sh` (run from the `samples/` directory).

**Interactive:**

```bash
cd samples
./deploy_tpch.sh
```

**Single command:**

```bash
cd samples
./deploy_tpch.sh \
  -u <you@company.com> \
  -h https://<workspace-host> \
  -p DEFAULT \
  -c 1 \
  -l _dev \
  --catalog main \
  --schema_namespace tpch_sample
```


| Flag                 | Meaning                                               | Default       |
| -------------------- | ----------------------------------------------------- | ------------- |
| `-u`                 | Databricks username                                   | (prompted)    |
| `-h`                 | Workspace host URL                                    | (prompted)    |
| `-p`                 | CLI profile                                           | `DEFAULT`     |
| `-c`                 | Compute: `0`=classic, `1`=serverless                  | `1`           |
| `-l`                 | Logical environment suffix (isolates your deployment) | `_test`       |
| `--catalog`          | Target catalog                                        | `main`        |
| `--schema_namespace` | Schema name prefix                                    | `tpch_sample` |
| `--warehouse_id`     | *(Optional)* SQL warehouse for the Genie space        | (prompted; blank = skip) |


> Always pass a unique `-l` (e.g. your initials `_jd`) so you don't collide with other
> deployments in a shared workspace.

> **Genie space + dashboards are optional** (see the [README prerequisites](./README.md#1-prerequisites)):
> with no `--warehouse_id` (or a blank prompt) both are skipped and the rest of the sample is
> unaffected — so users without SQL warehouse access are not blocked. When a warehouse id is
> supplied, the Genie space and dashboards are created as post-build steps over the gold schema.

This deploys three pipelines (`tpch_bronze`, `tpch_silver`, `tpch_gold`) and four jobs (setup +
runs 1–3) under `/Users/<you>/.bundle/tpch_samples/`.

---

## 2. Execution

Run the jobs in order. The setup job is a **one-time** provisioning step (slow — it loads the
full baseline) and is **skippable** once staging exists.


| #   | Job display name                                                   | What it does                                                               |
| --- | ------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| 0   | `… TPCH Samples - 0 - Setup and Initialise Staging (_env)`         | CREATE schemas + volume + full initial Parquet staging                     |
| 1   | `… TPCH Samples - 1 - Run 1 - Full Refresh (_env)`                 | bronze, silver, then gold (`full_refresh: true`), then create metric views + (optional) Genie space |
| 2   | `… TPCH Samples - 2 - Run 2 - Dim + Fact Updates (_env)`           | stage batch 2, then run the pipelines (`full_refresh: false`)              |
| 3   | `… TPCH Samples - 3 - Run 3 - Facts + Out-of-Order Dim Fix (_env)` | stage batch 3, then run the pipelines (`full_refresh: false`)              |


Jobs are prefixed with the bundle target and your username, e.g.
`[dev jane_doe] Lakeflow Framework - TPCH Samples - 1 - Run 1 - Full Refresh (_jd)`.

### One-shot deploy + run everything

`deploy_tpch_and_test.sh` deploys and then runs the jobs end to end:

```bash
cd samples
# Deploy + setup + run 1/2/3:
./deploy_tpch_and_test.sh -u <you@company.com> -h https://<host> -p DEFAULT -c 1 -l _dev \
  --catalog main --schema_namespace tpch_sample --runs 3

# Re-run on existing staging (skip the slow setup job):
./deploy_tpch_and_test.sh -u <you@company.com> -h https://<host> -p DEFAULT -c 1 -l _dev \
  --catalog main --schema_namespace tpch_sample --runs 3 --skip-setup
```


| Option         | Meaning                                                     |
| -------------- | ----------------------------------------------------------- |
| `--runs 0..3`  | How many processing runs to execute (0 = deploy/setup only) |
| `--skip-setup` | Skip the one-time setup/staging job                         |


### Re-demoing from a clean day 1

Run the **`reset_to_day1`** notebook (or clear the `incremental/` folders) to wipe day-2/3 data,
then run the setup-free Run 1 (full refresh) to rebuild the baseline from `initial/` only.

---

## 3. Demo flow / walkthrough

### Day 1 — Run 1 (full refresh)

The complete star schema is built: all dims, both base facts, the five aggregate MVs, and the
two UC metric views. **Show:** the gold schema fully populated; `dim_customer` (flow spec) vs
`dim_supplier` (materialized view) producing equivalent SCD2 dimensions; query a metric view
with `MEASURE(...)`. If you supplied a warehouse id, an **AI/BI Genie space** ("TPC-H Sample -
Gold Analytics") is also created over the gold schema (DESIGN §3.19) — **show** a natural-language
question (e.g. *"net sales by market segment in 1996"*).

### Day 2 — Run 2 (incremental: dims + significant facts + DQ)

- **Traceable SCD2 (effective 1996-01-01):** a handful of named customers/suppliers change,
producing new versions in silver and gold (point to specific keys in the UI). The change carries
a **business `effective_date`**, so gold facts attribute orders placed on/after 1996 to the new
version and earlier orders to the baseline — true point-in-time.
- **Fact growth:** a large batch of new orders and line items lands, growing `fct_order_lines`
and the aggregate MVs.
- **Schema evolution (DESIGN §3.16):** the `customer` batch adds a new `loyalty_tier` column that bronze
picks up automatically. **Show:** `DESCRIBE <bronze_crm>.customer` — the column appears with no spec
change; baseline rows are `NULL`.
- **Late-arriving dimension (DESIGN §3.18):** one line item references part `9000001`, whose master has not
arrived yet, so it resolves to the unknown member. **Show:** `SELECT part_sk FROM <gold>.fct_order_lines
WHERE part_key = 9000001` → `-1`.
- **Quarantine:** malformed `customer_address` and `orders` rows are dropped from the clean
tables and captured in `*_quarantine`. **Show:** `SELECT * FROM <silver>.orders_quarantine`.

### Day 3 — Run 3 (incremental: facts + supplier update/delete + backdated correction + late arrival + DQ)

- **More facts** land and grow the star further.
- **Supplier update (effective 1997-01-01):** a couple of suppliers get a second SCD2 version,
giving them multi-version history across Run 2 (1996) and Run 3 (1997). Orders resolve the
supplier name effective as of the order date.
- **Supplier delete (DESIGN §3.17):** supplier 3 is discontinued (`cdc_operation='D'`); `apply_as_deletes` closes its
open SCD2 version. Historical orders still resolve it; later orders fall through to the unknown member.
- **Backdated out-of-order correction (effective 1994-01-01):** a late `customer_address` row
*arrives* in Run 3 but is *effective before* the Run 2 (1996) update. Because silver sequences
by `effective_date`, it slots into history between the 1992 baseline and the 1996 update while
the 1996 value stays current — the headline framework talking point.
- **Late-arrival resolution (DESIGN §3.18):** part `9000001` finally arrives; a new line item for it resolves
to the real `dim_part` member, while the Run-2 fact keeps the unknown member (append-only facts are not
retro-repointed).
- **Quarantine** continues to catch a second bad batch.

### Ask Genie (natural language)

If you deployed the Genie space (DESIGN §3.19), open it and ask questions in plain English — the curated
tables, metric views, and instructions steer Genie to surrogate-key joins and the governed metric
views. Two examples and the SQL Genie generates:

- *"What were the top 5 market segments by net sales in 1996?"* — joins the fact to the conformed
  dimensions on surrogate keys and to `dim_date`, exactly as intended:

```sql
SELECT c.market_segment, SUM(f.net_sales) AS net_sales
FROM main.tpch_sample_gold.fct_order_lines f
JOIN main.tpch_sample_gold.dim_customer c ON f.customer_sk = c.customer_sk
JOIN main.tpch_sample_gold.dim_date d ON f.order_date_key = d.date_key
WHERE d.year = 1996 AND c.market_segment IS NOT NULL
GROUP BY c.market_segment
ORDER BY net_sales DESC
LIMIT 5
```

- *"What is the on-time delivery rate by ship mode?"* — queries the governed metric view with
  `MEASURE(...)` rather than re-deriving the measure from the base fact:

```sql
SELECT `Ship Mode`, MEASURE(`On-Time Delivery Rate`) AS on_time_delivery_rate
FROM main.tpch_sample_gold.tpch_sample_sales_metrics
WHERE `Ship Mode` IS NOT NULL
GROUP BY ALL
ORDER BY on_time_delivery_rate DESC
```

**Questions that showcase the Day-2/3 incremental data.** After Runs 2–3, ask these to surface the
SCD2 history and late-arriving dimension the incremental loads introduced:

- *"How many order line items are linked to the unknown part member (part_sk = -1)?"* — the
  **late-arriving dimension**: a Run-2 line item references a part whose master had not arrived yet,
  so it resolves to the unknown member (DESIGN §3.18).

```sql
SELECT COUNT(*) AS order_line_count
FROM main.tpch_sample_gold.fct_order_lines
WHERE part_sk = -1
```

- *"How many suppliers have more than one version in the supplier dimension?"* — the **SCD2
  historization** from the Run-3 supplier updates (effective 1997), which give affected suppliers a
  second version:

```sql
SELECT COUNT(*) AS suppliers_with_multiple_versions
FROM (
  SELECT supplier_key
  FROM main.tpch_sample_gold.dim_supplier
  GROUP BY supplier_key
  HAVING COUNT(*) > 1
)
```

### Explore the AI/BI dashboards

If you supplied a warehouse id, two **AI/BI (Lakeview) dashboards** are deployed as native bundle
resources (DESIGN §3.20) into the `dashboards/` folder under the bundle's workspace path:

- **TPC-H Commercial Overview** — headline KPIs (net sales, orders, AOV, on-time delivery, return
  rate), the net-sales-by-month trend, and net sales by region / segment / ship mode / top
  suppliers over the gold star schema.
- **TPC-H Pipeline Health & Governance** — the framework's own signals: late-arriving/unknown
  member resolution (`*_sk = -1`), SCD2 history depth (dimension rows vs current entities, plus a
  supplier version-history table), and a data-quality lens. This one is compelling even on the raw
  TPC-H data because it visualizes CDC + historization + DQ rather than business volumes.

Both are **optional** (same warehouse gating as Genie) and torn down automatically by
`destroy_tpch.sh` (they are bundle resources, so `bundle destroy` removes them — no extra cleanup
step). Because the datasets use unqualified table names bound to `dataset_catalog` /
`dataset_schema` at deploy, the dashboards automatically target whatever catalog, namespace and
logical environment the bundle was deployed with.

---

## 4. Troubleshooting & gotchas

- **Run the setup job before Run 1** (or pass without `--skip-setup`): Run 1 assumes the schemas,
volume, and initial staging already exist.
- **In-pipeline references must use `live.<table>`.** A gold dataset that reads another dataset in
the *same* pipeline must reference it as `live.<table>` so DLT registers the dependency and
orders the build; a fully-qualified `{catalog}.{schema}.{table}` reference is treated as
external. Cross-pipeline reads (gold reading **silver**) correctly stay fully-qualified via
`{silver_schema}`. The base facts resolve surrogate keys by reading `live.dim_customer`,
`live.dim_supplier`, and `live.dim_part`, which is what makes the dims build before the facts in
the gold DAG.
- **Append-only facts have no `__START_AT`.** `fct_order_lines` is itself sequenced by
`load_timestamp` (not `__START_AT`); only genuine SCD2 sources expose `__START_AT` / `__END_AT`.
It still carries surrogate keys, resolved by as-of joining the dimensions on `order_date`.
- **Point-in-time uses a business `effective_date`, not processing time.** TPC-H order dates are
1992-1998, but DLT processing time (`__START_AT` derived from `load_timestamp`) is "now," so the
two never overlap. The customer/supplier SCD2 dimensions therefore sequence by a synthetic
business `effective_date` (1992 baseline, 1996/1997 updates, 1994 backdated correction) so facts
can resolve the version that was effective as of the `order_date`.
- **UC Metric Views only support star joins off `source`** (no chained/snowflake joins) — that
is why geography is denormalized onto `dim_customer` / `dim_supplier`.
- **Staging data types must match across batches.** When injecting custom staging rows, keep
column types identical to the initial load (e.g. don't let `-1 * total_price` widen a
`decimal(18,2)`), or schema-on-read bronze will rescue the value to NULL.

---

## 5. Teardown

When you're done, tear everything down with `destroy_tpch.sh` — see
**[README §4 Cleanup](./README.md#4-cleanup)** for the command and the Genie-space cleanup note.
