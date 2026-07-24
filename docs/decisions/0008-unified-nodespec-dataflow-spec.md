# ADR-0008: A unified, node-based dataflow spec (`nodespec`)

**Date:** 2026-06-19
**Status:** Accepted (amended)

---

## Amendment — post-acceptance refinements

The decision below stands. Since acceptance, the authoring syntax has been
refined; the examples in this ADR use the **original** field names. The current
names (authoritative reference: ``docs/source/dataflow_spec_ref_main_nodespec.rst``)
differ as follows:

- **`input` → `input_flows`** — the target-node wiring list was renamed for clarity.
- **Data quality → nested `data_quality`** object (`{ "expectations_path": ... }`),
  replacing the `data_quality_expectations_enabled` / `_path` pair; presence implies
  enabled.
- **Quarantine → nested `quarantine`** object (`{ "mode", "target" }`), replacing
  `quarantine_mode` / `quarantine_target_details`.
- **`data_flow_type` is optional** — nodespec is the framework default, so a spec
  that omits it is treated as nodespec.
- **`scd_type` is a string** in `cdc_settings` (e.g. `"2"`).
- **Sink targets keep flat fields** (`sink_type` / `sink_config` / `sink_options`);
  a nested `sink` object was considered but deferred.
- **A node's `config` is schema-discriminated** by `node_type` +
  `source_type`/`target_type`, so editors offer only the fields valid for that node.

---

## Context

The framework historically shipped several distinct dataflow spec formats, and
each one has its own shape and its own rules:

- **Standard**: a single source flattened onto a single target, with CDC, data
  quality, quarantine, and table settings spread across the top level of the spec.
- **Flow**: a hand-authored flow graph with views, staging tables, and flow
  groups, where the author must already understand the framework's internal
  flow-spec representation.
- **Materialized view**: a separate `materializedViews` map with its own nested
  `sourceView` and `tableDetails` structure.

This creates real friction:

1. **Three formats to learn instead of one.** A new user has to first work out
   which spec type applies to their case, and then learn a different field layout
   for each. Knowledge gained writing a standard spec does not transfer to a flow
   or materialized view spec.

2. **The structure leaks framework internals.** The flow format in particular
   asks authors to think in terms of flow groups, view registration, and staging
   tables. Those are concepts that exist to serve the engine, not the person
   describing a pipeline. To write a correct spec you must understand how the
   framework assembles a pipeline, not just what you want the pipeline to do.

3. **Deep nesting is hard to write and hard to read.** Settings live at different
   depths depending on the format and the feature. Answering a simple question,
   such as "what feeds this table, and what happens to the data on the way in?",
   can mean tracing keys across several levels of nested objects. The nesting
   obscures the one thing a reader actually cares about, which is the shape of the
   pipeline.

4. **Topology is implicit.** In the older formats the connections between steps
   are inferred (from SQL, from key names, from position) rather than stated. The
   graph a pipeline actually forms is not something you can see by reading the
   spec.

5. **Streaming tables and materialized views must live in separate specs.**
   Because each output type has its own format, a pipeline that mixes streaming
   tables and materialized views has to be split across multiple specs. When those
   tables feed each other, for example a streaming table chained into a
   materialized view, the split is artificial and inconvenient: one logical
   pipeline ends up fragmented across files for no reason other than the spec
   format.

The cost of this is paid most by the two groups this framework exists to help.
The first is newcomers writing their first pipeline, who should not have to learn
the engine's internals to get started. The second is large organizations that
want to standardize and to easily read, understand, and edit each other's
pipelines across many people. Making both of those easier is the point of the
framework, and the current formats work against it.

## Decision

Introduce a single, unified dataflow spec, called **`nodespec`**, and make it the
way pipelines are described going forward.

A `nodespec` spec is a **graph of nodes**. There are exactly three node types, and
they compose by **chaining**:

```
source  ->  transformation  ->  target
(where data    (how data is        (where data
 comes from)    transformed)        lands)
```

- A **source** node says where data comes from (a table, files, a stream).
- A **transformation** node says how data is reshaped (SQL or Python).
- A **target** node says where data lands, and carries its own table-level
  settings (CDC, data quality, quarantine, clustering, and so on).

Nodes are wired together in two complementary ways. A **target** node declares
what feeds it through an explicit `input` list. **Source** and **transformation**
nodes are connected by explicit reference inside their own definition: a
transformation names its upstream view directly in its SQL or Python (for example
`FROM STREAM(live.v_source_customer)`), and a source names the table, path, or
stream it reads. The `input` list is therefore a target-node construct, while the
intermediate source-to-transformation wiring lives where the logic that uses it
lives. That uniform model replaces all three legacy formats. Every pipeline,
whether a one-hop ingest, a CDC merge, a multi-step transform, or a materialized
view, is expressed the same way: declare nodes, then chain them together.

Because output type is just a property of a target node, a single `nodespec` spec
can declare both streaming-table and materialized-view targets at once, including
chains where one feeds the other. A logical pipeline that mixes the two no longer
has to be split across separate specs by output type.

