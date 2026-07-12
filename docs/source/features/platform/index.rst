Key Databricks Features
=============================

The Lakeflow Framework (LFF) aims to expose **Lakeflow Spark Declarative Pipelines
(SDP)** functionality through the data flow spec — so you can configure product
behavior in metadata rather than bespoke pipeline code.

These are Databricks / SDP capabilities, not LFF inventions. Where we surface
something in the spec, a feature page explains what LFF exposes, how you
configure it, and links to Databricks Docs for full product semantics.

Not every SDP capability has (or needs) a dedicated feature page here. We
document the **key** areas teams configure most often through LFF; other SDP
behavior may still be available via the spec or pipeline resources without its
own page. For the full product picture, start with `Lakeflow Spark Declarative
Pipelines <https://docs.databricks.com/aws/en/ldp/>`_ in Databricks Docs.

Source and target type catalogs live under :doc:`features/sources-targets/index`.
Data quality expectations live under :doc:`features/data-quality/index`.

.. toctree::
   :maxdepth: 1

   Change Data Capture (CDC) <cdc>
   Change Data Feed (CDF) <cdf>
   Multi-Source Streaming (Flows) <multi-source-streaming>
   Liquid Clustering <liquid-clustering>
   Materialized Views <materialized-views>
   Schema-related Databricks Features <databricks-schema-features>
   Soft Deletes <soft-deletes>
   Target Catalog and Schema <target-catalog-schema>
