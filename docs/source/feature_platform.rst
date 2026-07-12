Supported Databricks Features
=============================

These are **Databricks / SDP (and related) product features** that the Lakeflow
Framework **exposes through the data flow spec**. They are not LFF inventions —
each page covers **what we surface**, **how you configure it in LFF**, and links
to Databricks Docs for full product semantics.

Source and target **type catalogs** live under :doc:`feature_sources_targets`.
Data quality **expectations** live under :doc:`feature_data_quality`.

.. toctree::
   :maxdepth: 1

   Change Data Capture (CDC) <feature_cdc>
   Change Data Feed (CDF) <feature_cdf>
   Multi-Source Streaming (Flows)<feature_multi_source_streaming>
   Liquid Clustering <feature_liquid_clustering>
   Materialized Views <feature_materialized_views>
   Schema-related Databricks Features <feature_databricks_schema_features>
   Soft Deletes <feature_soft_deletes>
   Target Catalog and Schema <feature_target_catalog_schema>
