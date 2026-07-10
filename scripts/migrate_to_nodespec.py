#!/usr/bin/env python3
"""
Migrate Lakeflow Framework dataflow specs to Nodespec format.

Converts standard, flow, and materialized_view specs into the node-based
Nodespec specification format.

Nodespec specs are snake_case throughout, so this script converts the
camelCase field names used by the standard/flow/materialized_view formats
(e.g. ``cdfEnabled`` -> ``cdf_enabled``, ``tableProperties`` ->
``table_properties``) while leaving opaque value maps (table properties,
reader options, spark conf, tokens) untouched.

Target wiring and feature settings use the current nodespec shape: targets
declare their inputs via ``input_flows``; data quality is a nested
``data_quality`` object; quarantine is a nested ``quarantine`` object
(``mode`` + optional ``target``). Sink targets keep their flat
``sink_type``/``sink_config``/``sink_options`` fields. Output is emitted in a
canonical field order (identity, then table/structural details, then feature
bundles, then ``input_flows``). Passing an existing nodespec spec normalises any
legacy fields and reorders it (idempotent).

Usage:
    python migrate_to_nodespec.py <input_spec> [--output <path>]
    python migrate_to_nodespec.py <input_dir> --output-dir <dir> [--recursive]

Examples:
    # Single file
    python migrate_to_nodespec.py spec_main.json --output nodespec_spec_main.json

    # Directory (all *_main.json files)
    python migrate_to_nodespec.py ./dataflowspec/ --output-dir ./nodespec_dataflowspec/
"""
import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Any, Tuple


# ─── camelCase -> snake_case key maps ────────────────────────────────────────
# Only structural keys are renamed. Values of opaque maps (table properties,
# reader options, spark conf, tokens) are copied verbatim — never recursed into.

_SOURCE_DETAIL_MAP = {
    "cdfEnabled": "cdf_enabled",
    "tablePath": "table_path",
    "readerOptions": "reader_options",
    "functionPath": "function_path",
    "pythonModule": "python_module",
    "sqlPath": "sql_path",
    "sqlStatement": "sql_statement",
    "selectExp": "select_exp",
    "whereClause": "where_clause",
    "schemaPath": "schema_path",
    "startingVersionFromDLTSetup": "starting_version_from_dlt_setup",
    "cdfChangeTypeOverride": "cdf_change_type_override",
    "pythonTransform": "python_transform",
}

_TARGET_DETAIL_MAP = {
    "schemaPath": "schema_path",
    "tableProperties": "table_properties",
    "partitionColumns": "partition_columns",
    "clusterByColumns": "cluster_by_columns",
    "clusterByAuto": "cluster_by_auto",
    "sparkConf": "spark_conf",
    "rowFilter": "row_filter",
    "configFlags": "config_flags",
}

# Snapshot settings carry camelCase keys at both the top level and inside the
# nested `source` object. All are converted to snake_case for nodespec; the
# transformer maps them back to the backend's camelCase at build time.
_SNAPSHOT_MAP = {
    "snapshotType": "snapshot_type",
    "sourceType": "source_type",
    "versionType": "version_type",
    "versionColumn": "version_column",
    "startingVersion": "starting_version",
    "datetimeFormat": "datetime_format",
    "readerOptions": "reader_options",
    "schemaPath": "schema_path",
    "selectExp": "select_exp",
    "deduplicateMode": "deduplicate_mode",
    "recursiveFileLookup": "recursive_file_lookup",
}

_QUARANTINE_MAP = {
    "targetFormat": "target_format",
    "clusterByAuto": "cluster_by_auto",
    "clusterByColumns": "cluster_by_columns",
    "partitionColumns": "partition_columns",
}

_TABLE_MIGRATION_MAP = {
    "catalogType": "catalog_type",
    "autoStartingVersionsEnabled": "auto_starting_versions_enabled",
    "sourceDetails": "source_details",
    "tableName": "table_name",
}

# Inner keys of table_migration_details.source_details (a delta source shape).
_MIGRATION_SOURCE_MAP = {
    "selectExp": "select_exp",
    "whereClause": "where_clause",
    "exceptColumns": "except_columns",
}

