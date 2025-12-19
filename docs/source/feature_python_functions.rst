Python Function Transforms
===============================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Pipeline`
   * - **Databricks Docs:**
     - NA

Overview
--------
You can specify custom Python functions or transforms in your Pipeline Bundle and then reference these in your data flow specs.
These allow for flexibility and more complex transformations to be supported without overly complicating the Framework.

The functions get called and executed by the framework directly after a View reads from its source.

There are two approaches to defining Python transforms:

1. **Extensions**: Define functions in the ``src/dataflows/extensions/`` directory and reference them by module name
2. **File Path**: Define functions in ``./python_functions/`` directories and reference by file path

Sample Bundle
-------------

Samples are available in the ``bronze_sample`` bundle in the ``src/dataflows/feature_samples`` folder.

Configuration
-------------

Using Extensions
~~~~~~~~~~~~~~~~

The extensions approach allows you to organize your Python functions in a central location and import them as standard Python modules.

**1. Create an Extension Module**

Create your transform functions in the ``extensions/`` directory at the bundle root:

::

    my_pipeline_bundle/
    ├── src/
    │   ├── extensions/
    │   │   └── transforms.py      # Your transform functions
    │   ├── dataflows/
    │   │   └── ...

Your extension module can contain multiple functions:

.. code-block:: python

    # src/extensions/transforms.py
    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F
    from typing import Dict

    def customer_aggregation(df: DataFrame) -> DataFrame:
        """
        Apply customer aggregation transformation.
        """
        return (
            df.withWatermark("load_timestamp", "10 minutes")
            .groupBy("CUSTOMER_ID")
            .agg(F.count("*").alias("COUNT"))
        )

    def customer_aggregation_with_tokens(df: DataFrame, tokens: Dict) -> DataFrame:
        """
        Apply aggregation with configurable parameters from tokens.
        """
        watermark_column = tokens.get("watermarkColumn", "load_timestamp")
        watermark_delay = tokens.get("watermarkDelay", "10 minutes")
        group_by_column = tokens.get("groupByColumn", "CUSTOMER_ID")
        
        return (
            df.withWatermark(watermark_column, watermark_delay)
            .groupBy(group_by_column)
            .agg(F.count("*").alias("COUNT"))
        )

**2. Reference in Data Flow Spec**

Use ``pythonTransform.module`` to reference your function:

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 12-14

         {
             "dataFlowId": "feature_python_extension_transform",
             "dataFlowGroup": "feature_samples",
             "dataFlowType": "standard",
             "sourceSystem": "testSystem",
             "sourceType": "delta",
             "sourceViewName": "v_feature_python_extension_transform",
             "sourceDetails": {
                 "database": "{staging_schema}",
                 "table": "customer",
                 "cdfEnabled": true,
                 "pythonTransform": {
                     "module": "transforms.customer_aggregation"
                 }
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "feature_python_extension_transform",
                 "tableProperties": {
                     "delta.enableChangeDataFeed": "true"
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 11-12

         dataFlowId: feature_python_extension_transform
         dataFlowGroup: feature_samples
         dataFlowType: standard
         sourceSystem: testSystem
         sourceType: delta
         sourceViewName: v_feature_python_extension_transform
         sourceDetails:
           database: '{staging_schema}'
           table: customer
           cdfEnabled: true
           pythonTransform:
             module: transforms.customer_aggregation
         mode: stream
         targetFormat: delta
         targetDetails:
           table: feature_python_extension_transform
           tableProperties:
             delta.enableChangeDataFeed: 'true'

**Using Tokens with Extensions**

You can pass configuration tokens to your transform function:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         "pythonTransform": {
             "module": "transforms.customer_aggregation_with_tokens",
             "tokens": {
                 "watermarkColumn": "event_timestamp",
                 "watermarkDelay": "5 minutes",
                 "groupByColumn": "ORDER_ID"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         pythonTransform:
           module: transforms.customer_aggregation_with_tokens
           tokens:
             watermarkColumn: event_timestamp
             watermarkDelay: 5 minutes
             groupByColumn: ORDER_ID


Using File Path
~~~~~~~~~~~~~~~

To define a python function using file paths, create a ``python_functions`` folder under the base folder for your dataflowspec:

::

    my_pipeline_bundle/
    ├── src/
    │   ├── dataflows/
    │   │   ├── use_case_1/
    │   │   │   ├── dataflowspec/
    │   │   │   │   └── my_data_flow_spec_main.json
    │   │   │   ├── python_functions/
    │   │   │   │   └── my_function.py
    │   │   │   └── schemas/

Your file must contain a function called ``apply_transform`` that:

* Takes a DataFrame as the first parameter (and optionally tokens as the second)
* Returns a DataFrame

.. code-block:: python

    from pyspark.sql import DataFrame
    from pyspark.sql import functions as F

    def apply_transform(df: DataFrame, tokens: Dict) -> DataFrame:
        """
        Apply a transformation to the DataFrame.
        """
        return (
            df.withWatermark("load_timestamp", "1 minute")
            .groupBy("CUSTOMER_ID")
            .agg(F.count("*").alias("COUNT"))
        )

**Reference using pythonTransform.functionPath:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :emphasize-lines: 12-14

         {
             "dataFlowId": "feature_python_function_transform",
             "dataFlowGroup": "feature_samples",
             "dataFlowType": "standard",
             "sourceSystem": "testSystem",
             "sourceType": "delta",
             "sourceViewName": "v_feature_python_function_transform",
             "sourceDetails": {
                 "database": "{staging_schema}",
                 "table": "customer",
                 "cdfEnabled": true,
                 "pythonTransform": {
                     "functionPath": "my_function.py"
                 }
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "feature_python_function_transform"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :emphasize-lines: 11-12

         dataFlowId: feature_python_function_transform
         dataFlowGroup: feature_samples
         dataFlowType: standard
         sourceSystem: testSystem
         sourceType: delta
         sourceViewName: v_feature_python_function_transform
         sourceDetails:
           database: '{staging_schema}'
           table: customer
           cdfEnabled: true
           pythonTransform:
             functionPath: my_function.py
         mode: stream
         targetFormat: delta
         targetDetails:
           table: feature_python_function_transform

pythonTransform Schema
----------------------

The ``pythonTransform`` object supports the following properties:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Required
     - Description
   * - ``module``
     - One of module/functionPath
     - Module and function reference (e.g., ``transforms.customer_aggregation``). The module must be in the ``src/dataflows/extensions/`` directory.
   * - ``functionPath``
     - One of module/functionPath
     - Path to a Python file containing an ``apply_transform`` function. Resolved relative to the ``./python_functions/`` directory.
   * - ``tokens``
     - No
     - Dictionary of token values to pass to the transform function. The function signature must accept ``tokens`` as a second parameter.

