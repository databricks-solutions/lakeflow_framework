Schemas
=======

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - NA

The Framework supports the defintiion of schemas in the following ways:

* Schema on Read:
    * A schema can be specified on most sources using JSON StructType format
* Schema on Write: 
    * A schema can be specified for Staging or Target tables using JSON StructType format or text DDL format.

Schema Types
------------

.. list-table::
   :header-rows: 0

   * - **Type**
     - **Description**
     - **Supports**
   * - JSON StructType
     - Allows you to specify the schema as a StructType in JSON format.
     - - Can be used for both Schema on Read and Schema on Write.
       - Can be used to define columns only.
   * - Text DDL
     - Allows you to specify the schema as a text DDL format.
     - - Can only be used to specify the schemas for your staging or target tables.
       - Feature Support: 

         - `Constraints <https://docs.databricks.com/aws/en/tables/constraints>`_
         - `Generated Columns <https://docs.databricks.com/aws/en/delta/generated-columns>`_
         - `Column Masking Functions <https://docs.databricks.com/aws/en/dlt/unity-catalog#row-filters-and-column-masks>`_

Schema File Location
--------------------

Schemas must be specified in their own dedicated files and will be locatated in a schemas folder, dependant on your chosen bundle structure as dicussed in the :doc:`build_pipeline_bundle_structure` section.

Data Flow Spec Configuration
---------------------------

Schema files are then referenced in the Data Flow Spec configuration for the source, staging table or target table they apply to. Refer to the :doc:`data_flow_spec` section for more information.


StructType JSON Format
----------------------

* Can be used for both Schema on Read and Schema on Write.
* File name: ``<name>.json``, the file MUST have a ``.json`` extension.
* Documentation:

    * PySpark StructType documentation: https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.types.StructType.html
    * Databricks Data Types documentation: https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html

Generating the Schema Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**PySpark:**

If you have your data in Databricks, you can can read your source into a dataframe and then use the following code to generate the JSON schema format:

.. code-block:: python

    df.schema.jsonValue()

**LLM:**

In Perplexity or ChatGPT the following prompt will generate the JSON schema format:

Prompt::

    Convert the following schema definition into the equivalent Databricks StructType JSON format. The output should be a valid JSON object representing the schema, including all field names, data types, nullability, and nested structures where applicable. Do not include any explanatory text—just the JSON output.

    Input schema:
    [Insert schema definition here]


For Example:
~~~~~~~~~~~~

.. code-block:: json
    :emphasize-lines: 1-3, 40-41

    {
        "type": "struct",
        "fields": [
            {
                "name": "CUSTOMER_ID",
                "type": "integer",
                "nullable": true,
                "metadata": {}
            },
            {
                "name": "FIRST_NAME",
                "type": "string",
                "nullable": true,
                "metadata": {}
            },
            {
                "name": "LAST_NAME",
                "type": "string",
                "nullable": true,
                "metadata": {}
            },
            {
                "name": "EMAIL",
                "type": "string",
                "nullable": true,
                "metadata": {}
            },
            {
                "name": "DELETE_FLAG",
                "type": "boolean",
                "nullable": true,
                "metadata": {}
            },
            {
                "name": "LOAD_TIMESTAMP",
                "type": "timestamp",
                "nullable": true,
                "metadata": {}
            }
        ]
    }

.. important::

    The highlighted wrapping struct fields declaration is mandatory.


Text DDL Format
---------------

* Can only be used to specify the schemas for your staging or target tables.
* Feature support:
    * Constraints - https://docs.databricks.com/aws/en/tables/constraints
    * Generated Columns - https://docs.databricks.com/aws/en/delta/generated-columns
    * Column Masking Functions - https://docs.databricks.com/aws/en/dlt/unity-catalog#row-filters-and-column-masks
* File name: ``<name>.ddl``, the file MUST have a ``.ddl`` extension.
* Documentation:

    * CREATE TABLE Documentation: https://docs.databricks.com/gcp/en/sql/language-manual/sql-ref-syntax-ddl-create-table-using

.. admonition:: DDL Format Rules
   :class: note
    
    * Each column must be defined on a new line
    * Use ``--`` to comment out columns (they will be removed from the schema)
    * Column names and data types must be valid according to Databricks SQL specifications

Examples
~~~~~~~~

Basic Schema Definition:

.. code-block:: text

    CUSTOMER_ID integer NOT NULL,
    FIRST_NAME string,
    LAST_NAME string,
    EMAIL string,
    DELETE_FLAG boolean,
    LOAD_TIMESTAMP timestamp

Schema Definition with Constraint and Generated Column:

.. code-block:: text
    :emphasize-lines: 7, 8

    CUSTOMER_ID integer NOT NULL,
    FIRST_NAME string,
    LAST_NAME string,
    EMAIL string,
    DELETE_FLAG boolean,
    LOAD_TIMESTAMP timestamp,
    LOAD_YEAR int GENERATED ALWAYS AS (YEAR(LOAD_TIMESTAMP)),
    CONSTRAINT pk_customer PRIMARY KEY(CUSTOMER_ID)

Schema Definition with Comments:

.. code-block:: text
    :emphasize-lines: 7

    CUSTOMER_ID integer NOT NULL,
    FIRST_NAME string,
    LAST_NAME string,
    EMAIL string,
    DELETE_FLAG boolean,
    LOAD_TIMESTAMP timestamp,
    -- CONSTRAINT pk_customer PRIMARY KEY(CUSTOMER_ID)
