Creating a Flows Data Flow Spec Reference
#############################################

A standard Data Flow Spec is the most basic type of Data Flow Spec and is suited to basic use cases where you are performing 1:1 ingestion or loads. It is particularly suited to Bronze Ingestion Use Cases.

Example:
--------

The below sample demonstrates a flows Data Flow Spec for a Silver multi-source streaming use case (refer to :doc:`patterns_streaming_multi_source_streaming` for more information):

.. tabs::

   .. tab:: JSON

      .. code-block:: json

        {
            "dataFlowId": "etp5stg",
            "dataFlowGroup": "etp5",
            "dataFlowType": "flow",
            "targetFormat": "delta",
            "targetDetails": {
                "table": "staging_table_mrg_p5",
                "schemaPath": "",
                "tableProperties": {
                    "delta.enableChangeDataFeed": "true"
                },
                "partitionColumns": []
            },
            "cdcSettings": {
                "keys": [
                    "CONTRACT_ID"
                ],
                "sequence_by": "EXTRACT_DTTM",
                "where": "",
                "ignore_null_updates": true,
                "except_column_list": [
                    "__START_AT",
                    "__END_AT"
                ],
                "scd_type": "2",
                "track_history_column_list": [],
                "track_history_except_column_list": []
            },
            "dataQualityExpectationsEnabled": false,
            "quarantineMode": "off",
            "quarantineTargetDetails": {},
            "flowGroups": [
                {
                    "flowGroupId": "et1",
                    "stagingTables": {
                        "staging_table_apnd_p5": {
                            "type": "ST",
                            "schemaPath": ""
                        }
                    },
                    "flows": {
                        "f_contract": {
                            "flowType": "append_view",
                            "flowDetails": {
                                "targetTable": "staging_table_apnd_p5",
                                "sourceView": "v_brz_contract"
                            },
                            "views": {
                                "v_brz_contract": {
                                    "mode": "stream",
                                    "sourceType": "delta",
                                    "sourceDetails": {
                                        "database": "main.bronze_test_4",
                                        "table": "contract",
                                        "cdfEnabled": true,
                                        "selectExp": [
                                            "*"
                                        ],
                                        "whereClause": []
                                    }
                                }
                            }
                        },
                        "f_loan": {
                            "flowType": "append_view",
                            "flowDetails": {
                                "targetTable": "staging_table_apnd_p5",
                                "sourceView": "v_brz_loan"
                            },
                            "views": {
                                "v_brz_loan": {
                                    "mode": "stream",
                                    "sourceType": "delta",
                                    "sourceDetails": {
                                        "database": "main.bronze_test_4",
                                        "table": "loan",
                                        "cdfEnabled": true,
                                        "selectExp": [
                                            "*"
                                        ],
                                        "whereClause": []
                                    }
                                }
                            }
                        },
                        "f_merge": {
                            "flowType": "merge",
                            "flowDetails": {
                                "targetTable": "staging_table_mrg_p5",
                                "sourceView": "staging_table_apnd_p5"
                            }
                        }
                    }
                }
            ]
        }

   .. tab:: YAML

      .. code-block:: yaml

        dataFlowId: etp5stg
        dataFlowGroup: etp5
        dataFlowType: flow
        targetFormat: delta
        targetDetails:
          table: staging_table_mrg_p5
          schemaPath: ''
          tableProperties:
            delta.enableChangeDataFeed: 'true'
          partitionColumns: []
        cdcSettings:
          keys:
            - CONTRACT_ID
          sequence_by: EXTRACT_DTTM
          where: ''
          ignore_null_updates: true
          except_column_list:
            - __START_AT
            - __END_AT
          scd_type: '2'
          track_history_column_list: []
          track_history_except_column_list: []
        dataQualityExpectationsEnabled: false
        quarantineMode: 'off'
        quarantineTargetDetails: {}
        flowGroups:
          - flowGroupId: et1
            stagingTables:
              staging_table_apnd_p5:
                type: ST
                schemaPath: ''
            flows:
              f_contract:
                flowType: append_view
                flowDetails:
                  targetTable: staging_table_apnd_p5
                  sourceView: v_brz_contract
                views:
                  v_brz_contract:
                    mode: stream
                    sourceType: delta
                    sourceDetails:
                      database: main.bronze_test_4
                      table: contract
                      cdfEnabled: true
                      selectExp:
                        - '*'
                      whereClause: []
              f_loan:
                flowType: append_view
                flowDetails:
                  targetTable: staging_table_apnd_p5
                  sourceView: v_brz_loan
                views:
                  v_brz_loan:
                    mode: stream
                    sourceType: delta
                    sourceDetails:
                      database: main.bronze_test_4
                      table: loan
                      cdfEnabled: true
                      selectExp:
                        - '*'
                      whereClause: []
              f_merge:
                flowType: merge
                flowDetails:
                  targetTable: staging_table_mrg_p5
                  sourceView: staging_table_apnd_p5

