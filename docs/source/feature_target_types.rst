Supported Target Types
======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta-live-tables/python-ref.html

The Lakeflow Framework supports multiple target types. 

Target Types
------------
.. list-table::
   :header-rows: 1
   :widths: 20 100 100

   * - **Type**
     - **Description**
     - **Key Features**
   * - **Delta Streaming Table**
     - Creates a streaming Delta table that continuously processes and updates data as it arrives.
     -  - Streaming write optimizations
        - Automatic schema evolution
        - Quality enforcement
        - Incremental processing
   * - **Materialized Views**
     - A materialized view is a view that contains precomputed records based on the query that defines the materialized view. Materialized views are commonly used for transformations and Gold Layer tables.
     -  - Automatic updates based on pipeline schedule/triggers
        - Guaranteed consistency with source data
        - Incremental refresh optimization
        - Ideal for transformations and aggregations
        - Pre-computation of slow queries
        - Optimization for frequently used computations
        - Detailed configuration details: :doc:`feature_materialized_views`
   * - **Delta Sink**
     - Stream records to a Delta tables.
     -  - Product documentation: https://docs.databricks.com/en/dlt/dlt-sinks
        - Limitations: https://docs.databricks.com/en/dlt/dlt-sinks#limitations
   * - **Kafka Sink**
     - Stream records to a Kafka topic.
     -  - Product documentation: https://docs.databricks.com/en/dlt/dlt-sinks
        - Limitations: https://docs.databricks.com/en/dlt/dlt-sinks#limitations
   * - **Foreach Batch Sink**
     - Enables processing each micro-batch with custom logic similar to the Spark Structured Streaming `foreachBatch` functionality. With the ForEachBatch sink, you can transform, merge, or write streaming data to one or more targets that do not natively support streaming writes
     -  - Product documentation: to be release (Private Preview)
        - Limitations: Similar to https://docs.databricks.com/en/dlt/dlt-sinks#limitations
        
General Data Flow Spec Configuration
------------------------------------

Set as an attribute when creating your Data Flow Spec, refer to the :doc:`dataflow_spec_reference` documentation for more information:

* :doc:`dataflow_spec_ref_source_details`
* :doc:`dataflow_spec_ref_target_details`

Detailed Target Type Configuration Details
------------------------------------------

.. toctree::
   :maxdepth: 1

   feature_materialized_views
