Creating a Materialized View Data Flow Spec Reference
####################################################

A Materialized View Data Flow Spec is designed for creating and maintaining materialized views that aggregate or transform data from source tables.


Schema
------

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

Example:
--------

The below demonstrates a Materialized View Data Flow Spec:

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
                    },
                    "tableDetails": {
                        "database": "{gold_schema}",
                        "tableProperties": {
                            "delta.autoOptimize.optimizeWrite": "true",
                            "delta.autoOptimize.autoCompact": "true"
                        },
                        "clusterByColumns": ["year", "month"],
                        "schemaPath": "schemas/customer_metrics_mv.json"
                    },
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
            tableDetails:
              database: '{gold_schema}'
              tableProperties:
                delta.autoOptimize.optimizeWrite: 'true'
                delta.autoOptimize.autoCompact: 'true'
              clusterByColumns:
                - year
                - month
              schemaPath: schemas/customer_metrics_mv.json
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

The above dataflow spec sample contains the following core components:

  * Dataflow metadata configuration
  * Source configuration
  * Table configuration
  * Data quality and quarantine settings

The following sections detail each of the above components.

.. _dataflow-spec-materialized-view-metadata-configuration:

Dataflow Metadata Configuration
-------------------------------

These properties define the basic identity and type of the dataflow:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **dataFlowId**
     - ``string``
     - A unique identifier for the data flow.
   * - **dataFlowGroup**
     - ``string``
     - The group to which the data flow belongs, can be the same as `dataFlowId` if there is no group.
   * - **dataFlowType**
     - ``string``
     - The type of data flow. Must be `materialized_view` for materialized view dataflows.

.. _dataflow-spec-materialized-view-source-configuration:

Source Configuration
---------------------

These properties define the source of the data:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **sourceSystem** (*optional*)
     - ``string``
     - The source system name. Value is not used to determine or change any behaviour.
   * - **sourceType**
     - ``string``
     - The type of source.  
       Supported: ``cloudFiles``, ``delta``, ``sql``, ``python``
   * - **sourceViewName**
     - ``string``
     - The name to assign the source view.  
       String Pattern: `v_([A-Za-z0-9_]+)`
   * - **sourceDetails**
     - ``object``
     - See :doc:`dataflow_spec_ref_source_details` for more information.

.. _dataflow-spec-materialized-view-table-configuration:

Table Configuration
------------------------------

These properties define the materialized view specific configuration:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **tableDetails**
     - ``object``
     - Configuration specific to materialized views.
   * - **database**
     - ``string``
     - The schema to write the materialized view to.
   * - **schemaPath**
     - ``string``
     - The path to the schema file for the materialized view.
   * - **tableProperties**
     - ``object``
     - The table properties to set on the materialized view.
   * - **path**
     - ``string``
     - A storage location for table data. If not set, use the managed storage location for the schema containing the table.
   * - **partitionColumns**
     - ``array``
     - The columns to partition the materialized view by.
   * - **clusterByColumns**
     - ``array``
     - The suggested columns to cluster the materialized view by.
   * - **comment**
     - ``string``
     - A description for the materialized view.
   * - **spark_conf** (*optional*)
     - ``object``
     - A list of Spark configurations for the execution of this query.
   * - **private** (*optional*)
     - ``boolean``
     - Create a table, but do not publish the table to the metastore.

.. _dataflow-spec-materialized-view-data-quality-configuration:

.. include:: dataflow_spec_ref_data_quality.rst
