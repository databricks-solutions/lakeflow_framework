Supported Databricks Features
=============================

These are **Databricks / SDP (and related) product features** that the Lakeflow
Framework **exposes through the data flow spec**. They are not LFF inventions —
each page covers **what we surface**, **how you configure it in LFF**, and links
to Databricks Docs for full product semantics.

Source and target **type catalogs** live under :doc:`features_sources_targets`.
Data quality **expectations** live under :doc:`features_data_quality`.

.. toctree::
   :maxdepth: 1

   Change Data Capture (CDC) <feature_cdc>
   Change Data Feed (CDF) <feature_cdf>
   Soft Deletes <feature_soft_deletes>
   Multi-Source Streaming <feature_multi_source_streaming>
   Materialized Views <feature_materialized_views>
   Liquid Clustering <feature_liquid_clustering>
   Schema Definitions <feature_schemas>
   Direct Publishing Mode <feature_direct_publishing_mode>
