Supported Source Types
======================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta-live-tables/python-ref.html

The Lakeflow Framework supports multiple source types. Each source type provides specific configuration 
options to handle different data ingestion scenarios.

Source Types
------------

.. list-table::
   :header-rows: 1
   :widths: 20 100 100

   * - **Type**
     - **Description**
     - **Key Features**
   * - **Batch Files**
     - Reads data from UC Volumes orcloud storage locations (e.g., S3, ADLS, GCS). Supports various file formats and provides options for filtering and transforming data during ingestion.
     -  - Flexible path-based file access
        - Reader options for different file formats
        - Optional select expressions and where clauses
        - Schema on read support
   * - **Cloud Files**
     - Reads data from UC Volumes or cloud storage locations (e.g., S3, ADLS, GCS). Supports various file formats and provides options for filtering and transforming data during ingestion.
     -  - Flexible path-based file access
        - Reader options for different file formats
        - Optional select expressions and where clauses
        - Schema on read support
   * - **Delta**
     - Connects to existing Delta tables in the metastore, supporting both batch and streaming reads with change data feed (CDF) capabilities.
     -  - Database and table-based access
        - Change Data Feed (CDF) support
        - Optional path-based access
        - Configurable reader options
   * - **Delta Join**
     - Enables joining multiple Delta tables, supporting both streaming and static join patterns.
     -  - Multiple source table configuration
        - Stream and static join modes
        - Left and inner join support
        - Flexible join conditions
        - Per-source CDF configuration
   * - **Kafka**
     - Enables reading from Apache Kafka topics for real-time streaming data processing.
     -  - Kafka-specific reader options
        - Schema definition support
        - Filtering and transformation support
        - Topic-based configurations
        - Demux and fan-out support
   * - **Python**
     - Allows using a Python function as a data source, providing flexibility for complex data transformations.
     -  - Python file-based configuration
        - Functions stored in `python_functions` subdirectory
        - Full Python / Pyspark capabilities
        - Detailed configuration details: :doc:`feature_python_source`
   * - **SQL**
     - Allows using SQL queries as data sources, providing flexibility for complex data transformations.
     -  - SQL file-based configuration
        - Queries stored in `dml` subdirectory
        - Full SQL transformation capabilities
        - Detailed configuration details: :doc:`feature_sql_source`

General Data Flow Spec Configuration
------------------------------------

Set as an attribute when creating your Data Flow Spec, refer to the :doc:`dataflow_spec_reference` documentation for more information:

* :doc:`dataflow_spec_ref_source_details`
* :doc:`dataflow_spec_ref_target_details`

Detailed Source Type Configuration Details
------------------------------------------

.. toctree::
   :maxdepth: 1

   feature_python_source
   feature_sql_source
