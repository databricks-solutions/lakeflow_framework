SQL Source
==========

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
You can specify a SQL query as a source type in your Data Flow Specs. These allow for flexibility and more complex transformations to be 
supported, as needed, without overly complicating the Framework.

Sample Bundle
-------------

A sample is available in the ``gold_sample`` bundle in the ``src/dataflows/stream_static_samples`` folder and can be seen in the 
``dim_customer_sql_main.json`` file.

Configuration
-------------

**SQL Query Definition**

To define a SQL query, you need to create a ``dml`` folder under the base folder for your given Data Flow Spec. 
You can then create a ``.sql`` file for your query under this folder. 

For example:

  ::

      my_pipeline_bundle/
      ├── src/
      │   ├── dataflows
      │   │   ├── use_case_1
      │   │   │   ├── my_data_flow_spec_main.json
      │   │   │   ├── dml
      │   │   │   │   └── my_query.sql
      │   │   │   ├── expectations
      │   │   │   ├── python_functions
      │   │   │   └── schemas


Your file can contain any SQL supported by Databricks but must ultimately return a dataset as a Single query. 
You can use CTEs, subqueries, joins, etc.

**Substitution Variables**

You can use substitution variables in your SQL query by using the ``{var}`` syntax. 
These will be substituted per the :doc:`feature_substitutions documentation.

For example:

.. code-block:: sql

    SELECT * FROM {bronze_schema}.my_table

**Referencing the Python Source in a Data Flow Spec**

To reference the Python source in a Data Flow Spec, you need to specify a Python source type in your Data Flow Spec. 
Refer to the :doc:`dataflow_spec_ref_source_details` section of the :doc:`dataflow_spec_reference` documentation for more information.
