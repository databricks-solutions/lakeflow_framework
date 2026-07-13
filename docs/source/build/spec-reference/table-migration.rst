Table Migration Configuration
-----------------------------

These properties control table migration:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **tableMigrationDetails** (*optional*)
     - ``object``
     - Details about table migration, only required if a table migration is needed.  
       See :ref:`Table Migration Details<table-migration-details>` section below.

.. _table-migration-details:

tableMigrationDetails
~~~~~~~~~~~~~~~~~~~~~

The `tableMigrationDetails` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **enabled**
     - ``boolean``
     - A flag indicating whether table migration is enabled.
   * - **catalogType**
     - ``string``
     - The type of catalog, either `hms` or `uc`.  
       Supported values: `["hms", "uc"]`
   * - **autoStartingVersionsEnabled** (*optional*)
     - ``boolean``
     - Flag to enable automatic starting version management. When enabled, the system automatically tracks source table versions and manages starting versions for views. Defaults to ``true``.
   * - **sourceDetails**
     - ``object``
     - Details about the source for migration.  
       See :ref:`source-migrate-delta`.

.. _source-migrate-delta:

sourceDetails
^^^^^^^^^^^^^

The `sourceDetails` object can potentially cater to different types of sources but is currently limited to the following:

* `sourceMigrateDelta`

**sourceMigrateDelta**

The ``sourceMigrateDelta`` object contains the following properties:

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - **database**
     - ``string``
     - The database name.
   * - **table**
     - ``string``
     - The table name.
   * - **selectExp** (*optional*)
     - ``array`` (items: ``string``)
     - An array of select expressions.
   * - **whereClause** (*optional*)
     - ``array`` (items: ``string``)
     - An array of where clauses.
   * - **exceptColumns** (*optional*)
     - ``array`` (items: ``string``)
     - An array of columns to exclude.
