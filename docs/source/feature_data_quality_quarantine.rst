Data Quality - Quarantine
============

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - NA

The Lakeflow Framework provides a quarantine feature that allows you to quarantine records that violate defined pipeline expectations. 

There are multiple ways to handle quarantined records and these can be configured using the ``quarantineMode`` property in the Data Flow Spec. Available options are:

- **off**: The quarantine feature is disabled
- **flag**: The quarantined records are flagged in the target table
- **table**: The quarantined records are stored in a separate quarantine table

If the `quarantineMode` property is set to `table`, the quarantineTargetDetails property can be set in the Data Flow Spec to define the details of the quarantine table, otherwise the quarantine table will be derived based of the main target table.


Configuration
-------------

Set as an attribute when creating your Data Flow Spec, refer to the :doc:`dataflow_spec_ref_data_quality` documentation for more information.