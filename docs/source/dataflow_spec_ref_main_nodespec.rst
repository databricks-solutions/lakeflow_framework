Creating a Nodespec Data Flow Spec Reference
############################################

The **Nodespec** Data Flow Spec describes a pipeline as a graph of nodes that
chain together:

.. code-block:: text

   source  ->  transformation  ->  target

Instead of the target-table-driven layout of the standard and flow specs, a
Nodespec spec is a flat list of nodes that reads top-to-bottom in the order the
data flows. The framework converts a Nodespec spec into its internal flow-based
format at build time, so every existing capability (CDC, data quality,
quarantine, snapshots, table migration, sinks, materialized views) is available.

Key concepts
============

There are three node types:

- **source** — where data comes from (Delta table, cloud files, Kafka, a SQL
  query, or a Python function).
- **transformation** — how data is reshaped (SQL or Python).
- **target** — where data lands. A target carries its own table-level settings
  (CDC, data quality, quarantine, clustering, and so on).

**How nodes connect.** A *target* node declares what feeds it through an explicit
``input_flows`` list. *Source* and *transformation* nodes are wired by explicit
reference inside their own definition: a SQL transformation names the view it
reads in its SQL (for example ``FROM STREAM(live.v_source_customer)``), and a
source names the table, path, or stream it reads. The ``input_flows`` list is
therefore a target-node construct.

**Casing.** Nodespec specs use ``snake_case`` field names.

**Field order.** Within a node's ``config``, fields are written in a consistent
order — identity (``table``/``database``), then table/structural details, then
feature blocks (``cdc_settings``, ``data_quality``, ``quarantine``,
``table_migration_details``), and finally ``input_flows``. The order is
conventional only; it does not affect behaviour.

Example: simple data flow
=========================

The simplest spec connects a source to a target:

.. code-block:: json

   {
       "data_flow_id": "nodespec_customer_simple",
       "data_flow_group": "nodespec_base_samples",
       "data_flow_type": "nodespec",
       "nodes": [
           {
               "name": "v_source_customer",
               "node_type": "source",
               "source_type": "delta",
               "config": {
                   "database": "{bronze_schema}",
                   "table": "customer",
                   "cdf_enabled": true,
                   "mode": "stream"
               }
           },
           {
               "name": "target_customer",
               "node_type": "target",
               "config": {
                   "table": "customer_silver",
                   "cluster_by_auto": true,
                   "input_flows": [
                       { "view": "v_source_customer", "flow": "f_customer_ingest" }
                   ]
               }
           }
       ]
   }

``data_flow_type`` is optional — nodespec is the framework's default spec type, so
a spec that omits it is treated as nodespec. Include ``"data_flow_type":
"nodespec"`` only if you want to be explicit.

Example: multi-step transformation and CDC
==========================================

Chaining a transformation into a CDC target. The SQL transformation names the
view it reads; the target lists the transformation in its ``input_flows``:

.. code-block:: json

   {
       "data_flow_id": "nodespec_customer_enriched",
       "data_flow_group": "nodespec_base_samples",
       "data_flow_type": "nodespec",
       "nodes": [
           {
               "name": "v_source_customer",
               "node_type": "source",
               "source_type": "delta",
               "config": { "database": "{bronze_schema}", "table": "customer", "cdf_enabled": true, "mode": "stream" }
           },
           {
               "name": "v_enrich",
               "node_type": "transformation",
               "transformation_type": "sql",
               "config": {
                   "sql_statement": "SELECT CUSTOMER_ID, EMAIL, CITY, LOAD_TIMESTAMP FROM STREAM(live.v_source_customer)"
               }
           },
           {
               "name": "target_customer_enriched",
               "node_type": "target",
               "config": {
                   "table": "customer_enriched",
                   "schema_path": "customer_enriched_schema.json",
                   "cdc_settings": {
                       "keys": ["CUSTOMER_ID"],
                       "sequence_by": "LOAD_TIMESTAMP",
                       "scd_type": "2",
                       "ignore_null_updates": true
                   },
                   "input_flows": ["v_enrich"]
               }
           }
       ]
   }

Editor autocomplete and validation
==================================

