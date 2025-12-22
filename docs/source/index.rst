.. Lakeflow Framework documentation master file, created by
   sphinx-quickstart on Mon Nov 25 17:16:32 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Lakeflow Framework documentation
=================================

The Lakeflow Framework is a metadata-driven data engineering framework built for Databricks. It accelerates and simplifies the deployment of Spark Declarative Pipelines (SDP) while supporting your entire software development lifecycle.

**Key Capabilities:**

* Build robust data pipelines using a configuration-driven, Lego-block approach
* Support batch and streaming workloads across the medallion architecture (Bronze, Silver, Gold)
* Deploy seamlessly with Databricks Asset Bundles (DABS)—no wheel files or control tables required
* Extend and maintain easily as your data platform evolves

This documentation covers everything from getting started to advanced orchestration patterns. Explore the sections below to begin building reliable, maintainable data pipelines.

.. toctree::
   :maxdepth: 4
   :caption: Contents:
   
   Introduction <introduction>
   getting_started
   Concepts <concepts> 
   Features <features>
   deploy_framework
   deploy_samples
   build_pipeline_bundle
   dataflow_spec_reference
   orchestration
   contributor
   logical_environment
