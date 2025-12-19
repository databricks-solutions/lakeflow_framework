Multi-Source Streaming
=====================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta-live-tables/flows.html

Delta Live Tables supports processing that requires reading data from multiple streaming sources to update a single streaming table via:

* **Append Flows** - Append streams from multiple sources to a single streaming table.
* **Change Flows** - Process CDC events from multiple sources to a single streaming table, using the CDC API's.

The Lakeflow Framework implements this capability via the Data Flow Spec using the concept of flow groups and flows. 

Configuration
-------------

In a Pipeline Bundle bundle, multi-source streaming is configured in the Data Flow Spec using the ``flow_groups`` and ``flows`` attributes. 
This is documented in :ref:`_flow-group-configuration` and :ref:`_flow-configuration`. 

Key Features
-----------
- Write to a single streaming table from multiple source streams
- Add or Remove streaming sources without requiring a full table refresh
- Support for backfilling historical data
- Alternative to UNION operations for combining multiple sources
- Maintain separate checkpoints for each flow

Important Considerations
----------------------
- Flow names are used to identify streaming checkpoints
- Renaming an existing flow creates a new checkpoint
- Flow names must be unique within a pipeline
- Data quality expectations should be defined on the target table, not in flow definitions
- Append flows provide more efficient processing compared to UNION operations for combining multiple sources
- Append SQL flows do not support quarantine table mode (they do support quarantine flag mode). This is because quarantine table mode requires a source view.

See Also
--------
- :doc:`feature_source_target_types`
- :doc:`dataflow_spec_ref_source_details`
- :doc:`dataflow_spec_ref_target_details`