_PYTHON_TRANSFORM_MAP = {
    "functionPath": "function_path",
    "pythonModule": "python_module",
    "module": "module",
}


def _rename(d: Dict, mapping: Dict[str, str]) -> Dict:
    """Return a new dict with top-level keys renamed per mapping; values as-is."""
    if not isinstance(d, dict):
        return d
    return {mapping.get(k, k): v for k, v in d.items()}


# ─── canonical field ordering ────────────────────────────────────────────────
# A single, readable order applied to emitted specs, nodes, and configs so that
# generated (and hand-authored) specs read consistently: identity first, then
# table/structural details, then feature bundles, with input_flows (the wiring)
# last. Keys not listed keep their original relative order, after the known ones.

_SPEC_ORDER = ["data_flow_id", "data_flow_group", "data_flow_type",
               "data_flow_version", "tags", "features", "nodes"]

_NODE_ORDER = ["name", "node_type", "source_type", "transformation_type",
               "target_type", "output_view_name", "enabled", "config"]

_CONFIG_ORDER = [
    "mode", "database", "table", "table_path", "path", "format",
    "cdf_enabled", "cdf_change_type_override", "starting_version_from_dlt_setup",
    "table_type",
    "function_path", "python_module", "sql_path", "sql_statement", "tokens",
    "select_exp", "where_clause", "schema_path", "reader_options", "python_transform",
    "table_properties", "partition_columns", "cluster_by_columns", "cluster_by_auto",
    "comment", "spark_conf", "row_filter", "config_flags",
    "refresh_policy", "table_details", "once",
    "cdc_settings", "cdc_snapshot_settings", "data_quality", "quarantine",
    "table_migration_details",
    "name", "sink_type", "sink_config", "sink_options",
    "input_flows",
]


def _order(d: Dict, order: List[str]) -> Dict:
    """Return d with keys in `order` first (when present), remaining keys after."""
    if not isinstance(d, dict):
        return d
    known = [k for k in order if k in d]
    rest = [k for k in d if k not in order]
    return {k: d[k] for k in known + rest}


# nodespec authors enum VALUES in snake_case; legacy formats use camelCase for
# a few of them, so snake them during migration.
_SOURCE_TYPE_TO_SNAKE = {"cloudFiles": "cloud_files", "batchFiles": "batch_files", "deltaJoin": "delta_join"}
_CONFIG_FLAG_TO_SNAKE = {"disableOperationalMetadata": "disable_operational_metadata"}


