Data Flow Spec - Source Details
##############################

The `sourceDetails` object can be any of the following, based on the `sourceType`:

Batch Files
----------------

The `sourceBatchFiles` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto  

   * - **Property**
     - **Type**
     - **Description**
   * - **format**
     - ``string``
     - The format of the batch files. Supported: `["csv", "json", "parquet", "text", "xml"]`
   * - **path**
     - ``string``
     - The path to the batch files.
   * - **readerOptions**
     - ``object``
     - Options for reading the batch files. See `definitions_sources.json` schema for supported options.
   * - **selectExp** (*optional*)
     - ``array``
     - An array of select expressions. Items: ``string``
   * - **whereClause** (*optional*)
     - ``array``
     - An array of where clauses. Items: ``string``
   * - **schemaPath** (*optional*)
     - ``string``
     - The schema path.
   * - **pythonTransform** (*optional*)
     - ``string``
     - The Python transform configuration. See :ref:`pythonTransform-object` for supported options.

Cloud Files
----------------

The `sourceCloudFiles` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **path**
     - ``string``
     - The path to the cloud files.
   * - **readerOptions**
     - ``object``
     - Options for reading the cloud files. See `definitions_sources.json` schema for supported options.
   * - **selectExp** (*optional*)
     - ``array``
     - An array of select expressions. Items: ``string``
   * - **whereClause** (*optional*)
     - ``array``
     - An array of where clauses. Items: ``string``
   * - **schemaPath** (*optional*)
     - ``string``
     - The schema path.
   * - **pythonTransform** (*optional*)
     - ``string``
     - The Python transform configuration. See :ref:`pythonTransform-object` for supported options.

Delta
----------------

The `sourceDelta` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **database**
     - ``string``
     - The database name.
   * - **table**
     - ``string``
     - The table name.
   * - **cdfEnabled**
     - ``boolean``
     - Whether change data feed (CDF) is enabled.
   * - **tablePath** (*optional*)
     - ``string``
     - The table path.
   * - **selectExp** (*optional*)
     - ``array``
     - An array of select expressions. Items: ``string``
   * - **whereClause** (*optional*)
     - ``array``
     - An array of where clauses. Items: ``string``
   * - **schemaPath** (*optional*)
     - ``string``
     - The schema path.
   * - **readerOptions** (*optional*)
     - ``object``
     - Additional reader options. See `definitions_sources.json` schema for supported options.
   * - **pythonTransform** (*optional*)
     - ``string``
     - The Python transform configuration. See :ref:`pythonTransform-object` for supported options.
   * - **startingVersionFromDLTSetup** (*optional*)
     - ``boolean``
     - Whether to automatically set reader option 'startingVersion' to the last time the SDP Setup operation was run on the source table. This helps to ensure CDF is read from the last time source table was reset (full refresh).

Delta Join
----------------

The `sourceDeltaJoin` object contains the following properties:

**Sources:**

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **database**
     - ``string``
     - The database name.
   * - **table**
     - ``string``
     - The table name.
   * - **alias**
     - ``string``
     - The alias for the table.
   * - **joinMode**
     - ``string``
     - The join mode. Supported: `["stream", "static"]`, Default: `"stream"`
   * - **cdfEnabled**
     - ``boolean``
     - Whether change data feed (CDF) is enabled.
   * - **tablePath** (*optional*)
     - ``string``
     - The table path.
   * - **selectExp** (*optional*)
     - ``array``
     - An array of select expressions. Items: ``string``
   * - **whereClause** (*optional*)
     - ``array``
     - An array of where clauses. Items: ``string``
   * - **schemaPath** (*optional*)
     - ``string``
     - The schema path.
   * - **readerOptions** (*optional*)
     - ``object``
     - Additional reader options. See `definitions_sources.json` schema for supported options.
   * - **pythonTransform** (*optional*)
     - ``string``
     - The Python transform configuration. See :ref:`pythonTransform-object` for supported options.

**Joins:**

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **joinType**
     - ``string``
     - The join type. Supported: `["left", "inner"]`, Default: `"left"`
   * - **condition**
     - ``string``
     - The join condition.

**Additional Properties:**

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **selectExp** (*optional*)
     - ``array``
     - An array of select expressions. Items: ``string``
   * - **whereClause** (*optional*)
     - ``array``
     - An array of where clauses. Items: ``string``
   * - **pythonTransform** (*optional*)
     - ``string``
     - The Python transform configuration. See :ref:`pythonTransform-object` for supported options.

Kafka
----------------

The `sourceKafkaReader` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **readerOptions**
     - ``object``
     - Options for reading from Kafka. See `definitions_sources.json` schema for supported options.
   * - **selectExp** (*optional*)
     - ``array``
     - An array of select expressions. Items: ``string``
   * - **whereClause** (*optional*)
     - ``array``
     - An array of where clauses. Items: ``string``
   * - **schemaPath** (*optional*)
     - ``string``
     - The schema path.
   * - **pythonTransform** (*optional*)
     - ``string``
     - The Python transform configuration. See :ref:`pythonTransform-object` for supported options.

Kafka SQL
----------------

In progress

Python
----------------

The `sourcePython` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **functionPath** (*optional*)
     - ``string``
     - The path to the Python file, which should live in the `python_functions` subdirectory.
   * - **pythonModule** (*optional*)
     - ``string``
     - The module to import the Python function from.
   * - **tokens**
     - ``object``
     - A dictionary of tokens that will be passed to the Python function. This allows you to pass in substitution variables from the data flow spec.

.. important::

   - You must select one of `functionPath` or `pythonModule`.

SQL
----------------

The `sourceSql` object contains the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **sqlPath** (*optional*)
     - ``string``
     - The path to the SQL file, which should live in the `dml` subdirectory.
   * - **sqlStatement** (*optional*)
     - ``string``
     - The SQL statement to execute.

.. important::

   - While the `sqlPath` and `sqlStatement` properties are optional you must select one.
   - If both `sqlPath` and `sqlStatement` are provided, `sqlStatement` will take precedence.


.. _pythonTransform-object:

Python Transform Object
-----------------------

The `pythonTransform` object can be used to specify a Python transform function to be applied to the dataframe post read. It can contain the following properties:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Property**
     - **Type**
     - **Description**
   * - **functionPath** (*optional*)
     - ``string``
     - The path to the Python file, which should live in the `python_functions` subdirectory.
   * - **module** (*optional*)
     - ``string``
     - The module to import the Python function from.
   * - **tokens** (*optional*)
     - ``object``
     - A dictionary of tokens that will be passed to the Python function. This allows you to pass in substitution variables from the data flow spec.

.. important::

   - You must select one of `functionPath` or `module`.