The above dataflow spec sample contains the following core components:

  * Dataflow metadata configuration
  * Target configuration
  * Data quality and quarantine settings
  * Flow group configuration

The following sections detail each of the above components.

.. _dataflow-spec-flows-metadata-configuration:

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
     - The type of data flow. It can be either `flow` or `standard`.  
       Supported: ``flow``, ``standard``

.. _dataflow-spec-flows-target-configuration:

Target Configuration
---------------------

These properties define where and how the data will be written:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **mode**
     - ``string``
     - The mode of the data flow.
       Supported: ``stream``, ``batch``
   * - **targetFormat**
     - ``string``
     - The format of the target data.
       If the format is `delta`, additional `targetDetails` must be provided.
   * - **targetDetails**
     - ``object``
     - See :doc:`dataflow_spec_ref_target_details`.

.. _dataflow-spec-flows-flow-groups-configuration:

Flow Group Configuration
------------------------

The `flowGroupDetails` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **dataFlowID** (*optional*)
     - ``string``
     - A unique identifier for the data flow. Only required when dataflow specs are split (see :doc:`splitting_dataflow_spec`).
   * - **flowGroupId**
     - ``string``
     - A unique identifier for the flow group.
   * - **stagingTables** (*optional*)
     - ``object``
     - An object containing named objects representing staging tables in the flow group. The key for each nested object in this object will become the table names for the staging tables.
   * - **flows**
     - ``array``
     - An array of flows in the flow group. Items: :ref:`flow-configuration`


.. _dataflow-spec-flows-staging-table-configuration:

Staging Table Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `stagingTableDetails` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **type**
     - ``string``
     - The type of the staging table can be either a Streaming Table or Materialized View. Supported: ``ST``, ``MV``
   * - **schemaPath** (*optional*)
     - ``string``
     - The schema path of the staging table.
   * - **partitionColumns** (*optional*)
     - ``array``
     - An array of partition columns for the staging table. Items: ``string``
   * - **cdcSettings** (*optional*)
     - ``object``
     - Change data capture (CDC) settings. Object: :doc:`dataflow_spec_ref_cdc`

.. admonition:: Recommendation
   :class: tip

   It is recommended that you avoid specifying a schema path for staging tables, in order to reduce maintenance overhead and to take advantage of schema evolution.

.. _dataflow-spec-flows-flow-configuration:

Flow Configuration
~~~~~~~~~~~~~~~~~~

A `flow` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **enabled**
     - ``boolean``
     - A flag indicating whether the flow is enabled.
   * - **flowType**
     - ``string``
     - The type of the flow.
       Supported: ``append_view``, ``append_sql``, ``merge``
   * - **flowDetails**
     - ``object``
     - Details about the flow, required based on `flowType`.  
       Properties vary based on `flowType`. See :ref:`Flow Details<Flow Details>`.
   * - **views** (*optional*)
     - ``object``
     - An object containing views used in the flow. The key for each nested object in this object will become the view names.

.. _dataflow-spec-flows-flow-details:

Flow Details
~~~~~~~~~~~~~

The `flowDetails` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Flow Type**
     - **Property**
     - **Type**
     - **Description**
   * - **append_sql**
     - **targetTable**
     - ``string``
     - The target table for the SQL append flow.
   * - 
     - **sqlPath**
     - ``string``
     - The path to the SQL file for the append flow.
   * - **append_view**
     - **targetTable**
     - ``string``
     - The target table for the view append flow.
   * - 
     - **sourceView**
     - ``string``
     - The source view for the append flow.
   * - 
     - **column_prefix** (*optional*)
     - ``string``
     - The prefix for columns in the target table.
   * - 
     - **column_prefix_exceptions** (*optional*)
     - ``array``
     - An array of columns that are exceptions to the prefix rule.
   * - **merge**
     - **targetTable**
     - ``string``
     - The target table for the merge flow.
   * - 
     - **sourceView**
     - ``string``
     - The source view for the merge flow.

.. _dataflow-spec-flows-view-configuration:

View Configuration
~~~~~~~~~~~~~~~~~~

The `viewDetails` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **mode**
     - ``string``
     - The mode of the view, either `batch` or `stream`.  
       Supported: ``batch``, ``stream``
   * - **sourceType**
     - ``string``
     - The type of the source. 
       Supported: ``cloudFiles``, ``delta``, ``deltaJoin``, ``sql``
   * - **columnsToUpdate** (*optional*)
     - ``array``
     - An array of columns to update.  
       Items: ``string``
   * - **sourceDetails** (*conditional*)
     - ``object``
     - See :doc:`dataflow_spec_ref_source_details`.



.. _dataflow-spec-flows-cdc-configuration:

.. include:: dataflow_spec_ref_cdc.rst

.. _dataflow-spec-flows-data-quality-configuration:

.. include:: dataflow_spec_ref_data_quality.rst

.. _dataflow-spec-flows-table-migration-configuration:

.. include:: dataflow_spec_ref_table_migration.rst
