Soft Deletes
============

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta-live-tables/python-ref.html#change-data-capture-from-a-change-feed-with-python-in-delta-live-tables

The Lakeflow Framework provides support for soft deletes when processing change data capture (CDC) events using the ``apply_changes()`` function. This allows you to handle DELETE operations in your CDC data while maintaining a history of deleted records.

When soft deletes are configured, deleted rows are temporarily retained as tombstones in the underlying Delta table. A view is created in the metastore that filters out these tombstones, providing a "live" view of current records.

Configuration
-------------

Soft deletes are configured using the ``apply_as_deletes`` parameter in the ``apply_changes()`` function. This parameter specifies the condition that indicates when a CDC event should be treated as a DELETE rather than an upsert.

The condition can be specified either as:

- A string expression: ``"Operation = 'DELETE'"``
- A Spark SQL expression using ``expr()``: ``expr("Operation = 'DELETE'")``