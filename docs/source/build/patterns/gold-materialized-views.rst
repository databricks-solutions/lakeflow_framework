Pattern - Gold Materialized Views
=================================

Description
------------
Suitable for gold-layer serving tables built from silver (or other upstream) tables using materialized views.

Use when:

- You want batch or incremental batch serving at gold (dimensions, facts, aggregates).
- Lower latency than a scheduled notebook job is sufficient.
- You prefer declarative SQL over streaming-first gold pipelines.

**Layers:** Gold

**Models:** Dimensional (dimensions and facts), data marts, curated aggregates

.. note::

   For gold workloads, materialized views are generally the first choice unless you need streaming-first gold with lower latency. See :doc:`/features/platform/materialized-views`.

**Data Flow Components:**

.. md-mermaid::

   flowchart LR
     UP["Upstream table(s)<br/>(e.g. silver SCD2)"]
     MV["Materialized View(s)<br/>SQL in spec"]
     UP --> MV

.. list-table::
   :header-rows: 1

   * - No.
     - Component
     - Description
     - M / O
   * - 1
     - Upstream table(s)
     - Silver (or gold) tables referenced in MV SQL — often current-state SCD2 or conformed entities.
     - M
   * - 2
     - Materialized view spec
     - ``dataFlowType: materialized_view`` with one or more MV definitions (including chained MVs).
     - M

Feature Support
----------------

.. list-table::
   :header-rows: 1

   * - Supported
     - Not Supported
   * - * Full and incremental refresh policies
       * Chained materialized views
       * Joins across upstream tables in MV SQL
     - * Multi-source streaming topology (use silver streaming patterns first)

Sample
------
- Bundle: ``samples/pattern-samples``
- Pipeline: ``Lakeflow Framework - Pattern - Base Gold Samples Pipeline``
- Sample: ``samples/pattern-samples/src/dataflows/base_samples/gold/dataflowspec/gold_materialized_views_main.json``

For stream-static gold dimensions (streaming silver into gold), see ``samples/pattern-samples/src/dataflows/stream_static_samples/dataflowspec/gold_dim_customer_json_main.json`` and the stream-static pattern pages.