def _snake_config_flag_values(obj) -> None:
    """Recursively snake `config_flags` array values in place."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "config_flags" and isinstance(v, list):
                obj[k] = [_CONFIG_FLAG_TO_SNAKE.get(x, x) if isinstance(x, str) else x for x in v]
            else:
                _snake_config_flag_values(v)
    elif isinstance(obj, list):
        for i in obj:
            _snake_config_flag_values(i)


def _order_node(node: Dict) -> Dict:
    """Order a node's keys and its config's keys canonically, and snake enum values."""
    if node.get("source_type") in _SOURCE_TYPE_TO_SNAKE:
        node["source_type"] = _SOURCE_TYPE_TO_SNAKE[node["source_type"]]
    node = _order(node, _NODE_ORDER)
    if isinstance(node.get("config"), dict):
        _snake_config_flag_values(node["config"])
        node["config"] = _order(node["config"], _CONFIG_ORDER)
    return node


def _convert_source_details(details: Dict) -> Dict:
    """camelCase -> snake_case for a source/view sourceDetails block."""
    out = _rename(details, _SOURCE_DETAIL_MAP)
    if isinstance(out.get("python_transform"), dict):
        out["python_transform"] = _rename(out["python_transform"], _PYTHON_TRANSFORM_MAP)
    return out


def _convert_snapshot(cs: Dict) -> Dict:
    """camelCase -> snake_case for cdcSnapshotSettings, including nested source."""
    out = _rename(cs, _SNAPSHOT_MAP)
    if isinstance(out.get("source"), dict):
        out["source"] = _rename(out["source"], _SNAPSHOT_MAP)
    return out


def _get(src: Dict, camel: str, snake: str):
    """Read a value that may be present under either camelCase or snake_case."""
    if camel in src:
        return src[camel]
    return src.get(snake)


def _add_target_settings(config: Dict, src: Dict) -> None:
    """Copy CDC / DQ / quarantine / table-migration settings onto a target config.

    `src` is the spec (standard), a staging-table config (flow), or an MV config.
    Reads either casing; writes snake_case.
    """
    # nodespec has a single CDC field (cdc_settings). Legacy cdcApplyChanges is
    # the same thing, so migrate either source key into cdc_settings.
    cdc = (_get(src, "cdcSettings", "cdc_settings")
           or _get(src, "cdcApplyChanges", "cdc_apply_changes"))
    if cdc:
        config["cdc_settings"] = cdc
    snapshot = _get(src, "cdcSnapshotSettings", "cdc_snapshot_settings")
    if snapshot:
        config["cdc_snapshot_settings"] = _convert_snapshot(snapshot)

    # Data quality collapses to a single nested object; presence implies enabled,
    # so the standalone enabled flag is dropped.
    dq_path = _get(src, "dataQualityExpectationsPath", "data_quality_expectations_path")
    if dq_path:
        config["data_quality"] = {"expectations_path": dq_path}

    # Quarantine collapses mode + target details into one nested object.
    # Mode "off" (or absent) means no quarantine, so no object is emitted.
    quarantine_mode = _get(src, "quarantineMode", "quarantine_mode")
    if quarantine_mode and quarantine_mode != "off":
        quarantine: Dict[str, Any] = {"mode": quarantine_mode}
        quarantine_details = _get(src, "quarantineTargetDetails", "quarantine_target_details")
        if quarantine_details:
            quarantine["target"] = _rename(quarantine_details, _QUARANTINE_MAP)
        config["quarantine"] = quarantine

    table_migration = _get(src, "tableMigrationDetails", "table_migration_details")
    if table_migration:
        tm = _rename(table_migration, _TABLE_MIGRATION_MAP)
        if isinstance(tm.get("source_details"), dict):
            tm["source_details"] = _rename(tm["source_details"], _MIGRATION_SOURCE_MAP)
        config["table_migration_details"] = tm


def _result_envelope(spec: Dict, nodes: List[Dict]) -> Dict:
    """Build the top-level nodespec spec (snake_case metadata)."""
    result = {
        "data_flow_id": spec.get("dataFlowId") or spec.get("data_flow_id"),
        "data_flow_group": spec.get("dataFlowGroup") or spec.get("data_flow_group"),
        "data_flow_type": "nodespec",
        "nodes": nodes,
    }
    version = _get(spec, "dataFlowVersion", "data_flow_version")
    if version:
        result["data_flow_version"] = version
    if spec.get("tags"):
        result["tags"] = spec["tags"]
    if spec.get("features"):
        result["features"] = spec["features"]
    result["nodes"] = [_order_node(n) for n in nodes]
    return _order(result, _SPEC_ORDER)


def _migrate_nodespec_config(cfg: Dict) -> None:
    """Migrate a single node config's legacy fields to the current shape, in place."""
    if "input" in cfg and "input_flows" not in cfg:
        cfg["input_flows"] = cfg.pop("input")
    path = cfg.pop("data_quality_expectations_path", None)
    cfg.pop("data_quality_expectations_enabled", None)
    if path and "data_quality" not in cfg:
        cfg["data_quality"] = {"expectations_path": path}
    mode = cfg.pop("quarantine_mode", None)
    qtd = cfg.pop("quarantine_target_details", None)
    if mode and mode != "off" and "quarantine" not in cfg:
        quarantine: Dict[str, Any] = {"mode": mode}
        if qtd:
            quarantine["target"] = qtd
        cfg["quarantine"] = quarantine


def _migrate_nodespec(spec: Dict) -> Dict:
    """Normalise an existing nodespec spec: migrate any legacy config fields
    (input -> input_flows; data_quality_expectations_* -> data_quality;
    quarantine_mode/quarantine_target_details -> quarantine) and apply the
    canonical field order. Idempotent for already-current specs."""
    for node in spec.get("nodes", []):
        if isinstance(node.get("config"), dict):
            _migrate_nodespec_config(node["config"])
    spec["nodes"] = [_order_node(n) for n in spec.get("nodes", [])]
    return _order(spec, _SPEC_ORDER)


