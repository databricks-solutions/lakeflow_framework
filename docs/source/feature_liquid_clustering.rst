Liquid Clustering
================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - https://docs.databricks.com/en/delta/clustering.html
     
Liquid clustering is a Databricks feature that replaces traditional table partitioning and ``ZORDER`` to simplify data layout decisions and optimize query performance. It provides flexibility to redefine clustering keys without rewriting existing data, allowing data layout to evolve alongside analytic needs over time.

Use Cases
---------
    
Databricks recommends liquid clustering for all new Delta tables, which includes both Streaming Tables (STs) and Materialized Views (MVs). The following are examples of scenarios that benefit from clustering:

* Tables often filtered by high cardinality columns.
* Tables with significant skew in data distribution.
* Tables that grow quickly and require maintenance and tuning effort.
* Tables with concurrent write requirements.
* Tables with access patterns that change over time.
* Tables where a typical partition key could leave the table with too many or too few partitions.

Selecting Clustering Keys
-------------------------

If ``clusterByAuto`` is set to ``true``, the clustering keys will be automatically selected based on the data in the table. Otherwise, the clustering keys can be specified in the ``clusterByColumns`` attribute.
If both ``clusterByAuto`` and ``clusterByColumns`` are set, the columns specified in ``clusterByColumns`` will be used as the initial clustering keys and the keys will be automatically updated based on the data in the table over time.

Please refer to the `Liquid Clustering documentation <https://docs.databricks.com/en/delta/clustering.html#choose-clustering-keys>`_ for more information on selecting clustering keys.

Configuration
-------------  

Enabled by setting the ``clusterBy`` attribute as documented in :ref:`dataflow_spec_ref_target_details_delta`. 
Additionally or alternatively, the ``clusterByAuto`` attribute can be enabled to allow for automatic clustering key selection as documented in :ref:`dataflow_spec_ref_target_details_delta`.
