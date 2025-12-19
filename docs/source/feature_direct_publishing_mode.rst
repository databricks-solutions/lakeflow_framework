Direct Publishing Mode
======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Pipeline` :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     -  - https://docs.databricks.com/aws/en/dlt/target-schema
        - https://docs.databricks.com/aws/en/dlt/configure-pipeline

.. Note::
  Direct publishing mode should be enabled by default for all new pipelines by specifing the ``schema`` field in the pipeline resource file. Sample pipeline have been updated to have direct publishing mode enabled. To enable direct publishing mode on existing pipelines, the pipeline needs to be destroyed and redeployed with the ``target`` field updated to ``schema`` in the pipeline resource file.

.. Warning::
  Destroying and redeploying a pipeline to enable direct publishing mode will result in the pipeline tables being dropped and recreated and therefore, will reprocess all the data on the next run of the pipeline.


The Framework supports:

* `Publishing to multiple catalogs and schemas from a single pipeline <https://docs.databricks.com/aws/en/dlt/target-schema>`_
* `Legacy Live Schema Publishing <https://docs.databricks.com/aws/en/dlt/live-schema>`_


This is configured in two places:

1. In the Data Flow Spec, under the ``targetDetails`` section.
2. In the pipeline resource file. Databricks Spark Declarative Pipeline Settings documentation: https://docs.databricks.com/aws/en/dlt/configure-pipeline


Refer to the section :doc:`build_pipeline_bundle_steps` for more information.