def migrate_spec(spec: Dict) -> Dict:
    """Convert a dataflow spec to nodespec format based on its dataFlowType."""
    spec_type = (spec.get("dataFlowType") or spec.get("data_flow_type") or "standard").lower()

    if spec_type == "standard":
        return _migrate_standard(spec)
    elif spec_type == "flow":
        return _migrate_flow(spec)
    elif spec_type == "materialized_view":
        return _migrate_materialized_view(spec)
    elif spec_type == "nodespec":
        return _migrate_nodespec(spec)  # normalise legacy fields + canonical order
    else:
        print(f"  Warning: Unknown dataFlowType '{spec_type}', treating as standard")
        return _migrate_standard(spec)


# ─── Standard Spec Migration ─────────────────────────────────────────────────

def _migrate_standard(spec: Dict) -> Dict:
    """Convert a standard spec to nodespec."""
    # Historical snapshot targets read files/tables directly (via
    # cdc_snapshot_settings) and have no source node — the standard spec carries
    # no sourceDetails in that case, so don't synthesise one.
    snapshot = _get(spec, "cdcSnapshotSettings", "cdc_snapshot_settings") or {}
    is_historical_snapshot = _get(snapshot, "snapshotType", "snapshot_type") == "historical"

    nodes: List[Dict] = []
    source_id: Optional[str] = None
    if not is_historical_snapshot:
        source_id = spec.get("sourceViewName") or "v_source"
        nodes.append(_build_source_node(source_id, spec.get("sourceType", "delta"),
                                        spec.get("sourceDetails", {}), spec.get("mode", "stream")))

    target_config, target_type = _build_spec_target(spec)
    if source_id:
        target_config["input_flows"] = [source_id]
    target_name = target_config.get("table") or target_config.get("name") or "output"
    target_node: Dict[str, Any] = {"name": f"target_{target_name}", "node_type": "target"}
    if target_type != "delta":
        target_node["target_type"] = target_type
    target_node["config"] = target_config
    nodes.append(target_node)

    return _result_envelope(spec, nodes)


def _build_source_node(name: str, source_type: str, source_details: Dict, mode: str) -> Dict:
    """Build a nodespec source node (snake_case) from camelCase source details."""
    config: Dict[str, Any] = {}
    if mode:
        config["mode"] = mode
    config.update(_convert_source_details(source_details))

    node: Dict[str, Any] = {"name": name, "node_type": "source", "source_type": source_type}
    if config:
        node["config"] = config
    return node


def _build_spec_target(spec: Dict) -> Tuple[Dict, str]:
    """Build the spec-level target config (delta or sink). Returns (config, target_type)."""
    target_details = spec.get("targetDetails", {})
    target_format = spec.get("targetFormat", "delta")

    if target_format != "delta":
        # Sink target: map the known sink fields to snake_case.
        config = {}
        if "name" in target_details:
            config["name"] = target_details["name"]
        if "type" in target_details:
            config["sink_type"] = target_details["type"]
        if "config" in target_details:
            config["sink_config"] = target_details["config"]
        sink_options = _get(target_details, "sinkOptions", "sink_options")
        if sink_options is not None:
            config["sink_options"] = sink_options
    else:
        config = _rename(target_details, _TARGET_DETAIL_MAP)

    _add_target_settings(config, spec)
    return config, target_format


# ─── Flow Spec Migration ─────────────────────────────────────────────────────

