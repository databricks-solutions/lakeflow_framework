Change Data Capture (CDC)
=========================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta-live-tables/cdc.html

Lakeflow Declarative Pipelines simplifies change data capture (CDC) with the AUTO CDC and AUTO CDC FROM SNAPSHOT APIs.

* Use AUTO CDC to process changes from a change data feed (CDF).
* Use AUTO CDC FROM SNAPSHOT to process changes in database snapshots.

Both AUTO CDC and AUTO CDC FROM SNAPSHOT support:

* Updating tables using SCD type 1 and type 2
    * Use SCD type 1 to update records directly. History is not retained for updated records.
    * Use SCD type 2 to retain a history of records, either on all updates or on updates to a specified set of columns.
* Out of order records
* Retaining a history of records, either on all updates or on updates to a specified set of columns.

Use of AUTO CDC FROM SNAPSHOT
-----------------------------
There are two ways to use the AUTO CDC FROM SNAPSHOT feature:

1. To process changes from a snapshot of a table/view periodically (**periodic**)

   - This can be used in both ``standard`` and ``flow`` data flow types (refer to :ref:`dataflow types` for more information).
   - For this to be enabled, the ``cdcSnapshotSettings`` object must be configured with the ``snapshotType`` set to ``periodic`` and must be chained so that a source is available to ingest the snapshots.
   
   A new snapshot is ingested with each pipeline update, and the ingestion time is used as the snapshot version. When a pipeline is run in continuous mode, multiple snapshots are ingested with each pipeline update on a period determined by the trigger interval setting for the flow that contains the AUTO CDC FROM SNAPSHOT processing

2. To process historical snapshot from a file or table based source which has multiple snapshots available at any given time (**historical**)
   
   - This can only be used in ``standard`` data flow types.
   - For this to be enabled, the ``cdcSnapshotSettings`` object must be configured with the ``snapshotType`` set to ``historical`` and must not have a source configured at the root level of the Data Flow Spec, the source is instead configured at the ``cdcSnapshotSettings`` level (refer to :ref:`dataflow_spec_ref_cdc` for more information).
   - This will process all the historical snapshots available at the time of the pipeline run and any new snapshots will be ingested with each pipeline update.

Configuration
-------------

Set as an attribute when creating your Data Flow Spec, refer to the :doc:`dataflow_spec_ref_cdc` section of the :doc:`dataflow_spec_reference` documentation for more information.
