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
       - The location to load the source data from. This can be a table name or a path to a file or directory with multiple snapshots. Supports three path pattern styles for version extraction: the ``{version}`` placeholder (simple single-segment match), the ``{fragment}`` placeholder (for multi-file snapshots), and regex named capture groups (for complex partitioning). See :ref:`file-path-patterns` for details and examples.
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
       - (*optional*) A filter expression to apply to the source data. This filter is applied to the dataframe as a WHERE clause when the source is read. The placeholder ``{version}`` can be used in this filter expression and will be substituted with the version value at run time (e.g. ``"year = '{version}'"``). Not applicable when using regex named capture groups in ``path``.
     * - **recursiveFileLookup**
       - ``boolean``
       - (*optional*) When set to ``true``, enables recursive directory traversal to find snapshot files. This should be used when snapshots are stored in a nested directory structure such as Hive-style partitioning (e.g., ``/data/{version}/file.parquet``). When set to ``false`` (default), only files in the immediate directory are searched. Default: ``false``.


  .. note::
    If ``recursiveFileLookup`` is set to ``true``, ensure that the ``path`` parameter is compatible with recursive directory traversal. When using the ``{version}`` placeholder, place it in the directory portion of the path rather than the filename (e.g. ``/data/{version}/file.parquet``). When using regex named capture groups, the pattern spans the full relative path from the first dynamic segment, so ``recursiveFileLookup`` must be ``true`` if the version spans multiple directory levels.

.. _file-path-patterns:

File Path Patterns
^^^^^^^^^^^^^^^^^^

  The ``path`` field supports three styles for expressing where the version (and optional fragment) appears in the file path. All styles can be combined with a static base path prefix that is resolved at run time (e.g. ``{sample_file_location}``).

  .. list-table::
     :header-rows: 1
     :widths: 20 35 45

     * - Style
       - Syntax
       - When to Use
     * - ``{version}`` placeholder
       - ``{version}``
       - Version is contained in a single path segment or filename component. Simple and readable for flat or single-level partitioned layouts.
     * - ``{fragment}`` placeholder
       - ``{fragment}``
       - Snapshot data for a single version is split across multiple files. Use alongside ``{version}`` to group files sharing the same version together.
     * - Regex named capture groups
       - ``(?P<version_<name>>.+)``
       - Version is spread across multiple path segments or interleaved with other text. Supports complex partitioning schemes (e.g. Hive-style ``YEAR=.../MONTH=.../DAY=...``) where the version cannot be expressed as a single placeholder.

  **``{version}`` — single-segment version**

  The ``{version}`` placeholder matches one path segment or filename component. It is internally converted to a regex named capture group ``(?P<version_main>.+)``.

  .. code-block:: json

     {
       "path": "/mnt/data/snapshots/customer_{version}.csv",
       "versionType": "timestamp",
       "datetimeFormat": "%Y_%m_%d"
     }

  Files matched: ``customer_2024_01_01.csv``, ``customer_2024_01_02.csv``, …

  For directory-partitioned layouts, place ``{version}`` in the directory portion and set ``recursiveFileLookup`` to ``true``:

  .. code-block:: json

     {
       "path": "/mnt/data/snapshots/{version}/customer.csv",
       "versionType": "timestamp",
       "datetimeFormat": "YEAR=%Y/MONTH=%m/DAY=%d",
       "recursiveFileLookup": true
     }

  Files matched: ``YEAR=2024/MONTH=01/DAY=01/customer.csv``, …

  **``{fragment}`` — multi-file snapshots**

  Use ``{fragment}`` alongside ``{version}`` when a single snapshot version is split across multiple files. All files sharing the same version are read and unioned together before CDC processing.

  .. code-block:: json

     {
       "path": "/mnt/data/snapshots/customer_{version}_split_{fragment}.csv",
       "versionType": "timestamp",
       "datetimeFormat": "%Y_%m_%d"
     }

  Files matched and grouped by version: ``customer_2024_01_01_split_1.csv``, ``customer_2024_01_01_split_2.csv`` → both ingested as version ``2024-01-01``.

  **Regex named capture groups — multi-segment versions**

  For cases where the version is distributed across multiple directory levels or interleaved with fixed text, use Python regex named capture groups with the prefix ``version_``. All groups whose names start with ``version_`` are extracted and concatenated **in the order they appear in the pattern** (left to right) to form the final version string, which is then parsed according to ``datetimeFormat`` or treated as an integer.

  Group naming convention: ``(?P<version_<name>>.+)``. The ``<name>`` suffix is arbitrary but must be unique within the pattern. The concatenation order is determined by the position of each group in the path expression, not the name.

  .. code-block:: json

     {
       "path": "/mnt/data/snapshots/(?P<version_year>.+)/(?P<version_month>.+)/data/customer_(?P<version_day>.+).csv",
       "versionType": "timestamp",
       "datetimeFormat": "%Y%m%d",
       "recursiveFileLookup": true
     }

  For the file ``2024/01/data/customer_15.csv``, the groups are captured left-to-right: ``version_year=2024``, ``version_month=01``, ``version_day=15``. These are concatenated in pattern order to produce ``"20240115"``, which is then parsed with ``datetimeFormat: "%Y%m%d"``.

  .. tip::

     Arrange your ``(?P<version_...>)`` groups in the path from left to right in the same order that their values should be concatenated to match your ``datetimeFormat``. The group names themselves only need to be unique — their order in the pattern controls concatenation.

  See ``samples/bronze_sample/src/dataflows/feature_samples/dataflowspec/historical_snapshot_files_datetime_recursive_and_partitioned_regex_main.json`` for a complete working example.

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