def _migrate_flow(spec: Dict) -> Dict:
    """Convert a flow spec to nodespec."""
    nodes: List[Dict] = []
    node_ids: set = set()

    flow_groups = spec.get("flowGroups", [])

    staging_table_names = set()
    for fg in flow_groups:
        staging_table_names.update(fg.get("stagingTables", {}).keys())

    def find_target_node(target_name: str) -> Optional[Dict]:
        for n in nodes:
            if n["name"] == f"target_{target_name}":
                return n
        return None

    for fg in flow_groups:
        staging_tables = fg.get("stagingTables", {})
        flows = fg.get("flows", {})

        # Staging tables -> target nodes (inputs filled while processing flows).
        for stg_name, stg_config in staging_tables.items():
            target_id = f"target_{stg_name}"
            if target_id in node_ids:
                continue
            node_ids.add(target_id)
            config = _build_target_config_from_staging(stg_name, stg_config)
            config["input_flows"] = []
            nodes.append({"name": target_id, "node_type": "target", "config": config})

        for flow_name, flow_config in flows.items():
            flow_type = flow_config.get("flowType")
            flow_details = flow_config.get("flowDetails", {})
            target_table = flow_details.get("targetTable")
            views = flow_config.get("views", {})

            source_node_id = None

            # Views -> source nodes.
            for view_name, view_config in views.items():
                if view_name not in node_ids:
                    node_ids.add(view_name)
                    nodes.append(_build_source_node(
                        view_name,
                        view_config.get("sourceType", "delta"),
                        view_config.get("sourceDetails", {}),
                        view_config.get("mode", "stream"),
                    ))
                source_node_id = view_name

            # append_sql flows carry SQL directly in flowDetails (no view).
            if flow_type == "append_sql":
                sql_source_id = f"v_sql_{flow_name}"
                if sql_source_id not in node_ids:
                    node_ids.add(sql_source_id)
                    sql_config: Dict[str, Any] = {}
                    if flow_details.get("sqlStatement"):
                        sql_config["sql_statement"] = flow_details["sqlStatement"]
                    elif flow_details.get("sqlPath"):
                        sql_config["sql_path"] = flow_details["sqlPath"]
                    node: Dict[str, Any] = {"name": sql_source_id, "node_type": "source", "source_type": "sql"}
                    if sql_config:
                        node["config"] = sql_config
                    nodes.append(node)
                source_node_id = sql_source_id

            # Fall back to an explicit sourceView reference. When that reference
            # is a staging table (a table produced by another target in this
            # spec), nodespec models it as an explicit "internal" source node
            # that reads the staging table; the transformer auto-detects it.
            if not source_node_id and flow_details.get("sourceView"):
                source_view = flow_details["sourceView"]
                staging_key = source_view.split(".")[-1]
                if staging_key in staging_table_names:
                    internal_id = source_view if source_view.startswith("v_") else f"v_{staging_key}"
                    if internal_id not in node_ids:
                        node_ids.add(internal_id)
                        nodes.append({
                            "name": internal_id,
                            "node_type": "source",
                            "source_type": "delta",
                            "config": {"mode": "stream", "table": staging_key},
                        })
                    source_node_id = internal_id
                else:
                    source_node_id = source_view

            if not (target_table and source_node_id):
                continue

            # Strip any schema qualifier from the target table name when matching.
            target_key = target_table.split(".")[-1]
            target_node = find_target_node(target_key)
            if target_node is not None:
                target_node["config"].setdefault("input_flows", []).append(source_node_id)
            else:
                # Main (spec-level) target (delta or sink).
                target_id = f"target_{target_key}"
                if target_id not in node_ids:
                    node_ids.add(target_id)
                    main_config, target_type = _build_spec_target(spec)
                    if flow_details.get("once"):
                        main_config["once"] = True
                    main_config["input_flows"] = [source_node_id]
                    main_node: Dict[str, Any] = {"name": target_id, "node_type": "target"}
                    if target_type != "delta":
                        main_node["target_type"] = target_type
                    main_node["config"] = main_config
                    nodes.append(main_node)

    # Drop placeholder empty input lists.
    for node in nodes:
        config = node.get("config", {})
        if config.get("input_flows") == []:
            del config["input_flows"]

    return _result_envelope(spec, nodes)


