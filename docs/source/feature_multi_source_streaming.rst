Multi-Source Streaming (Flows)
==============================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - `Load and process data incrementally with Lakeflow pipeline flows <https://docs.databricks.com/en/delta-live-tables/flows.html>`_

Overview
--------

Lakeflow Spark Declarative Pipelines (**SDP**) **flows** support reading from
multiple streaming sources to update a single streaming table:

* **Append flows** — append streams from multiple sources to one streaming table.
* **Change flows** — process CDC events from multiple sources into one streaming
  table via the AUTO CDC APIs.

A key benefit of the flows model is operational flexibility: you can add or remove
flow groups and individual flows as requirements evolve, without breaking the
existing pipeline or requiring a full table refresh.

The Lakeflow Framework exposes SDP flows through the data flow spec using
``flow_groups`` and ``flows``.

Configuration
-------------

In a Pipeline Bundle, multi-source streaming is configured in the Data Flow Spec
using the ``flow_groups`` and ``flows`` attributes.
This is documented in :ref:`flow-group-configuration <dataflow-spec-flows-flow-groups-configuration>` and :ref:`flow-configuration <dataflow-spec-flows-flow-configuration>`. 

Key Features
------------
- Write to a single streaming table from multiple source streams
- Evolve flow groups and flows over time without a full table refresh
- Support for historical backfill
- Alternative to UNION operations for combining multiple sources
- Maintain separate checkpoints for each flow

Important Considerations
------------------------
- Flow names are used to identify streaming checkpoints
- Renaming an existing flow creates a new checkpoint
- Flow names must be unique within a pipeline
- Data quality expectations should be defined on the target table, not in flow definitions
- Append flows provide more efficient processing compared to UNION operations for combining multiple sources
- Append SQL flows do not support quarantine table mode (they do support quarantine flag mode). This is because quarantine table mode requires a source view.

See Also
--------
- :doc:`feature_source_types`
- :doc:`feature_target_types`
- :doc:`dataflow_spec_ref_source_details`
- :doc:`dataflow_spec_ref_target_details`