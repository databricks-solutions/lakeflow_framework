Change Data Capture (CDC) Configuration
----------------------------------------

The ``cdcSettings`` and ``cdcSnapshotSettings`` enable and pass configuration info to the CDC API's.

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **cdcSettings**
     - ``object``
     - See :ref:`cdcSettings` for more information.
   * - **cdcSnapshotSettings**
     - ``object``
     - See :ref:`cdcSnapshotSettings` for more information.

cdcSettings
~~~~~~~~~~~~~~~~~   

The ``cdcSettings`` object contains the following properties:

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - **keys**
     - ``list``
     - The column or combination of columns that uniquely identify a row in the source data. This is used to identify which CDC events apply to specific records in the target table.
   * - **sequence_by**
     - str
     - The column name specifying the logical order of CDC events in the source data. Delta Live Tables uses this sequencing to handle change events that arrive out of order.
   * - **scd_type**
     - ``string``
     - Whether to store records as SCD type 1 or SCD type 2. Set to ``1`` for SCD type 1 or 2 for SCD type ``2``.   
   * - **apply_as_deletes**
     - ``string``
     - (*optional*) Specifies when a CDC event should be treated as a DELETE rather than an upsert.
   * - **where**
     - ``string``
     - (*optional*) Filter the rows by a condition.
   * - **ignore_null_updates**
     - ``boolean``
     - (*optional*) Allow ingesting updates containing a subset of the target columns. When a CDC event matches an existing row and ignore_null_updates is True, columns with a null retain their existing values in the target. This also applies to nested columns with a value of null. When ignore_null_updates is False, existing values are overwritten with null values.
   * - **except_column_list**
     - ``list``
     - (*optional*) A list of columns to exclude from the upsert into the target table.
   * - | **track_history_column_list**
       | **track_history_except_column_list**
     - ``list``
     - A subset of output columns to be tracked for history in the target table. Use track_history_column_list to specify the complete list of columns to be tracked. Use track_history_except_column_list to specify the columns to be excluded from tracking.


cdcSnapshotSettings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``cdcSnapshotSettings`` object contains the following properties:

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - **keys**
     - ``list``
     - The column or combination of columns that uniquely identify a row in the source data. This is used to identify which CDC events apply to specific records in the target table.
   * - **snapshotType**
     - str
     - The type of snapshot to process. Set to ``periodic`` for periodic snapshots or ``historical`` for historical snapshots (refer to :ref:`CDC Historical Snapshot Source Configuration` for which type to use). Note that ``historical`` snapshot types are not supported in ``flow`` data flow types.
   * - **scd_type**
     - ``string``
     - Whether to store records as SCD type 1 or SCD type 2. Set to ``1`` for SCD type 1 or 2 for SCD type ``2``.
   * - **sourceType**
     - ``string``
     - The type of source to ingest the snapshots from. Set to ``file`` for file based sources.
   * - **source**
     - ``object``
     - The source to ingest the snapshots from. This is required for ``historical`` snapshot types. See :ref:`cdc-apply-changes-from-snapshot-source` for more information.
   * - **track_history_column_list**
     - ``list``
     - (*optional*) A subset of output columns to be tracked for history in the target table. Use this to specify the complete list of columns to be tracked. This cannot be used in conjunction with ``track_history_except_column_list``.
   * - **track_history_except_column_list**
     - ``list``
     - (*optional*) A subset of output columns to be excluded from history tracking in the target table. Use this to specify which columns should not be tracked. This cannot be used in conjunction with ``track_history_column_list``.
   * - **deduplicateMode**
     - ``string``
     - (*optional*) How to deduplicate source snapshot data before CDC. Default: ``off`` (no deduplication). Use ``full_row`` to deduplicate based on the full row (deterministic) excluding the ``_metadata`` column if present. Use ``keys_only`` to keep the first row per key(s): This is non-deterministic; as it preserves the first row per key(s) without ordering on any other columns.

  .. warning::
     The ``keys_only`` option is **non-deterministic**. It preserves the first row per key(s). Use it with caution and only when you accept that which duplicate row is kept may vary between runs.

.. _cdc-apply-changes-from-snapshot-source:

CDC Historical Snapshot Source Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  The ``source`` object contains the following properties for ``file`` based sources:

  .. list-table::
     :header-rows: 1

     * - Parameter
       - Type
       - Description
     * - **format**
       - ``string``
       - The format of the source data. E.g. supported formats are ``table``, ``parquet``, ``csv``, ``json``. All formats supported by spark see `PySpark Data Sources API <https://spark.apache.org/docs/3.5.3/sql-data-sources.html>`_.
     * - **path**
       - ``string``
       - The location to load the source data from. This can be a table name or a path to a a file or directory with multiple snapshots. A placeholder ``{version}`` can be used in this path which will be substituted with the version value in run time.
     * - **versionType**
       - ``string``
       - The type of versioning to use. Can be either ``int`` or ``datetime``.
     * - **datetimeFormat**
       - ``string``
       - (*conditional*) Required if ``versionType`` is ``datetime``. The format of ``startingVersion`` datetime value.
     * - **microSecondMaskLength**
       - ``integer``
       - (*optional*) WARNING: Edge Cases Only!
         - Specify this if your ``versionType`` is ``datetime`` and your filename includes microsends, but not the full 6 digits. The number of microsecond digits to included at the end of the datetime value.
         - The default value is 6.
     * - **startingVersion**
       - ``string`` or ``integer``
       - (*optional*) The version to start processing from.
     * - **readerOptions**
       - ``object``
       - (*optional*) Additional options to pass to the reader.
     * - **schemaPath**
       - ``string``
       - (*optional*) The schema path to use for the source data.
     * - **selectExp**
       - ``list``
       - (*optional*) A list of select expressions to apply to the source data.
     * - **filter**
       - ``string``
       - (*optional*) A filter expression to apply to the source data. This filter is applied to the dataframe as a WHERE clause when the source is read. A placeholder ``{version}`` can be used in this filter expression which will be substituted with the version value in run time.
     * - **recursiveFileLookup**
       - ``boolean``
       - (*optional*) When set to ``true``, enables recursive directory traversal to find snapshot files. This should be used when snapshots are stored in a nested directory structure such as Hive-style partitioning (e.g., ``/data/{version}/file.parquet``). When set to ``false`` (default), only files in the immediate directory are searched. Default: ``false``.


  .. note::
    If ``recursiveFileLookup`` is set to ``true``, ensure that the ``path`` parameter is specified in a way that is compatible with recursive directory traversal. I.e. the ``{version}`` placeholder is used in the path and not the filename.

  The ``source`` object contains the following properties for ``table`` based sources:

  .. list-table::
     :header-rows: 1

     * - Parameter
       - Type
       - Description
     * - **table**
       - ``string``
       - The table name to load the source data from.
     * - **versionColumn**
       - ``string``
       - The column name to use for versioning.
     * - **startingVersion**
       - ``string`` or ``integer``
       - (*optional*) The version to start processing from.
     * - **selectExp**
       - ``list``
       - (*optional*) A list of select expressions to apply to the source data.
