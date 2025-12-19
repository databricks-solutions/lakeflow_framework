Target Details Reference
#######################

The target details object specifies how and where data should be written in your dataflow. This section documents the configuration options available for different target formats.

.. _dataflow_spec_ref_target_details_delta:

Delta Target Details
-------------------

When using Delta format as your target, the following properties are available:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **table**
     - ``string``
     - The name of the target table.
   * - **database** (*optional*)
     - ``string``
     - The database name for the target table. If not specified, the default database will be used.
   * - **tableProperties** (*optional*)
     - ``object``
     - A map of Delta table properties to set on the target table. Common properties include:
       
       - ``delta.autoOptimize.optimizeWrite``
       - ``delta.autoOptimize.autoCompact``
       - ``delta.enableChangeDataFeed``
   * - **partitionColumns** (*optional*)
     - ``array[string]``
     - List of columns to partition the table by.
   * - **clusterBy** (*optional*)
     - ``array[string]``
     - List of columns to cluster the table by.
   * - **clusterByAuto** (*optional*)
     - ``boolean``
     - When true, the clustering keys will be automatically selected based on the data in the table.
   * - **schemaPath** (*optional*)
     - ``string``
     - Path to a schema file that defines the expected structure of the target table.
   * - **mergeSchema** (*optional*)
     - ``boolean``
     - When true, allows the schema to be updated when new columns are present in the source.
   * - **overwriteSchema** (*optional*)
     - ``boolean``
     - When true, allows complete replacement of the existing schema with a new one.
   * - **comment**
     - ``string``
     - A description for the materialized view.
   * - **spark_conf** (*optional*)
     - ``object``
     - A list of Spark configurations for the execution of this query.

.. _dataflow_spec_ref_target_details_kafka:

Delta Sink Target Details
-------------------

When using a Delta Sink as a target, the following properties are available:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **name**
     - ``string``
     - The name of the Delta Sink.
   * - **sinkOptions**
     - ``object``
     - The options for the Delta Sink.

Delta sinkOptions
~~~~~~~~~~~~~~~~~

Please refer to the Databricks documentation for the most up to date information on the Delta Sink: https://docs.databricks.com/en/dlt/dlt-sinks

You must specify one of the below properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **tableName**
     - ``string``
     - The fully qualified name of the Delta table to write to. Three level namespace for UC e.g. `catalog_name.schema_name.table_name`
   * - **path**
     - ``string``
     - The path to the Delta table to write to e.g. `/Volumes/catalog_name/schema_name/volume_name/path/to/data`


Kafka Sink Target Details
-------------------------

When using a Kafka Sink as a target, the following properties are available:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **name**
     - ``string``
     - The name of the Kafka topic to write records to.
   * - **sinkOptions**
     - ``object``
     - Kafka configuration properties as key-value pairs.

.. _dataflow_spec_ref_target_details_kafka_options:

Kafka sinkOptions
~~~~~~~~~~~~~~~~~

The `kafkaOptions` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Option**
     - **Type**
     - **Description**
   * - **kafka.bootstrap.servers**
     - ``string``
     - The Kafka bootstrap servers connection string
   * - **kafka.group.id**
     - ``string``
     - The consumer group ID
   * - **kafka.security.protocol**
     - ``string``
     - Security protocol to use (defaults to SASL_SSL)
   * - **kafka.ssl.truststore.location**
     - ``string``
     - Location of the SSL truststore file
   * - **kafka.ssl.truststore.password.accessKeyName**
     - ``string``
     - Access key name for the truststore password
   * - **kafka.ssl.truststore.password.secretScopeName**
     - ``string``
     - Secret scope name containing the truststore password
   * - **kafka.ssl.keystore.location**
     - ``string``
     - Location of the SSL keystore file
   * - **kafka.ssl.keystore.password.accessKeyName**
     - ``string``
     - Access key name for the keystore password
   * - **kafka.ssl.keystore.password.secretScopeName**
     - ``string``
     - Secret scope name containing the keystore password

Foreach Batch Sink Target Details
--------------------------------

When using a Foreach Batch Sink as a target, the following properties are available:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **name**
     - ``string``
     - The name of the Foreach Batch Sink.
   * - **type**
     - ``string``
     - The type of the Foreach Batch Sink. Supported values: `["basic_sql", "python_function"]`
   * - **config**
     - ``object``
     - The configuration for the Foreach Batch Sink type.

Foreach Batch basic_sql config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `basic_sql` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **database**
     - ``string``
     - The database name for the target table. If not specified, the default database will be used.
   * - **table**
     - ``string``
     - The name of the target table.
   * - **sqlPath**
     - ``string``
     - The path to the SQL file to execute.
   * - **sqlStatement**
     - ``string``
     - The SQL statement to execute. This is an alternative to `sqlPath` and is mutually exclusive with it.
   * - **partitionBy** (*optional*)
     - ``array[string]``
     - List of columns to partition the table by.
   * - **clusterBy** (*optional*)
     - ``array[string]``
     - List of columns to cluster the table by.
   * - **tableProperties** (*optional*)
     - ``object``
     - A map of Delta table properties to set on the target table.

.. note::
   The SELECT statement specified via the `sqlPath` or `sqlStatement` property must:
   
   * reference `micro_batch_view` as the source table in the FROM clause of the query that retrieves data from the sourve view.
   * be a batch query i.e. do not wrap the `micro_batch_view` in a STREAM() function.
   
Basic example:

  .. code-block:: sql
  
    SELECT
      *
    FROM micro_batch_view

Subquery Example:

.. code-block:: sql
  
    SELECT
      *
    FROM (

      SELECT
        *
      FROM micro_batch_view
    )

CTE Example:

  .. code-block:: sql
  
    WITH source_cte AS (
      SELECT
        *
      FROM micro_batch_view
    )

    SELECT
      *
    FROM source_cte

Foreach Batch python_function config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `python_function` config object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **functionPath** (*optional*)
     - ``string``
     - The path to the Python file, which should live in the `python_functions` subdirectory.
   * - **module** (*optional*)
     - ``string``
     - The module to import the Python function from.
   * - **tokens** (*optional*)
     - ``object``
     - A map of tokens to pass to the Python function.

.. important::

   - You must select one of `functionPath` or `module`.