### The `input` list

`input` belongs to target nodes and lists what feeds the target. Each item is
either a plain string (the upstream node name, with the flow name auto-generated)
or an object that defines the flow name:

```json
"input": [
  "v_source_customer",
  { "view": "v_source_address", "flow": "f_append_address" }
]
```

The two forms can be mixed in the same list. By default the framework derives the
flow name from the graph, so simple specs stay simple; the object form defines it
when stability matters. This matters because renaming a flow forces a full refresh
in SDP, so defining the flow name lets authors keep it stable across edits and
migrations without triggering one. Source and transformation nodes do not carry an
`input` list; they reference their upstream within their own definition as
described above.

### Why a node graph

The node-and-edge model is the mental model most people already have for data
pipelines. It is how ETL is drawn on a whiteboard, how lineage is shown, and how
virtually every visual pipeline tool represents work. By matching that model
directly, the spec stops being something you have to learn the internals of and
becomes something you can read at a glance. Newcomers can be productive without
first absorbing the framework's flow-spec representation, and teams can read each
other's pipelines without reverse-engineering the structure first.

### Before and after

Consider a real pattern: two streaming sources are appended into one staging
table, and that staging table is then merged into a silver table with SCD2
history. In the flow format the author hand-builds the flow groups, registers
each view, declares the staging table, and wires the flows. The pipeline's shape
is buried several levels deep:

```json
{
  "dataFlowId": "multi_source_streaming_decomp_staging",
  "dataFlowGroup": "multi_source_streaming_decomposed_staging",
  "dataFlowType": "flow",
  "targetFormat": "delta",
  "targetDetails": {
    "database": "{silver_schema}",
    "table": "customer_ms_decomp_merge",
    "schemaPath": "customer.json",
    "tableProperties": { "delta.enableChangeDataFeed": "true" }
  },
  "cdcSettings": {
    "keys": ["CUSTOMER_ID"],
    "scd_type": "2",
    "sequence_by": "LOAD_TIMESTAMP",
    "except_column_list": ["LOAD_TIMESTAMP"],
    "ignore_null_updates": true
  },
  "flowGroups": [
    {
      "flowGroupId": "multi_source_streaming_decomp_staging_1",
      "stagingTables": { "customer_ms_decomp_appnd": { "type": "ST" } },
      "flows": {
        "f_customer": {
          "flowType": "append_view",
          "flowDetails": {
            "targetTable": "customer_ms_decomp_appnd",
            "sourceView": "v_customer"
          },
          "views": {
            "v_customer": {
              "mode": "stream",
              "sourceType": "delta",
              "sourceDetails": {
                "database": "{bronze_schema}",
                "table": "base_customer_append",
                "cdfEnabled": true
              }
            }
          }
        },
        "f_customer_address": {
          "flowType": "append_view",
          "flowDetails": {
            "targetTable": "customer_ms_decomp_appnd",
            "sourceView": "v_customer_address"
          },
          "views": {
            "v_customer_address": {
              "mode": "stream",
              "sourceType": "delta",
              "sourceDetails": {
                "database": "{bronze_schema}",
                "table": "base_customer_address_append",
                "cdfEnabled": true,
                "whereClause": ["STATE is not NULL"]
              }
            }
          }
        },
        "f_merge": {
          "flowType": "merge",
          "flowDetails": {
            "targetTable": "{silver_schema}.customer_ms_decomp_merge",
            "sourceView": "customer_ms_decomp_appnd"
          }
        }
      }
    }
  ]
}
```

The same pipeline as a `nodespec` graph is a flat list of nodes that reads
top-to-bottom in the order the data flows. Each concern sits on the node it
belongs to, and the connections are stated rather than inferred:

```json
{
  "data_flow_id": "multi_source_streaming_decomp_staging",
  "data_flow_group": "multi_source_streaming_decomposed_staging",
  "data_flow_type": "nodespec",
  "nodes": [
    {
      "name": "v_customer",
      "node_type": "source",
      "source_type": "delta",
      "config": { "database": "{bronze_schema}", "table": "base_customer_append", "cdf_enabled": true, "mode": "stream" }
    },
    {
      "name": "v_customer_address",
      "node_type": "source",
      "source_type": "delta",
      "config": { "database": "{bronze_schema}", "table": "base_customer_address_append", "cdf_enabled": true, "mode": "stream", "where_clause": ["STATE is not NULL"] }
    },
    {
      "name": "staging_customer_append",
      "node_type": "target",
      "config": {
        "table": "customer_ms_decomp_appnd",
        "input": ["v_customer", "v_customer_address"]
      }
    },
    {
      "name": "v_staging_cdf",
      "node_type": "source",
      "source_type": "delta",
      "config": { "table": "customer_ms_decomp_appnd", "cdf_enabled": true, "mode": "stream" }
    },
    {
      "name": "target_customer_merge",
      "node_type": "target",
      "config": {
        "database": "{silver_schema}",
        "table": "customer_ms_decomp_merge",
        "schema_path": "customer.json",
        "table_properties": { "delta.enableChangeDataFeed": "true" },
        "cdc_settings": {
          "keys": ["CUSTOMER_ID"],
          "sequence_by": "LOAD_TIMESTAMP",
          "scd_type": "2",
          "except_column_list": ["LOAD_TIMESTAMP"],
          "ignore_null_updates": true
        },
        "input": ["v_staging_cdf"]
      }
    }
  ]
}
```

