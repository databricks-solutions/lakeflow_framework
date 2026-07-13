Data Flow and Pipeline Patterns
###############################

.. _patterns_overview:

Reference patterns for designing data flows and pipelines. 

Start with :doc:`Base Patterns </build/patterns/base-patterns>` (bronze → silver → gold), then adopt :doc:`Advanced composition </build/patterns/advanced-composition>` patterns when sources, keys, or join semantics require them.

* Operating models and modeling paradigms: :doc:`/architecture/index`
* :doc:`/features/platform/multi-source-streaming`
* :doc:`/build/bundle-structure`
* :doc:`/build/patterns/scaling-decomposing-pipelines`
* :doc:`/build/patterns/mix-and-match-patterns`
* SDP concepts (datasets, flows): `Lakeflow Spark Declarative Pipelines — key concepts <https://docs.databricks.com/aws/en/ldp/concepts/#key-concepts>`_

When selecting a pattern, start with ownership model, modeling approach, source characteristics (streaming, static, CDC), and latency needs.

.. note::

   These patterns are **not an exhaustive catalog** of everything the Lakeflow Framework supports. They are a curated **starting point** — common building blocks and composition approaches that align with the bundled ``pattern-samples`` and what most teams implement first. Combine, extend, or depart from them as your sources, modeling, and operational constraints require.

.. tip::

   **Runnable samples:** End-to-end specs live in ``samples/pattern-samples`` (bronze → silver → gold, multi-source streaming, stream-static joins, CDC from snapshot, gold materialized views, and more). See :doc:`/samples/index` for deploy steps. Each pattern page links to the matching specs in that bundle; advanced pattern pages also include multi-day example data flows for SCD and late-arriving behavior.

.. rubric:: Base Patterns

These patterns match the default ``pattern-samples`` bronze, silver, and gold pipelines. Most new projects begin here. See also :doc:`/build/patterns/base-patterns`.

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Pattern
     - Description
   * - :doc:`/build/patterns/basic-1-1`
     - **Basic 1:1** — the default building block for most pipelines: bronze source ingest and source-aligned silver or lightly transformed conformed entities (append, SCD1, or SCD2) from one streaming source to one target.
   * - :doc:`/build/patterns/gold-materialized-views`
     - **Gold — materialized views** — gold serving tables from silver using full or incremental MV refresh.
   * - :doc:`/build/patterns/cdc-stream-from-snapshot`
     - **CDC from snapshot** — build a CDC stream from snapshot sources (building block).

.. rubric:: Advanced composition

Use when multiple sources, snapshot CDC, or stream-static join semantics apply. See also :doc:`/build/patterns/advanced-composition`.

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Pattern
     - Description
   * - :doc:`/build/patterns/multi-source-streaming`
     - **Multi-source streaming** — shared keys, staging append/merge, basic transforms.
   * - :doc:`/build/patterns/stream-static-basic`
     - **Stream-static — basic** — one driving stream joined to static tables.
   * - :doc:`/build/patterns/stream-static-streaming-dwh`
     - **Stream-static — streaming DWH** — CDF-driven joins when any table may change.

.. rubric:: Scaling and decomposing pipelines

Decompose monolithic pipelines across flow groups and staging tables. See :doc:`/build/patterns/scaling-decomposing-pipelines`.

.. rubric:: Mix and Match Patterns

Combine multiple patterns within one pipeline or data flow. See :doc:`/build/patterns/mix-and-match-patterns`.

.. toctree::
   :maxdepth: 2
   :hidden:

   Base Patterns <base-patterns>
   Advanced composition <advanced-composition>
   Scaling and decomposing pipelines <scaling-decomposing-pipelines>
   Mix and Match Patterns <mix-and-match-patterns>