Nodespec specs have a JSON Schema (``src/schemas/spec_nodespec.json``), so editors
can offer key/value autocomplete and inline validation while you author them. The
schema is wired through ``main.json``, which routes any ``*_main.json`` file to
the correct spec schema based on its ``data_flow_type``. Add the ``json.schemas``
mapping described in :doc:`feature_auto_complete` — the same ``*_main.json``
mapping enables IntelliSense for nodespec (no nodespec-specific configuration is
required).

.. _dataflow-spec-nodespec-metadata-configuration:

Dataflow metadata configuration
===============================

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **data_flow_id**
     - ``string``
     - A unique identifier for the data flow.
   * - **data_flow_group**
     - ``string``
     - The group to which the data flow belongs.
   * - **data_flow_type** (*optional*)
     - ``string``
     - ``"nodespec"``. Optional — nodespec is the default spec type, so a spec
       that omits ``data_flow_type`` is treated as nodespec. When present it must
       be ``"nodespec"``.
   * - **data_flow_version** (*optional*)
     - ``string``
     - Version of the dataflow spec for migration purposes.
   * - **tags** (*optional*)
     - ``object``
     - Custom tags for the dataflow.
   * - **features** (*optional*)
     - ``object``
     - Feature flags (e.g., ``operationalMetadataEnabled``).

.. _dataflow-spec-nodespec-nodes:

Node configuration
==================

Each entry of the ``nodes`` array has:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **name**
     - ``string``
     - Unique name for the node within the spec. Source and transformation node
       names double as their view names (prefixed with ``v_`` if not already).
   * - **node_type**
     - ``string``
     - One of ``source``, ``transformation``, ``target``.
   * - **source_type**
     - ``string``
     - Required for source nodes (see below).
   * - **transformation_type**
     - ``string``
     - Required for transformation nodes (see below).
   * - **target_type** (*optional*)
     - ``string``
     - For target nodes: ``delta`` (default), ``delta_sink``,
       ``foreach_batch_sink``, or ``custom_python_sink``.
   * - **output_view_name** (*optional*)
     - ``string``
     - Override the generated view name for a source/transformation node.
   * - **enabled** (*optional*)
     - ``boolean``
     - Whether the node is enabled. Default: ``true``.
   * - **config**
     - ``object``
     - Node-specific configuration (see below).

