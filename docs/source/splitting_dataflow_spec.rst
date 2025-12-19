Splitting Flows Data Flow Spec into main and flow files
-------------------------------------------------------
A data flow spec can be broken up into a main (ending with ``_main.json|yaml``) and flow (ending with ``_flow.json|yaml``) spec file.

The main spec file will contain the main pipeline configuration and the flow spec file will contain the flow configuration and are joined by having the same dataFlowId.

To achieve this, the main spec file will have the structure described in the :doc:`dataflow_spec_ref_main_flows` schema without the :ref:`_flow-group-configuration` property and this will instead be moved to the flow spec file
The flow spec file will have the structure described in the :ref:`_flow-group-configuration` schema but the ``dataFlowID`` is now required as it will serve as the link to the main spec.

Below is a sample of how a Data Flow Spec can be split into main and flow spec files:

Original Data Flow Spec file (single unsplit file):

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

Split Data Flow Spec into main and flow files:

Main file: 

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
             "quarantineTargetDetails": {}
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

Flow file:

.. tabs::

   .. tab:: JSON

      .. code-block:: json

         {
             "dataFlowId": "etp5stg",
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

   .. tab:: YAML

      .. code-block:: yaml

         dataFlowId: etp5stg
         flowGroupId: et1
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
