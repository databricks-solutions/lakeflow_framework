Creating a Standard Data Flow Spec Reference
#############################################

A standard Data Flow Spec is the most basic type of Data Flow Spec and is suited to basic use cases where you are performing 1:1 ingestion or loads. It is particularly suited to Bronze Ingestion Use Cases.

Example Specification
---------------------

The below demonstrates a standard Data Flow Spec for a Bronze ingestion use case (refer to :doc:`patterns/basic-1-1` for more information):

.. tabs::

   .. tab:: JSON

      .. code-block:: json
         :linenos:

         {
             "dataFlowId": "crm_1",
             "dataFlowGroup": "crm",
             "dataFlowType": "standard",
             "sourceType": "delta",
             "sourceSystem": "crm",
             "sourceViewName": "v_customer_address",
             "sourceDetails": {
                 "database": "source_db",
                 "table": "customer_address",
                 "cdfEnabled": true,
                 "schemaPath": "schemas/customer_address.json"
             },
             "mode": "stream",
             "targetFormat": "delta",
             "targetDetails": {
                 "table": "customer_address",
                 "tableProperties": {
                     "delta.autoOptimize.optimizeWrite": "true",
                     "delta.autoOptimize.autoCompact": "true"
                 },
                 "partitionColumns": ["country_code"],
                 "schemaPath": "schemas/customer_address.json"
             },
             "dataQualityExpectationsEnabled": true,
             "quarantineMode": "table",
             "quarantineTargetDetails": {
                 "targetFormat": "delta",
                 "table": "customer_address_quarantine",
                 "tableProperties": {}
             },
             "cdcSettings": {
                 "keys": ["address_id"],
                 "sequence_by": "updated_timestamp",
                 "scd_type": "2",
                 "where": "",
                 "ignore_null_updates": true,
                 "except_column_list": ["updated_timestamp"],
                 "apply_as_deletes": "DELETE_FLAG = True"
             }
         }

   .. tab:: YAML

      .. code-block:: yaml
         :linenos:

         dataFlowId: crm_1
         dataFlowGroup: crm
         dataFlowType: standard
         sourceType: delta
         sourceSystem: crm
         sourceViewName: v_customer_address
         sourceDetails:
           database: source_db
           table: customer_address
           cdfEnabled: true
           schemaPath: schemas/customer_address.json
         mode: stream
         targetFormat: delta
         targetDetails:
           table: customer_address
           tableProperties:
             delta.autoOptimize.optimizeWrite: 'true'
             delta.autoOptimize.autoCompact: 'true'
           partitionColumns:
             - country_code
           schemaPath: schemas/customer_address.json
         dataQualityExpectationsEnabled: true
         quarantineMode: table
         quarantineTargetDetails:
           targetFormat: delta
           table: customer_address_quarantine
           tableProperties: {}
         cdcSettings:
           keys:
             - address_id
           sequence_by: updated_timestamp
           scd_type: '2'
           where: ''
           ignore_null_updates: true
           except_column_list:
             - updated_timestamp
           apply_as_deletes: DELETE_FLAG = True

The above data flow spec sample contains the following core components:

  * Data flow metadata configuration
  * Source configuration
  * Target configuration
  * Data quality and quarantine settings
  * CDC (SCD2) configuration

The following sections detail each of the above components.

.. _dataflow-spec-standard-metadata-configuration:

Data Flow Metadata Configuration
--------------------------------

These properties define the basic identity and type of the data flow:

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
       Supported: `["flow", "standard"]`

.. _dataflow-spec-standard-source-configuration:

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
     - The source system name. Value is not used to determine or change any behaviour, required if `dataFlowType` is `standard`.
   * - **sourceType**
     - ``string``
     - The type of source, required if `dataFlowType` is `standard`.  
       Supported: ``cloudFiles``, ``delta``, ``deltaJoin``, ``kafka``
   * - **sourceViewName**
     - ``string``
     - The name to assign the source view, required if `dataFlowType` is `standard`.  
       String Pattern: `v_([A-Za-z0-9_]+)`
   * - **sourceDetails**
     - ``object``
     - See :doc:`spec-reference/source-details` for more information.

.. _dataflow-spec-standard-target-configuration:

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
       Supported: ``["stream", "batch"]``
   * - **targetFormat**
     - ``string``
     - The format of the target data.
       If the format is `delta`, additional `targetDetails` must be provided.
   * - **targetDetails**
     - ``object``
     - See :doc:`spec-reference/target-details`.

.. _dataflow-spec-standard-cdc-configuration:

.. include:: cdc.rst

.. _dataflow-spec-standard-data-quality-configuration:

.. include:: data-quality.rst

.. _dataflow-spec-standard-table-migration-configuration:

.. include:: table-migration.rst