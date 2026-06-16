Getting Started
===============

The following section is a quick start guide on how to get started with the Lakeflow Framework as a data engineer.

Prerequisites
-------------

1. Databricks CLI installed and configured, if you are using DABs to locally deploy the Lakeflow Framework and Pipeline Bundles.
2. Access to a Databricks workspace.
3. VSCode installed.

Setup
-----

Follow the below steps to get yourself setup to learn and use the Lakeflow Framework:

1. :doc:`deploy_framework`
2. :doc:`deploy_samples`
3. :doc:`feature_auto_complete`

Understanding the Framework
---------------------------
1. :doc:`concepts`
2. Step through the ``feature-samples`` bundle — run the ``feature_samples_run_job`` and inspect the resulting tables in the ``{namespace}_feature`` schema. This is the simplest entry point as all features share a single schema.
3. :doc:`features`

Developing your first Pipeline Bundle
-------------------------------------

1. Select from one of the recommended pipeline patterns that best fits your use case, as documented in :doc:`patterns`
2. Build and deploy a data pipeline bundle. Refer to :doc:`build_pipeline_bundle`.