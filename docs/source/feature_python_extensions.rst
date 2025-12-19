Python Extensions
=================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Pipeline`

Overview
--------
Python Extensions allow data engineers to write custom Python modules that extend the framework's capabilities. Extensions are organized in a central ``extensions/`` directory and can be imported as standard Python modules throughout your dataflow specifications.

.. important::

    Extensions provide a powerful mechanism for implementing custom logic—sources, transforms, and sinks—while maintaining clean separation between framework code and business logic.

This feature allows development teams to:

- **Centralize Custom Logic**: Organize all custom Python code in one location
- **Reuse Across Dataflows**: Reference the same functions from multiple dataflow specs
- **Maintain Clean Imports**: Use standard Python module imports (e.g., ``transforms.my_function``)
- **Manage Dependencies**: Install additional Python packages via ``requirements_additional.txt``
- **Test Independently**: Extensions can be unit tested outside of Spark Declarative Pipelines

.. note::

    Extensions are loaded during pipeline initialization when the framework adds the ``extensions/`` directory to the Python path. Any additional dependencies specified in ``requirements_additional.txt`` are installed before the pipeline starts.

How It Works
------------

The extension system consists of three main components:

1. **Extensions Directory**: A ``src/extensions/`` folder in your pipeline bundle containing Python modules
2. **Module References**: Dataflow specs reference extension functions using ``module`` syntax (e.g., ``transforms.my_function``)
3. **Dependency Management**: Optional ``requirements_additional.txt`` files for installing pip packages

Directory Structure
^^^^^^^^^^^^^^^^^^^

Extensions live in the ``src/extensions/`` directory of your pipeline bundle:

::

    my_pipeline_bundle/
    ├── src/
    │   ├── extensions/
    │   │   ├── __init__.py           # Optional, for package imports
    │   │   ├── sources.py            # Custom source functions
    │   │   ├── transforms.py         # Custom transform functions
    │   │   └── sinks.py              # Custom sink functions
    │   ├── dataflows/
    │   │   └── ...
    │   └── pipeline_configs/
    │       └── ...
    └── requirements_additional.txt   # Optional pip dependencies

Dependency Management
---------------------

Extensions may require additional Python packages beyond the framework's core dependencies. For detailed information on managing Python dependencies, see :doc:`feature_python_dependency_management`.

Extension Examples
------------------

Source Extensions
^^^^^^^^^^^^^^^^^

Custom functions that generate DataFrames for use as data sources.


.. code-block:: python
   :caption: src/extensions/sources.py

    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
    from typing import Dict

    def get_customer_cdf(spark: SparkSession, tokens: Dict) -> DataFrame:
        """
        Get customer data with Change Data Feed enabled.
        """
        source_table = tokens["sourceTable"]
        reader_options = {"readChangeFeed": "true"}
        
        return (
            spark.readStream
            .options(**reader_options)
            .table(source_table)
        )

    def get_api_data(spark: SparkSession, tokens: Dict) -> DataFrame:
        """
        Fetch data from an external API.
        """
        import requests  # From requirements_additional.txt
        
        api_url = tokens["apiUrl"]
        response = requests.get(api_url)
        data = response.json()
        
        return spark.createDataFrame(data)

**Reference in Dataflow Spec:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 12

         {
             "dataFlowId": "customer_from_extension",
             "dataFlowGroup": "my_dataflows",
             "dataFlowType": "standard",
             "sourceSystem": "custom",
             "sourceType": "python",
             "sourceViewName": "v_customer",
             "sourceDetails": {
                 "tokens": {
                     "sourceTable": "{staging_schema}.customer"
                 },
                 "pythonModule": "sources.get_customer_cdf"
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "customer"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 10

         dataFlowId: customer_from_extension
         dataFlowGroup: my_dataflows
         dataFlowType: standard
         sourceSystem: custom
         sourceType: python
         sourceViewName: v_customer
         sourceDetails:
           tokens:
             sourceTable: '{staging_schema}.customer'
           pythonModule: sources.get_customer_cdf
         mode: stream
         targetFormat: delta
         targetDetails:
           table: customer

Transform Extensions
^^^^^^^^^^^^^^^^^^^^

Custom functions that transform DataFrames after they are read from a source.

**Function Signatures:**

.. code-block:: python

    # Without tokens
    def my_transform(df: DataFrame) -> DataFrame:
        ...

    # With tokens
    def my_transform_with_tokens(df: DataFrame, tokens: Dict) -> DataFrame:
        ...

**Example:**

.. code-block:: python
   :caption: src/extensions/transforms.py

    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F
    from typing import Dict

    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F

    def explode_deletes_function_transform(df: DataFrame) -> DataFrame:
        """
        Duplicates delete records and adjusts sequence_by timestamp.
        For deletes: is_delete=0 gets +1ms, is_delete=1 gets +2ms.
        """
        # Create array: [0,1] for deletes, [0] for others, then explode
        sequence_column = "LOAD_TIMESTAMP"
        change_type_column = "meta_cdc_operation"

        is_delete = F.col(change_type_column) == "delete"
        array_col = F.when(is_delete, F.array(F.lit(0), F.lit(1))).otherwise(F.array(F.lit(0)))
        
        return (
            df.withColumnRenamed("_change_type", change_type_column)
            .withColumn("is_delete", F.explode(array_col))
            .withColumn(
                sequence_column, 
                F.when(is_delete & (F.col("is_delete") == 0), 
                    F.col(sequence_column) + F.expr("INTERVAL 1 millisecond"))
                .when(is_delete & (F.col("is_delete") == 1), 
                    F.col(sequence_column) + F.expr("INTERVAL 2 millisecond"))
                .otherwise(F.col(sequence_column))
            )
        )

**Reference in Dataflow Spec:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 12-14

         {
             "dataFlowId": "customer",
             "dataFlowGroup": "my_dataflows",
             "dataFlowType": "standard",
             "sourceSystem": "erp",
             "sourceType": "delta",
             "sourceViewName": "v_customer",
             "sourceDetails": {
                 "database": "{bronze_schema}",
                 "table": "customer",
                 "cdfEnabled": true,
                 "pythonTransform": {
                     "module": "transforms.explode_deletes_function_transform",
                 }
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "customer"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 11-12

         dataFlowId: customer
         dataFlowGroup: my_dataflows
         dataFlowType: standard
         sourceSystem: erp
         sourceType: delta
         sourceViewName: v_customer
         sourceDetails:
           database: '{bronze_schema}'
           table: customer
           cdfEnabled: true
           pythonTransform:
             module: transforms.explode_deletes_function_transform
         mode: stream
         targetFormat: delta
         targetDetails:
           table: customer_aggregated

Sink Extensions
^^^^^^^^^^^^^^^

Custom functions for ``foreach_batch_sink`` targets that process micro-batches.

**Function Signature:**

.. code-block:: python

    def my_batch_handler(df: DataFrame, batch_id: int, tokens: Dict) -> None:
        """
        Process a micro-batch of data.
        
        Args:
            df: The micro-batch DataFrame
            batch_id: The batch identifier
            tokens: Dictionary of token values from the dataflow spec
        """
        ...

**Example:**

.. code-block:: python
   :caption: src/extensions/sinks.py

    from pyspark.sql import DataFrame
    from typing import Dict

    def write_to_external_api(df: DataFrame, batch_id: int, tokens: Dict) -> None:
        """
        Send each batch to an external API.
        """
        import requests  # From requirements_additional.txt
        
        api_url = tokens["apiUrl"]
        api_key = tokens["apiKey"]
        
        # Convert to JSON and send
        records = df.toJSON().collect()
        for record in records:
            requests.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=record
            )

**Reference in Dataflow Spec:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 19

         {
             "dataFlowId": "customer_to_api",
             "dataFlowGroup": "my_dataflows",
             "dataFlowType": "standard",
             "sourceSystem": "erp",
             "sourceType": "delta",
             "sourceViewName": "v_customer_api",
             "sourceDetails": {
                 "database": "{silver_schema}",
                 "table": "customer",
                 "cdfEnabled": true
             },
             "mode": "stream",
             "targetFormat": "foreach_batch_sink",
             "targetDetails": {
                 "name": "customer_api_sink",
                 "type": "python_function",
                 "config": {
                     "module": "sinks.write_to_external_api",
                     "tokens": {
                         "apiUrl": "https://api.example.com/customers",
                         "apiKey": "{api_secret_key}"
                     }
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 17

         dataFlowId: customer_to_api
         dataFlowGroup: my_dataflows
         dataFlowType: standard
         sourceSystem: erp
         sourceType: delta
         sourceViewName: v_customer_api
         sourceDetails:
           database: '{silver_schema}'
           table: customer
           cdfEnabled: true
         mode: stream
         targetFormat: foreach_batch_sink
         targetDetails:
           name: customer_api_sink
           type: python_function
           config:
             module: sinks.write_to_external_api
             tokens:
               apiUrl: https://api.example.com/customers
               apiKey: '{api_secret_key}'

Additional Resources
--------------------

- :doc:`feature_python_dependency_management` - Managing Python dependencies
- :doc:`feature_python_source` - Using Python as a source type
- :doc:`feature_python_functions` - Python transform functions (file path approach)
- :doc:`dataflow_spec_ref_source_details` - Complete source configuration reference
- :doc:`dataflow_spec_ref_target_details` - Complete target configuration reference

