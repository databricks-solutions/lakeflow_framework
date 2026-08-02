# TPC-H Sample - End-to-End Medallion Reference

A comprehensive, end-to-end Lakeflow Framework bundle that turns the `samples.tpch` benchmark
schema into a fully streaming **medallion Lakehouse**. What's inside:

- **Source data at scale** - the `samples.tpch` benchmark (~SF 5: 7.5M orders, ~30M line items),
parsed into 12 staging entities across 8 simulated source systems and reshaped for trend,
seasonality, and skew.
- **A full medallion warehouse:**
  - **Bronze** - schema-on-read ingestion (Auto Loader infers + evolves); 12 raw passthrough tables.
  - **Silver** - conformed, clean names, historized (SCD2/SCD1) with data-quality quarantine.
  - **Gold** - governed star schema: 5 dimensions, 2 base facts, 5 aggregate MVs.
- **UC Metric Views** - a governed semantic layer queried with `MEASURE(...)`.
- **AI/BI Genie space** *(optional)* - natural-language analytics over the gold schema.
- **AI/BI Lakeview dashboards** *(optional)* - a commercial overview + a pipeline-health / governance view.

It is the most comprehensive sample in the framework: where `feature-samples` shows each feature in isolation and
`pattern-samples` shows the core medallion patterns, `tpch_sample` ties everything together on a
realistic dataset at scale.

> **Looking for more than the fast path?** Background, architecture, and the design rationale
> ("the why") live in **[DESIGN.md](./DESIGN.md)**. The detailed deploy reference and the demo
> walkthrough live in **[GUIDE.md](./GUIDE.md)**. This README is the quickstart.

---



## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Quickstart](#2-quickstart)
3. [What you get & how to verify](#3-what-you-get--how-to-verify)
4. [Cleanup](#4-cleanup)

**Deeper docs**

- **[GUIDE.md](./GUIDE.md)** - detailed setup & deployment, execution, demo walkthrough, troubleshooting.
- **[DESIGN.md](./DESIGN.md)** - background, architecture, design choices, repository layout, source data, UC objects.

---



## 1. Prerequisites

- **Databricks CLI** installed and configured with a profile.
- The **Lakeflow Framework already deployed** to your workspace (see the framework deploy docs).
- A target **Unity Catalog** that exists (default `main`) and on which you have **`CREATE SCHEMA`**
privilege. The bundle creates schemas + the staging volume; it does **not** create the catalog.
- Access to the `samples.tpch` catalog (available by default in most workspaces).
- **Serverless** is the default/primary compute path (a classic resource tree is maintained for parity).
- **(Optional) A SQL warehouse** - only needed for the **AI/BI Genie space** and the **AI/BI
(Lakeview) dashboards**. The deploy prompt asks for a warehouse id; leave it blank to **skip both
Genie and the dashboards**. Everything else in the sample deploys and runs without a warehouse,
so users without SQL warehouse access are not blocked.

---



## 2. Quickstart

Build the full warehouse end-to-end (deploy, stage data, then run all three days) with a single
command (prerequisites in §1):

```bash
cd samples
./deploy_tpch_and_test.sh \
  -u <you@company.com> -h https://<workspace-host> -p DEFAULT \
  -c 1 -l _dev --catalog main --schema_namespace tpch_sample \
  --warehouse_id <sql-warehouse-id>
```

This deploys the three pipelines and four jobs, runs the one-time setup, then executes Run 1
(full refresh), Run 2, and Run 3. Re-running on staging that already exists? Add `--skip-setup`.

> `--warehouse_id` is **optional** - it enables the AI/BI Genie space and dashboards. Omit it
> (or leave the prompt blank) to skip both; everything else still deploys (see §1).

When it finishes, head to **§3** to see what you got and verify it — or the
**[deploy & demo guide](./GUIDE.md)** for the manual step-by-step, the full flag/job reference, and
the Day-1/2/3 demo talk track.

> Prefer to drive it step-by-step (deploy, then run each job yourself)? See
> **[GUIDE.md](./GUIDE.md)**.

---



## 3. What you get & how to verify

**What you get.** A populated `tpch_sample_gold` star schema — **5 dimensions, 2 base facts, 5
aggregate MVs, and 2 UC metric views** — on top of a conformed silver layer and schema-on-read
bronze. (Full object inventory: [DESIGN §6](./DESIGN.md#6-unity-catalog-objects-produced).)

**How to verify.** Run a few queries against the gold (and silver) schema:

```sql
-- TPC-H-style: revenue by market segment (no join to samples.tpch needed)
SELECT c.market_segment, sum(f.net_sales) AS net_sales
FROM main.tpch_sample_gold.fct_order_lines f
JOIN main.tpch_sample_gold.dim_customer c
  ON f.customer_key = c.customer_key AND c.__END_AT IS NULL
GROUP BY 1 ORDER BY 2 DESC;

-- Same metric, two ways:
SELECT sales_month, market_segment, net_sales
FROM main.tpch_sample_gold.fct_sales_by_month_segment;          -- fixed-grain MV

SELECT `Order Month`, `Market Segment`, MEASURE(`Net Sales`)
FROM main.tpch_sample_gold.tpch_sample_sales_metrics            -- metric view, any grain
GROUP BY 1, 2;

-- Data-quality quarantine
SELECT * FROM main.tpch_sample_silver.customer_address_quarantine;
SELECT order_key, total_price, comment FROM main.tpch_sample_silver.orders_quarantine;

-- Out-of-order SCD2 history (customer 1) on the business timeline: the backdated correction
-- (effective 1994) slots between the 1992 baseline and the 1996 update; 1996 stays current.
SELECT customer_key, address, __START_AT, __END_AT
FROM main.tpch_sample_silver.customer_address
WHERE customer_key = 1 ORDER BY __START_AT;

-- Point-in-time surrogate keys: every fact row carries the dim version effective as of order_date.
-- Customer 1's orders map to different customer_sk values across the 1992/1994/1996 windows.
SELECT f.order_date, f.customer_sk, c.address, c.market_segment
FROM main.tpch_sample_gold.fct_order_lines f
JOIN main.tpch_sample_gold.dim_customer c ON f.customer_sk = c.customer_sk
WHERE f.customer_key = 1 ORDER BY f.order_date;
```

For the guided demo narrative behind these results (Day 1/2/3, Genie, dashboards), see the
**[demo walkthrough](./GUIDE.md#3-demo-flow--walkthrough)**.

---



## 4. Cleanup

```bash
cd samples
./destroy_tpch.sh -h https://<workspace-host> [-p DEFAULT] [-l _dev] [--catalog main] [--schema_namespace tpch_sample]
```

This tears down the tpch bundle (pipelines, jobs, and the schemas it created).

> **Genie space cleanup is handled too.** The Genie space is created via the Genie API from a
> notebook task (see DESIGN §3.19), so `bundle destroy` alone does not manage it. `destroy_tpch.sh`
> therefore trashes the space first via the CLI (`databricks genie list-spaces` / `trash-space`,
> matched by title) before destroying the bundle. This is best-effort and idempotent, safe if no
> space was ever created.

---



## Further reading

- **[GUIDE.md](./GUIDE.md)** - detailed setup & deployment (flags, jobs, one-shot script),
execution, the Day-1/2/3 demo walkthrough, and troubleshooting.
- **[DESIGN.md](./DESIGN.md)** - background & purpose, architecture overview, design choices ("the
why"), repository layout, staged source data, the Unity Catalog objects produced, and the
backlog / roadmap.

