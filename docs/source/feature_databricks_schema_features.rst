Schema-related Databricks Features
==================================

.. list-table::
   :header-rows: 0

   * - **Applies To:**
     - :bdg-success:`Pipeline Bundle`
   * - **Configuration Scope:**
     - :bdg-success:`Data Flow Spec`
   * - **Databricks Docs:**
     - - `Constraints <https://docs.databricks.com/aws/en/tables/constraints>`_
       - `Generated columns <https://docs.databricks.com/aws/en/delta/generated-columns>`_
       - `Column masks <https://docs.databricks.com/aws/en/dlt/unity-catalog#row-filters-and-column-masks>`_
       - `Databricks SQL data types <https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html>`_

Overview
--------

Databricks supports schema-level table capabilities such as constraints,
generated columns, column masks, and SQL data types. Lakeflow Framework does
not redefine these product features; it provides a way to include them in the
schema files that are referenced by the data flow spec.

How LFF exposes it
------------------

Use a text DDL schema file for staging or target tables when you need
Databricks SQL schema features that cannot be represented in JSON StructType
format. Reference that schema file from the relevant source, staging, target, or
materialized view configuration in the data flow spec.

For file layout, supported schema formats, ``schemaPath`` usage, and examples,
see :doc:`feature_schemas`.
