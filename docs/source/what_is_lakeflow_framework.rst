What is the Lakeflow Framework?
===============================

The Lakeflow Framework is a metadata-driven framework for building Databricks Lakeflow Spark Declarative Pipelines. It uses a configuration-driven, pattern-based approach to support both batch and streaming workloads across the medallion architecture. Deploy the **Framework Bundle** once, then **Pipeline Bundles** for your data flows — with Declarative Automation Bundles (DABs) for flat workspace deploy (default) or the ``lakeflow-framework`` PyPI wheel (v0.20.0+). Optional ``contrib`` packages extend the core framework with community integrations. The framework is designed for simplicity, extensibility, and long-term alignment with the Databricks product roadmap.

.. image:: images/lff-architecture-v1-two-boxes.jpg
   :alt: Lakeflow Framework architecture — Framework Bundle and Pipeline Bundle on a DABS Foundation
   :align: center

Why teams use it
----------------

* Faster delivery through reusable pipeline patterns
* Consistent configuration model across environments
* Native alignment with Declarative Automation Bundles (DABs)
* Simple, extensible, and long-term alignment with the Databricks product roadmap
* Lower maintenance overhead as platform features evolve

Core outcomes
-------------

* Build and deploy reliable Databricks Lakeflow Spark Declarative Pipelines
* Support Bronze/Silver/Gold medallion workloads
* Support centralized and domain-oriented operating models, including data mesh and data product approaches
* Accommodate multiple modelling paradigms (modeling paradigms), including dimensional, Data Vault, and enterprise canonical models
* Keep implementation extensible without heavy custom scaffolding

Core concepts
-------------

* **Pattern-based pipeline design**: reusable building blocks standardize implementation and reduce duplication.
* **Framework and Pipeline Bundles**: deploy the Framework Bundle to the workspace first, then one or more Pipeline Bundles that reference it at ``framework_source_path`` (see :doc:`deploy_before_you_deploy`).
* **Two-layer architecture**:

  * SDP wrapper components expose Spark Declarative Pipelines APIs directly, keeping behavior explicit and close to the platform.
  * The Data Flow Spec abstraction layer composes those components into consistent, configuration-driven pipeline definitions.

* **Deployment and operations principles**:

  * DABs-native deployment — flat workspace deploy (default) or ``pip install lakeflow-framework`` (v0.20.0+)
  * Optional ``contrib`` integrations without expanding core package dependencies
  * Minimal third-party dependencies
  * No control tables
  * Extensible framework structure
  * Flexible bundle-based delivery across environments

Medallion pipeline patterns
---------------------------

The Lakeflow Framework supports common Databricks medallion architecture patterns for both batch and streaming workloads:

* Bronze ingestion pipelines for raw landing
* Silver refinement pipelines for modelling, quality, and conformance
* Gold serving pipelines for consumption-ready datasets
* Mixed static/streaming and CDC-oriented topologies

The framework composes Spark Declarative Pipelines into repeatable, configuration-driven patterns while keeping implementation behavior explicit and maintainable.

Next steps
----------

* Start with :doc:`quick_start`
* Review architecture in :doc:`concepts`
* Explore practical implementations in :doc:`patterns`
* Review spec-level options in :doc:`dataflow_spec_reference`
* Build pipeline bundles in :doc:`build_pipeline_bundle`
* Deploy the framework and pipelines via :doc:`deploy` — read :doc:`deploy_before_you_deploy` first for deploy order and ownership
