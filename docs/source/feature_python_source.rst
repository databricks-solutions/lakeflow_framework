Python Source
=============

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Data Flow Spec`
   * - **Databricks Docs:**
     - NA

Overview
--------
You can specify a Python function as a source type in your Data Flow Specs. These allow for flexibility and more complex data retrieval to be 
supported, as needed, without overly complicating the Framework.

There are two approaches to defining Python sources:

1. **Pipeline logic modules**: Define functions in the ``src/python/`` directory and reference them by module name using ``pythonModule``
2. **File Path**: Define functions in ``./python_functions/`` directories and reference by file path using ``functionPath``

Sample Bundle
-------------

Samples are available in the ``feature-samples`` bundle in the ``src/dataflows/feature_samples`` folder.

Configuration
-------------

Using Pipeline Logic Modules (``src/python/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Place your Python source functions in ``src/python/`` — the framework adds this directory
to ``sys.path`` at pipeline initialisation so spec strings resolve without extra configuration.

.. admonition:: Deprecation Notice
   :class: warning

   The legacy ``src/extensions/`` directory is **deprecated as of v0.13.0** and will be
   **removed in v1.0.0**. Move ``.py`` files to ``src/python/`` — existing ``pythonModule``
   strings in Data Flow Specs are unchanged.

**1. Create a module in ``src/python/``**

Create your source functions in the ``src/python/`` directory:

::

    my_pipeline_bundle/
    ├── src/
    │   ├── python/
    │   │   └── sources.py      # Your source functions
    │   ├── dataflows/
    │   │   └── ...

Your module can contain multiple functions. Each function must:

* Accept ``spark`` (SparkSession) and ``tokens`` (Dict) as parameters
* Return a DataFrame

.. code-block:: python
   :linenos:

    # src/python/sources.py
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
    from typing import Dict

    def get_customer_cdf(spark: SparkSession, tokens: Dict) -> DataFrame:
        """
        Get customer data with Change Data Feed enabled.
        """
        source_table = tokens["sourceTable"]
        reader_options = {
            "readChangeFeed": "true"
        }

        df = spark.readStream.options(**reader_options).table(source_table)
        return df.withColumn("TEST_COLUMN", F.lit("testing from extension..."))

    def get_orders_batch(spark: SparkSession, tokens: Dict) -> DataFrame:
        """
        Get orders data as a batch read.
        """
        source_table = tokens["sourceTable"]
        return spark.read.table(source_table)

**2. Reference in Data Flow Spec**

Use ``pythonModule`` in ``sourceDetails`` to reference your function:

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :linenos:
         :emphasize-lines: 6,12

         {
             "dataFlowId": "feature_python_extension_source",
             "dataFlowGroup": "feature_samples",
             "dataFlowType": "standard",
             "sourceSystem": "testSystem",
             "sourceType": "python",
             "sourceViewName": "v_feature_python_extension_source",
             "sourceDetails": {
                 "tokens": {
                     "sourceTable": "{staging_schema}.customer"
                 },
                 "pythonModule": "sources.get_customer_cdf"
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "feature_python_extension_source",
                 "tableProperties": {
                     "delta.enableChangeDataFeed": "true"
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :linenos:
         :emphasize-lines: 6,11

         dataFlowId: feature_python_extension_source
         dataFlowGroup: feature_samples
         dataFlowType: standard
         sourceSystem: testSystem
         sourceType: python
         sourceViewName: v_feature_python_extension_source
         sourceDetails:
           tokens:
             sourceTable: '{staging_schema}.customer'
           pythonModule: sources.get_customer_cdf
         mode: stream
         targetFormat: delta
         targetDetails:
           table: feature_python_extension_source
           tableProperties:
             delta.enableChangeDataFeed: 'true'

Using File Path
~~~~~~~~~~~~~~~

To define a python source function using file paths, create a ``python_functions`` folder under the base folder for your dataflowspec:

::

    my_pipeline_bundle/
    ├── src/
    │   ├── dataflows/
    │   │   ├── use_case_1/
    │   │   │   ├── dataflowspec/
    │   │   │   │   └── my_data_flow_spec_main.json
    │   │   │   ├── python_functions/
    │   │   │   │   └── my_source_function.py
    │   │   │   └── schemas/

Your file must contain a function called ``get_df`` that:

* Accepts ``spark`` (SparkSession) and ``tokens`` (Dict) as parameters
* Returns a DataFrame

.. code-block:: python
   :linenos:

    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql import functions as F
    from typing import Dict

    def get_df(spark: SparkSession, tokens: Dict) -> DataFrame:
        """
        Get a DataFrame from the source details with applied transformations.
        """
        source_table = tokens["sourceTable"]
        reader_options = {
            "readChangeFeed": "true"
        }

        df = spark.readStream.options(**reader_options).table(source_table)
        return df.withColumn("TEST_COLUMN", F.lit("testing..."))

**Reference using functionPath:**

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :linenos:
         :emphasize-lines: 6,12

         {
             "dataFlowId": "feature_python_function_source",
             "dataFlowGroup": "feature_samples",
             "dataFlowType": "standard",
             "sourceSystem": "testSystem",
             "sourceType": "python",
             "sourceViewName": "v_feature_python_function_source",
             "sourceDetails": {
                 "tokens": {
                     "sourceTable": "{staging_schema}.customer"
                 },
                 "functionPath": "my_source_function.py"
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "feature_python_function_source"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :linenos:
         :emphasize-lines: 6,11

         dataFlowId: feature_python_function_source
         dataFlowGroup: feature_samples
         dataFlowType: standard
         sourceSystem: testSystem
         sourceType: python
         sourceViewName: v_feature_python_function_source
         sourceDetails:
           tokens:
             sourceTable: '{staging_schema}.customer'
           functionPath: my_source_function.py
         mode: stream
         targetFormat: delta
         targetDetails:
           table: feature_python_function_source

sourceDetails Schema for Python Source
--------------------------------------

When using ``sourceType: "python"``, the ``sourceDetails`` object supports the following properties:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Required
     - Description
   * - ``pythonModule``
     - One of pythonModule/functionPath
     - Module and function reference (e.g., ``sources.get_customer_cdf``). The module must be in the ``src/python/`` directory.
   * - ``functionPath``
     - One of pythonModule/functionPath
     - Path to a Python file containing a ``get_df`` function. Resolved relative to the ``./python_functions/`` directory.
   * - ``tokens``
     - No
     - Dictionary of token values to pass to the source function. Supports substitution variables like ``{staging_schema}``.

Function Signatures
-------------------

**For Extensions (pythonModule)**

The function name can be anything, but it must accept ``spark`` and ``tokens``:

.. code-block:: python
   :linenos:

    def my_source_function(spark: SparkSession, tokens: Dict) -> DataFrame:
        ...

**For File Path (functionPath)**

The function must be named ``get_df``:

.. code-block:: python
   :linenos:

    def get_df(spark: SparkSession, tokens: Dict) -> DataFrame:
        ...

Additional Resources
--------------------

Refer to the :doc:`dataflow_spec_ref_source_details` section of the :doc:`dataflow_spec_reference` documentation for more information on source configuration.
