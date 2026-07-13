What is the Lakeflow Framework?
===============================

The Lakeflow Framework (**LFF**) is a metadata-driven framework for building Databricks Lakeflow Spark Declarative Pipelines. It uses a configuration-driven, pattern-based approach to support both batch and streaming workloads across the medallion architecture. Deploy the **Framework Bundle** once, then **Pipeline Bundles** for your data flows — with Declarative Automation Bundles (DABs) for flat workspace deploy (default) or the ``lakeflow-framework`` PyPI wheel (v0.20.0+). Optional ``contrib`` packages extend the core framework with community integrations. The framework is designed for simplicity, extensibility, and long-term alignment with the Databricks product roadmap.

.. include:: ../_lff_architecture_diagram.rst


Why teams use it
----------------

* Faster delivery through reusable pipeline patterns
* Simple, extensible, and long-term alignment with the Databricks product roadmap
* Lower maintenance overhead as platform features evolve
* Consistent configuration model across environments
* Centralized configuration inheritance — pipelines resolve global settings at runtime
* Native alignment with Declarative Automation Bundles (DABs)

Core outcomes
-------------

* Build and deploy reliable Databricks Lakeflow Spark Declarative Pipelines
* Support Bronze/Silver/Gold medallion workloads
* Support centralized and domain-oriented operating models, including data mesh and data product approaches
* Accommodate multiple modeling paradigms, including dimensional, Data Vault, and enterprise canonical models
* Keep implementation extensible without heavy custom scaffolding

Core concepts
-------------

* **Pattern-based pipeline design**: reusable building blocks standardize implementation and reduce duplication.
* **Framework and Pipeline Bundles**: deploy the Framework Bundle to the workspace first, then one or more Pipeline Bundles that reference it at ``framework_source_path`` (see :doc:`/deploy/before-you-deploy`).
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
* Silver refinement pipelines for modeling, quality, and conformance
* Gold serving pipelines for consumption-ready datasets
* Mixed static/streaming and CDC-oriented topologies

The framework composes Spark Declarative Pipelines into repeatable, configuration-driven patterns while keeping implementation behavior explicit and maintainable.

Next steps
----------

Back to :doc:`/index` for the guided path (Quick Start → Concepts → Build / Deploy) or jump straight into Architecture, Samples, Build, Deploy, or Features from the top navigation.