def _build_target_config_from_staging(table_name: str, stg_config: Dict) -> Dict:
    """Build a target config from a flow staging-table definition."""
    config: Dict[str, Any] = {"table": table_name}
    config.update(_rename(
        {k: v for k, v in stg_config.items() if k != "type"},
        _TARGET_DETAIL_MAP,
    ))
    # Drop settings handled separately so they get correct snake_case + conversion.
    for k in ("cdcSettings", "cdc_settings", "cdcApplyChanges", "cdc_apply_changes",
              "cdcSnapshotSettings", "cdc_snapshot_settings",
              "dataQualityExpectationsEnabled", "data_quality_expectations_enabled",
              "dataQualityExpectationsPath", "data_quality_expectations_path",
              "quarantineMode", "quarantine_mode",
              "quarantineTargetDetails", "quarantine_target_details"):
        config.pop(k, None)
    _add_target_settings(config, stg_config)
    return config


# ─── Materialized View Spec Migration ─────────────────────────────────────────

def _migrate_materialized_view(spec: Dict) -> Dict:
    """Convert a materialized_view spec to nodespec."""
    materialized_views = spec.get("materializedViews", {})
    nodes: List[Dict] = []

    for mv_name, mv_config in materialized_views.items():
        target_config: Dict[str, Any] = {"table": mv_name, "table_type": "mv"}

        for camel, snake in (("sqlPath", "sql_path"), ("sqlStatement", "sql_statement"),
                             ("refreshPolicy", "refresh_policy")):
            val = _get(mv_config, camel, snake)
            if val is not None:
                target_config[snake] = val

        table_details = _get(mv_config, "tableDetails", "table_details")
        if table_details:
            target_config["table_details"] = _rename(table_details, _TARGET_DETAIL_MAP)

        _add_target_settings(target_config, mv_config)

        # MV source views are no longer inlined on the target: emit a source node
        # and chain it into the MV via `input`.
        source_view = _get(mv_config, "sourceView", "source_view")
        if isinstance(source_view, dict) and source_view:
            source_id = (source_view.get("sourceViewName")
                         or source_view.get("source_view_name")
                         or f"v_source_{mv_name}")
            nodes.append(_build_source_node(
                source_id,
                source_view.get("sourceType") or source_view.get("source_type", "delta"),
                source_view.get("sourceDetails") or source_view.get("source_details", {}),
                "batch",
            ))
            target_config["input_flows"] = [source_id]

        nodes.append({"name": f"target_{mv_name}", "node_type": "target", "config": target_config})

    return _result_envelope(spec, nodes)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def process_file(input_path: str, output_path: Optional[str] = None) -> str:
    """Process a single spec file."""
    with open(input_path, "r") as f:
        spec = json.load(f)

    result = migrate_spec(spec)

    if output_path is None:
        output_path = input_path

    with open(output_path, "w") as f:
        json.dump(result, f, indent=4)
        f.write("\n")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Lakeflow Framework specs to Nodespec format"
    )
    parser.add_argument("input", help="Input spec file or directory")
    parser.add_argument("--output", "-o", help="Output file (for single file mode)")
    parser.add_argument("--output-dir", "-d", help="Output directory (for directory mode)")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="Process directories recursively")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without writing files")

    args = parser.parse_args()

    if os.path.isfile(args.input):
        output = args.output or args.input.replace(".json", "_nodespec.json")
        if args.dry_run:
            print(f"Would convert: {args.input} → {output}")
        else:
            result = process_file(args.input, output)
            print(f"Converted: {args.input} → {result}")

    elif os.path.isdir(args.input):
        output_dir = args.output_dir or args.input
        os.makedirs(output_dir, exist_ok=True)

        count = 0
        for root, dirs, files in os.walk(args.input):
            for fname in sorted(files):
                if fname.endswith("_main.json"):
                    input_path = os.path.join(root, fname)
                    rel = os.path.relpath(input_path, args.input)
                    output_path = os.path.join(output_dir, rel)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                    if args.dry_run:
                        print(f"Would convert: {input_path} → {output_path}")
                    else:
                        try:
                            process_file(input_path, output_path)
                            print(f"  ✓ {fname}")
                            count += 1
                        except Exception as e:
                            print(f"  ✗ {fname}: {e}")

            if not args.recursive:
                break

        if not args.dry_run:
            print(f"\nConverted {count} files to {output_dir}")
    else:
        print(f"Error: {args.input} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