.. note::
   There is no primary/secondary target flag. The framework auto-selects the
   spec target (the backend's ``targetDetails``) as the terminal target — the
   one not consumed by any other node. Any other targets become staging tables.

.. _dataflow-spec-nodespec-source-nodes:

Source node configuration
=========================

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **source_type**
     - ``string``
     - ``delta``, ``cloud_files``, ``batch_files``, ``delta_join``, ``kafka``, ``sql``, ``python``.
   * - **mode** (*optional*)
     - ``string``
     - ``stream`` or ``batch``. Default: ``stream``.
   * - **database** / **table**
     - ``string``
     - For ``delta`` sources.
   * - **path**
     - ``string``
     - For ``cloud_files`` / ``batch_files`` sources.
   * - **cdf_enabled** (*optional*)
     - ``boolean``
     - Enable Change Data Feed for Delta sources.
   * - **reader_options** (*optional*)
     - ``object``
     - Reader options (cloud files, Kafka).
   * - **schema_path** (*optional*)
     - ``string``
     - Path to a schema definition file.
   * - **select_exp** / **where_clause** (*optional*)
     - ``array``
     - Select expressions / WHERE clauses applied on read.
   * - **python_transform** (*optional*)
     - ``object``
     - Apply a Python ``apply_transform(df)`` to the source on read. Supported
       for backward compatibility; prefer a dedicated transformation node.

.. note::
   ``source_type: "sql"`` and ``source_type: "python"`` embed transformation
   logic directly in a source definition. They remain supported but are
   **discouraged** and emit a warning at build time. Model the logic as a
   dedicated transformation node instead.

.. _dataflow-spec-nodespec-transformation-nodes:

Transformation node configuration
=================================

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **transformation_type**
     - ``string``
     - ``sql`` or ``python``.
   * - **sql_path** / **sql_statement**
     - ``string``
     - For ``sql`` transforms. The SQL names the view(s) it reads, e.g.
       ``FROM STREAM(live.v_source_customer)``.
   * - **function_path** / **python_module**
     - ``string``
     - For ``python`` transforms. The referenced file/module must contain an
       ``apply_transform(df)`` (or ``apply_transform(df, tokens)``) function.
   * - **tokens** (*optional*)
     - ``object``
     - Tokens passed to a Python transform.

.. note::
   A ``python`` transformation node becomes its own view that reads its upstream
   view and applies ``apply_transform``. The upstream is inferred from the graph,
   so no explicit reference is required.

.. _dataflow-spec-nodespec-target-nodes:

Target node configuration
=========================

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **Type**
     - **Description**
   * - **table**
     - ``string``
     - Target table name.
   * - **database** (*optional*)
     - ``string``
     - Target database/schema.
   * - **table_type** (*optional*)
     - ``string``
     - ``st`` (streaming table, default) or ``mv`` (materialized view).
   * - **schema_path** (*optional*)
     - ``string``
     - Schema definition file (``.json`` or ``.ddl``).
   * - **table_properties** (*optional*)
     - ``object``
     - Delta table properties.
   * - **partition_columns** / **cluster_by_columns** / **cluster_by_auto** (*optional*)
     - ``array`` / ``array`` / ``boolean``
     - Partitioning and liquid clustering. ``partition_columns`` and
       ``cluster_by_columns`` are mutually exclusive.
   * - **comment** / **spark_conf** / **row_filter** / **config_flags** (*optional*)
     - ``string`` / ``object`` / ``string`` / ``array``
     - Additional table settings.
   * - **once** (*optional*)
     - ``boolean``
     - Execute the flow to this target only once (batch).
   * - **cdc_settings** / **cdc_snapshot_settings** (*optional*)
     - ``object``
     - CDC / snapshot-CDC settings for this target.
   * - **data_quality** (*optional*)
     - ``object``
     - Data quality expectations: ``{ "expectations_path": <path> }``. Presence
       enables expectations (there is no separate enabled flag).
   * - **quarantine** (*optional*)
     - ``object``
     - Quarantine for rows failing expectations: ``{ "mode": "flag" | "table",
       "target": { ... } }``. Omit for no quarantine; ``target`` is the quarantine
       table config, required when ``mode`` is ``table``.
   * - **table_migration_details** (*optional*)
     - ``object``
     - Table migration configuration.
   * - **input_flows**
     - ``array``
     - What feeds this target. Each item is either an upstream node name
       (``string``, flow name auto-generated) or an object
       ``{ "view": <node name>, "flow": <flow name> }`` that sets the flow name.
       Conventionally written last in the config.

.. note::
   Which fields are valid depends on ``table_type``. Streaming-table settings
   (``cdc_settings``, ``cdc_snapshot_settings``, ``table_migration_details``,
   ``once``) are only allowed on streaming tables (``table_type`` ``st`` or
   omitted); materialized-view settings (``sql_path``, ``sql_statement``,
   ``refresh_policy``, ``table_details``) are only allowed on materialized views
   (``table_type: "mv"``). The schema enforces this, so an editor flags, e.g.,
   ``sql_path`` on a streaming table or ``cdc_settings`` on a materialized view.

Sink targets
-----------

When ``target_type`` is a sink (``delta_sink``, ``kafka_sink``,
``foreach_batch_sink``, ``custom_python_sink``) the target config uses the sink
fields instead of the delta-table fields: ``name``, ``sink_type`` (sink sub-type,
e.g. ``basic_sql`` / ``python_function`` for ``foreach_batch_sink``),
``sink_config`` (sink-specific configuration), and ``sink_options`` (e.g.
``table_name``/``path`` for a delta sink, or Kafka connection options), plus
``input_flows``.

Defining flow names
-------------------

By default the framework derives a flow name from the graph, so simple specs stay
simple. Use the object form of ``input_flows`` to set a flow name explicitly:

.. code-block:: json

   "input_flows": [
       "v_source_a",
       { "view": "v_source_b", "flow": "f_append_b" }
   ]

Defining the flow name keeps it stable across edits. This matters because
renaming a flow forces a full refresh in SDP, so a defined name avoids triggering
one. The string and object forms can be mixed in the same list.

Snapshot CDC targets
-------------------

A target's ``cdc_snapshot_settings`` configures snapshot-based CDC. There are two
modes, set via ``snapshot_type``:

- **historical** — the snapshot source is built **inside** the settings via
  ``source_type`` (``file`` or ``table``) and a ``source`` object. No source node
  is required; the framework reads the files/table directly.
- **periodic** — the target reads from an upstream **source node** chained via
  ``input_flows``; ``source_type`` / ``source`` are not used.

For historical snapshots the ``source`` object fields depend on ``source_type``:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Field**
     - **source_type**
     - **Description**
   * - **path**
     - ``file``
     - Snapshot file path/pattern; may contain a ``{version}`` token.
   * - **format**
     - ``file``
     - File format, e.g. ``csv``, ``parquet``, ``json``.
   * - **reader_options**
     - ``file``
     - Options passed to the file reader, e.g. ``{"header": "true"}``.
   * - **datetime_format**
     - ``file``
     - Format used to parse the ``{version}`` token for timestamp versioning.
   * - **schema_path**
     - ``file``
     - Schema file applied when reading the snapshot files.
   * - **recursiveFileLookup**
     - ``file``
     - Recurse into subdirectories when discovering snapshot files.
   * - **table**
     - ``table``
     - Source table, e.g. ``{schema}.snapshot_source``.
   * - **version_column**
     - ``table``
     - Column carrying the snapshot version.
   * - **version_type**
     - both
     - How versions are interpreted, e.g. ``timestamp`` or ``integer``.
   * - **select_exp**
     - both
     - Select expressions applied to the snapshot source.

Example — historical file snapshot:

.. code-block:: json

   {
       "name": "target_customer_snapshot",
       "node_type": "target",
       "config": {
           "table": "customer_snapshot",
           "cdc_snapshot_settings": {
               "keys": ["CUSTOMER_ID"],
               "scd_type": "2",
               "snapshot_type": "historical",
               "source_type": "file",
               "source": {
                   "format": "csv",
                   "path": "{sample_file_location}/snapshot_customer/customer_{version}.csv",
                   "reader_options": { "header": "true" },
                   "version_type": "timestamp",
                   "datetime_format": "%Y_%m_%d"
               }
           }
       }
   }

.. _dataflow-spec-nodespec-mv:

Materialized view targets
=========================

A materialized view is a target node with ``table_type: "mv"``. It can be defined
by inline SQL or by chaining a source node into it:

.. code-block:: json

   {
       "name": "target_customer_summary",
       "node_type": "target",
       "config": {
           "table": "customer_summary",
           "table_type": "mv",
           "sql_statement": "SELECT STATE, count(*) AS n FROM live.customer_silver GROUP BY STATE"
       }
   }

To feed a materialized view from a source node, chain it via ``input_flows`` (an
inline ``source_view`` on the target is **not** supported):

.. code-block:: json

   {
       "name": "v_mv_source",
       "node_type": "source",
       "source_type": "delta",
       "config": { "database": "{staging_schema}", "table": "customer", "mode": "batch" }
   },
   {
       "name": "target_customer_mv",
       "node_type": "target",
       "config": {
           "table": "customer_mv",
           "table_type": "mv",
           "input_flows": ["v_mv_source"]
       }
   }

A single spec may contain both streaming-table and materialized-view targets,
including chains where one feeds the other, so a pipeline that mixes the two does
not have to be split across separate specs.

.. _dataflow-spec-nodespec-conversion:

How Nodespec specs are converted
================================

1. The terminal target (not consumed by any other node) becomes ``targetDetails``;
   its CDC, data quality, and quarantine settings move to the spec level.
2. Other targets become ``stagingTables``, each with their own settings.
3. Source nodes become views; an internal source (one that reads a table produced
   by a target in the same spec) references that table directly.
4. Transformation nodes become SQL or Python views.
5. Each ``input_flows`` entry becomes a flow into its target. The flow type is
   ``merge`` when the target has CDC, otherwise ``append_view`` (or ``append_sql``
   for an inline SQL source).
6. Each ``table_type: "mv"`` target becomes its own materialized-view flow spec.

Comparison with other spec types
================================

.. list-table::
   :header-rows: 1
   :widths: auto

   * - **Aspect**
     - **Standard**
     - **Flow**
     - **Nodespec**
   * - **Paradigm**
     - Single source → target
     - Target-table-driven with flow groups
     - Node graph
   * - **Multiple sources**
     - No
     - Yes (via views)
     - Yes (via source nodes)
   * - **Intermediate tables**
     - No
     - Yes (staging tables)
     - Yes (non-terminal targets)
   * - **Streaming tables + materialized views in one spec**
     - No
     - No
     - Yes