There are no flow groups to assemble, no views to register by hand, and no
separate staging-table block. Fan-in is just two names in one `input` list, CDC
lives on the target it applies to, and adding another step later is another node
in the chain rather than another layer of nesting.

### Convergence behaviour

`nodespec` does not change the engine. The transformer lowers a node graph into
the framework's existing flow-spec representation, so all current capabilities
(CDC, snapshots, data quality, quarantine, sinks, table migration, materialized
views) are available. The legacy formats continue to transform into the same
representation, so the two can coexist during adoption.

### Aligning toward the chaining model

To steer everyone toward the chaining model, two behaviours change:

- **Inline SQL/Python sources are discouraged (warning, not breaking).** Folding
  transformation logic into a source definition, meaning a source whose type is
  `sql` or `python`, or an `append_sql` flow, conflates "where data comes from"
  with "how it is transformed". This still works, but now emits a warning, in
  both the legacy and `nodespec` formats. The recommended replacement is a plain
  source chained into a dedicated transformation node.

- **Inline source views on materialized view targets are removed (breaking).** A
  materialized view target may no longer carry an inline `source_view`. Authors
  declare a source node and chain it into the materialized view target via
  `input`, exactly like every other node. This keeps the graph uniform, with one
  way to feed a target rather than a special case for materialized views. Because
  this pattern was not in use, it is removed outright rather than deprecated.

## Consequences

- **One format to learn.** Knowledge transfers across every pipeline shape.
  Onboarding becomes "learn the three node types and how to chain them" instead of
  "learn three different specs and how to choose between them".

- **Specs are readable.** A reader follows the chain top-to-bottom and sees the
  pipeline's shape directly. Per-target settings live on the target they
  describe, which makes specs easier for teams to review and edit.

- **Topology is explicit.** Targets state what feeds them via `input`, and
  transformations name their upstream views directly in their logic, which makes
  specs inspectable and a natural fit for lineage and visual tooling.

- **Streaming tables and materialized views in one spec.** A single spec can
  declare both streaming-table and materialized-view targets, including chains
  where one feeds the other, so a logical pipeline no longer has to be split
  across specs by output type.

- **No loss of capability.** The node graph lowers into the existing flow-spec
  representation, so every current feature remains available.

- **Smooth adoption.** Legacy formats keep working. A migration script converts
  existing specs into `nodespec`. The inline-source-transformation warning gives
  consumers time to align before any future removal.

- **One breaking change.** Materialized view targets no longer accept an inline
  `source_view`, so authors chain a source node instead.

## Key design decisions

The decisions below define how the `nodespec` model behaves. They are the design
choices made while building out the format and translating the full feature set
onto it.

| Decision | Rationale |
|----------|-----------|
| **No primary or secondary target.** The spec target the backend needs (`targetDetails`) is auto-selected from the graph as the terminal target; authors never mark one. | "Primary target" was a backend implementation detail leaking into the spec. The graph already determines which target is terminal. |
| **All target settings live on the target node.** CDC, data quality, quarantine, table migration, and sink config are declared on the target they apply to, not at the spec level. | Each setting belongs with the thing it configures, which removes the spec-level scatter of the older formats. |
| **Materialized views are target nodes** (`table_type: "mv"`), and a single spec may contain both streaming-table and materialized-view targets, including chains between them. | Keeps the node model uniform and lets one logical pipeline stay in one spec instead of being split by output type. |
| **Inline SQL/Python sources and `append_sql` are discouraged.** They still work and are warned about; the recommended alternative is a transformation node, which defines the logic as a view rather than folding it into a source. | Keeps "where data comes from" separate from "how it is transformed". |
| **Materialized view inline `source_view` is removed (breaking).** Chain a source node into the MV target via `input`. | One uniform way to feed any target, with no special case for materialized views. |
| **Historical snapshot targets need no source node.** Targets with historical snapshot CDC config describe their source within that config; periodic snapshot targets still require a source. | The historical snapshot system reads files or tables directly, so a source view would have nothing to read. |
| **`input` is a target-node construct.** Each item is a string (auto flow name) or `{ "view", "flow" }` (flow name defined). | Source-to-transformation wiring lives in the transformation's own definition; `input` only describes what feeds a target. Defining the flow name avoids a full refresh in SDP on rename. |
| **Internal sources are auto-detected by table name.** A source that reads a table produced by a target in the same spec is wired internally with no extra view. | Enables staging-to-downstream chains without manual `live.` wiring. |
