Target Catalog and Schema
=========================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Pipeline` :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     -  - `Set the target catalog and schema <https://docs.databricks.com/aws/en/ldp/target-schema>`_
        - `Configure pipelines <https://docs.databricks.com/aws/en/ldp/configure-pipeline>`_
        - `LIVE schema (legacy) <https://docs.databricks.com/aws/en/ldp/live-schema>`_

Overview
--------

Lakeflow Spark Declarative Pipelines (**SDP**) **default publishing mode** publishes
materialized views and streaming tables to Unity Catalog using the target
**catalog** and **schema** configured on the pipeline. Unqualified identifiers
resolve to those defaults unless you override them with fully qualified names
or ``USE CATALOG`` / ``USE SCHEMA`` in pipeline code.

.. Note::
  New Lakeflow Framework pipelines should set ``catalog`` and ``schema`` in the
  pipeline resource file. LFF sample bundles use default publishing mode.

.. Warning::
  Pipelines created before February 5, 2025 may still use **legacy publishing
  mode** and the ``LIVE`` virtual schema. Migrating an existing pipeline to
  default publishing mode requires destroying and redeploying with ``catalog``
  and ``schema`` configured instead of the legacy ``target`` field. Pipeline
  tables are dropped and recreated, so the next run reprocesses all data.


The Framework supports:

* `Publishing to multiple catalogs and schemas from a single pipeline <https://docs.databricks.com/aws/en/ldp/target-schema>`_
* `Legacy publishing mode and the LIVE virtual schema <https://docs.databricks.com/aws/en/ldp/live-schema>`_ for existing pipelines only


This is configured in two places:

1. In the Data Flow Spec, under the ``targetDetails`` section.
2. In the pipeline resource file (``catalog`` and ``schema``). See `Configure pipelines <https://docs.databricks.com/aws/en/ldp/configure-pipeline>`_.


Refer to the section :doc:`/build/bundle-steps` for more information.

