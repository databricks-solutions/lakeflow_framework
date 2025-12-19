Materialized Views
================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-info:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-info:`Data Flow Spec`
   * - **Databricks Docs:**
     - - `Materialized Views <https://docs.databricks.com/aws/en/dlt/materialized-views>`_
       - `Delta Live Tables Python Reference <https://docs.databricks.com/en/delta-live-tables/python-ref.html>`_
       - `Delta Live Tables SQL Reference <https://docs.databricks.com/en/delta-live-tables/sql-ref.html>`_

Overview
--------
Materialized Views are the precomputed results of a query stored in a Table. Please refer to the above documentation for full details on Materialized Views and how they work. 

Key Features:

- Automatic updates based on pipeline schedule/triggers
- Guaranteed consistency with source data. All required data is processed, even if it arrives late or out of order.
- Incremental refresh optimization. Databricks will try to choose the appropriate strategy that minimizes the cost of updating a materialized view.
- Ideal for transformations and aggregations
- Pre-computation of slow queries
- Optimization for frequently used computations

.. admonition:: Important
   :class: warning

    To support Incremental refresh, some keywords and clauses require row-tracking to be enabled on the queried data sources.
    Refer to the the following links for details on:
        - `Incremental Refresh <https://docs.databricks.com/aws/en/optimizations/incremental-refresh#support-for-materialized-view-incremental-refresh>`_
        - `Row Tracking <https://docs.databricks.com/aws/en/delta/row-tracking>`_

Sample Bundle
-------------

A sample is available in:

    - the ``bronze_sample`` bundle in the ``src/dataflows/feature_samples`` folder in the ``materialized_views_main.json|yaml`` file
    - the ``gold_sample`` bundle in the ``src/dataflows/base_samples`` folder in the ``materialized_views_main.json|yaml`` file


Data Flow Spec Configuration
---------------------------

Materialized Views are must be configured in the Materialized Views Data Flow Spec Type. This Data Flow Specification is defined in the :doc:`dataflow_spec_ref_main_materialized_views` documentation.

