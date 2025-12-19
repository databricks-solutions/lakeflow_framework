Builder Parallelization
=======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Global` :bdg-success:`Pipeline Configuration`
   * - **Databricks Docs:**
     - NA

Overview
--------
The Lakeflow Framework supports parallel processing during both dataflow specification building and pipeline initialization phases to improve performance and reduce initialization time. 
This feature utilizes ThreadPoolExecutor to process multiple operations concurrently, which is particularly beneficial for:

- Large pipelines with many dataflow specifications
- Complex dataflow specifications requiring validation and transformation

The framework automatically detects the number of logical CPU cores available on the Spark driver using ``os.cpu_count()`` and sets the default max workers to ``cores - 1`` to reserve one core for system operations. This ensures optimal performance while maintaining system stability. If CPU core detection fails, the framework falls back to a default of 1 worker thread.

Parameters
----------

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Parameter**
     - **Type**
     - **Default Value**
     - **Phase**
     - **Description**
   * - ``override_max_workers``
     - Integer
     - NA
     - Pipeline Initialization
     - Should only be used if the auto-detected default is not working. Controls the maximum number of worker threads used when:

       - Reading dataflow specification files from the filesystem
       - Validating dataflow specifications against schemas
       - Applying dataflow specification version mappings and transformations
       - Creating DataFlow objects from dataflow specifications
       - Initializing SDP tables, views, and streaming tables
   * - ``pipeline_builder_disable_threading``
     - Boolean
     - False
     - Pipeline Initialization
     - Disables threading when creating DataFlow objects

Configuration
-------------

Global Configuration
~~~~~~~~~~~~~~~~~~~~~
Configure these parameters globally for all pipelines in your ``src/config/global.json|yaml`` file:

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 7

         {
             "spark_config": {
                 "spark.databricks.sql.streamingTable.cdf.applyChanges.returnPhysicalCdf": true,
                 "pipelines.streamingFlowReadOptionsEnabled": true,
                 "pipelines.externalSink.enabled": true
             },
             "override_max_workers": 4,
             "mandatory_table_properties": {
                 "delta.logRetentionDuration": "interval 45 days",
                 "delta.deletedFileRetentionDuration": "interval 45 days",
                 "delta.enableRowTracking": "true"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 5

         spark_config:
           spark.databricks.sql.streamingTable.cdf.applyChanges.returnPhysicalCdf: true
           pipelines.streamingFlowReadOptionsEnabled: true
           pipelines.externalSink.enabled: true
         override_max_workers: 4
         mandatory_table_properties:
           delta.logRetentionDuration: interval 45 days
           delta.deletedFileRetentionDuration: interval 45 days
           delta.enableRowTracking: 'true'

Troubleshooting
---------------

**Debugging Core Detection:**

The framework logs the detected core count and calculated default max workers during initialization:

.. code-block:: text

    INFO - Logical cores (threads): 4
    INFO - Default max workers: 3