Data Flow Spec Configuration Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following schema details the configuration for a Materialized View Data Flow Spec:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "dataFlowId": "feature_materialized_views",
             "dataFlowGroup": "feature_samples",
             "dataFlowType": "materialized_view",
             "materializedViews": {
                 "mv_name": {
                     "sourceView": {
                         "sourceViewName": "",
                         "sourceType": "[delta|python|sql]",
                         "sourceDetails": {}
                     },
                     "sqlPath": "",
                     "sqlStatement": "",
                     "tableDetails": {
                         "database": "",
                         "schemaPath": "",
                         "tableProperties": {},
                         "path": "",
                         "partitionColumns": [],
                         "clusterByColumns": []
                     },
                     "dataQualityExpectationsEnabled": false,
                     "dataQualityExpectationsPath": "",
                     "quarantineMode": "off",
                     "quarantineTargetDetails": {}
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         dataFlowId: feature_materialized_views
         dataFlowGroup: feature_samples
         dataFlowType: materialized_view
         materializedViews:
           mv_name:
             sourceView:
               sourceViewName: ''
               sourceType: '[delta|python|sql]'
               sourceDetails: {}
             sqlPath: ''
             sqlStatement: ''
             tableDetails:
               database: ''
               schemaPath: ''
               tableProperties: {}
               path: ''
               partitionColumns: []
               clusterByColumns: []
             dataQualityExpectationsEnabled: false
             dataQualityExpectationsPath: ''
             quarantineMode: 'off'
             quarantineTargetDetails: {}

Source Type Details
~~~~~~~~~~~~~~~~~~~

Materialized Views can be configured in your Data Flow Spec in three ways:

1. **Using a Source View**
   - Define a source view that the materialized view will be based on
   - Supports Delta, Python, and SQL source types
   - Example configuration:

   .. tabs::

      .. tab:: JSON

         .. code-block:: json

            {
                "sourceView": {
                    "sourceViewName": "v_customer",
                    "sourceType": "delta",
                    "sourceDetails": {
                        "database": "{staging_schema}",
                        "table": "customer",
                        "cdfEnabled": true
                    }
                }
            }

      .. tab:: YAML

         .. code-block:: yaml

            sourceView:
              sourceViewName: v_customer
              sourceType: delta
              sourceDetails:
                database: '{staging_schema}'
                table: customer
                cdfEnabled: true

2. **Using SQL Path**
   - Reference a SQL file containing the query for the materialized view
   - Example configuration:

   .. tabs::

      .. tab:: JSON

         .. code-block:: json

            {
                "sqlPath": "./customer_mv.sql"
            }

      .. tab:: YAML

         .. code-block:: yaml

            sqlPath: ./customer_mv.sql

3. **Using SQL Statement**
   - Directly specify the SQL query for the materialized view
   - Example configuration:

   .. tabs::

      .. tab:: JSON

         .. code-block:: json

            {
                "sqlStatement": "SELECT * FROM {staging_schema}.customer"
            }

      .. tab:: YAML

         .. code-block:: yaml

            sqlStatement: SELECT * FROM {staging_schema}.customer

Additional Configuration Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Materialized Views support several additional configuration options:

- **Table Details**: Configure the target table properties
  - Database
  - Schema path
  - Table properties
  - Path
  - Partition columns
  - Cluster by columns

- **Data Quality Expectations**
  - Enable data quality checks
  - Specify expectations path
  - Configure quarantine mode (off, flag, table)

- **Quarantine Configuration**
  - Set quarantine mode
  - Configure quarantine target details

Example Configuration
-------------------

A complete example of a materialized view configuration:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "dataFlowId": "feature_materialized_views",
             "dataFlowGroup": "feature_samples",
             "dataFlowType": "materialized_view",
             "materializedViews": {
                 "mv_from_source_view": {
                     "sourceView": {
                         "sourceViewName": "v_mv_source_view",
                         "sourceType": "delta",
                         "sourceDetails": {
                             "database": "{staging_schema}",
                             "table": "customer",
                             "cdfEnabled": true
                         }
                     }
                 },
                 "mv_from_sql_path": {
                     "sqlPath": "./mv_from_sql_path.sql"
                 },
                 "mv_from_sql_statement": {
                     "sqlStatement": "SELECT * FROM {staging_schema}.customer"
                 },
                 "mv_with_quarantine": {
                     "sqlStatement": "SELECT * FROM {staging_schema}.customer_address",
                     "dataQualityExpectationsEnabled": true,
                     "dataQualityExpectationsPath": "./customer_address_dqe.json",
                     "quarantineMode": "table",
                     "quarantineTargetDetails": {
                         "targetFormat": "delta"
                     }
                 }
             }
         }

   .. tab:: YAML

      .. code-block:: yaml

         dataFlowId: feature_materialized_views
         dataFlowGroup: feature_samples
         dataFlowType: materialized_view
         materializedViews:
           mv_from_source_view:
             sourceView:
               sourceViewName: v_mv_source_view
               sourceType: delta
               sourceDetails:
                 database: '{staging_schema}'
                 table: customer
                 cdfEnabled: true
           mv_from_sql_path:
             sqlPath: ./mv_from_sql_path.sql
           mv_from_sql_statement:
             sqlStatement: SELECT * FROM {staging_schema}.customer
           mv_with_quarantine:
             sqlStatement: SELECT * FROM {staging_schema}.customer_address
             dataQualityExpectationsEnabled: true
             dataQualityExpectationsPath: ./customer_address_dqe.json
             quarantineMode: table
             quarantineTargetDetails:
               targetFormat: delta

For more detailed information about configuration options, refer to the :doc:`dataflow_spec_reference` documentation. 