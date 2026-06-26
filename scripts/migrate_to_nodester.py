#!/usr/bin/env python3
"""
Migrate Lakeflow Framework dataflow specs to Nodester format.

Converts standard, flow, and materialized_view specs into the node-based
Nodester specification format.

Nodester specs are snake_case throughout, so this script converts the
camelCase field names used by the standard/flow/materialized_view formats
(e.g. ``cdfEnabled`` -> ``cdf_enabled``, ``tableProperties`` ->
``table_properties``) while leaving opaque value maps (table properties,
reader options, spark conf, tokens) untouched.

Usage:
    python migrate_to_nodester.py <input_spec> [--output <path>]
    python migrate_to_nodester.py <input_dir> --output-dir <dir> [--recursive]

Examples:
    # Single file
    python migrate_to_nodester.py spec_main.json --output nodester_spec_main.json

    # Directory (all *_main.json files)
    python migrate_to_nodester.py ./dataflowspec/ --output-dir ./nodester_dataflowspec/
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
# nested `source` object. `recursiveFileLookup` is intentionally left camelCase
# (the framework reads it as-is).
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
    cdc = _get(src, "cdcSettings", "cdc_settings")
    if cdc:
        config["cdc_settings"] = cdc
    cdc_apply = _get(src, "cdcApplyChanges", "cdc_apply_changes")
    if cdc_apply:
        config["cdc_apply_changes"] = cdc_apply
    snapshot = _get(src, "cdcSnapshotSettings", "cdc_snapshot_settings")
    if snapshot:
        config["cdc_snapshot_settings"] = _convert_snapshot(snapshot)

    dq_enabled = _get(src, "dataQualityExpectationsEnabled", "data_quality_expectations_enabled")
    if dq_enabled:
        config["data_quality_expectations_enabled"] = dq_enabled
    dq_path = _get(src, "dataQualityExpectationsPath", "data_quality_expectations_path")
    if dq_path:
        config["data_quality_expectations_path"] = dq_path

    quarantine_mode = _get(src, "quarantineMode", "quarantine_mode")
    if quarantine_mode:
        config["quarantine_mode"] = quarantine_mode
    quarantine_details = _get(src, "quarantineTargetDetails", "quarantine_target_details")
    if quarantine_details:
        config["quarantine_target_details"] = _rename(quarantine_details, _QUARANTINE_MAP)

    table_migration = _get(src, "tableMigrationDetails", "table_migration_details")
    if table_migration:
        config["table_migration_details"] = _rename(table_migration, _TABLE_MIGRATION_MAP)


def _result_envelope(spec: Dict, nodes: List[Dict]) -> Dict:
    """Build the top-level nodester spec (snake_case metadata)."""
    result = {
        "data_flow_id": spec.get("dataFlowId") or spec.get("data_flow_id"),
        "data_flow_group": spec.get("dataFlowGroup") or spec.get("data_flow_group"),
        "data_flow_type": "nodester",
        "nodes": nodes,
    }
    version = _get(spec, "dataFlowVersion", "data_flow_version")
    if version:
        result["data_flow_version"] = version
    if spec.get("tags"):
        result["tags"] = spec["tags"]
    if spec.get("features"):
        result["features"] = spec["features"]
    return result


def migrate_spec(spec: Dict) -> Dict:
    """Convert a dataflow spec to nodester format based on its dataFlowType."""
    spec_type = (spec.get("dataFlowType") or spec.get("data_flow_type") or "standard").lower()

    if spec_type == "standard":
        return _migrate_standard(spec)
    elif spec_type == "flow":
        return _migrate_flow(spec)
    elif spec_type == "materialized_view":
        return _migrate_materialized_view(spec)
    elif spec_type == "nodester":
        return spec  # already nodester
    else:
        print(f"  Warning: Unknown dataFlowType '{spec_type}', treating as standard")
        return _migrate_standard(spec)


# ─── Standard Spec Migration ─────────────────────────────────────────────────

def _migrate_standard(spec: Dict) -> Dict:
    """Convert a standard spec to nodester."""
    source_id = spec.get("sourceViewName") or "v_source"
    source_node = _build_source_node(source_id, spec.get("sourceType", "delta"),
                                      spec.get("sourceDetails", {}), spec.get("mode", "stream"))

    target_config, target_type = _build_spec_target(spec)
    target_config["input"] = [source_id]
    target_name = target_config.get("table") or target_config.get("name") or "output"
    target_node: Dict[str, Any] = {"name": f"target_{target_name}", "node_type": "target"}
    if target_type != "delta":
        target_node["target_type"] = target_type
    target_node["config"] = target_config

    return _result_envelope(spec, [source_node, target_node])


def _build_source_node(name: str, source_type: str, source_details: Dict, mode: str) -> Dict:
    """Build a nodester source node (snake_case) from camelCase source details."""
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
    """Convert a flow spec to nodester."""
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
            config["input"] = []
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
            # spec), nodester models it as an explicit "internal" source node
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
                target_node["config"].setdefault("input", []).append(source_node_id)
            else:
                # Main (spec-level) target (delta or sink).
                target_id = f"target_{target_key}"
                if target_id not in node_ids:
                    node_ids.add(target_id)
                    main_config, target_type = _build_spec_target(spec)
                    if flow_details.get("once"):
                        main_config["once"] = True
                    main_config["input"] = [source_node_id]
                    main_node: Dict[str, Any] = {"name": target_id, "node_type": "target"}
                    if target_type != "delta":
                        main_node["target_type"] = target_type
                    main_node["config"] = main_config
                    nodes.append(main_node)

    # Drop placeholder empty input lists.
    for node in nodes:
        config = node.get("config", {})
        if config.get("input") == []:
            del config["input"]

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
    """Convert a materialized_view spec to nodester."""
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
            target_config["input"] = [source_id]

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
        description="Migrate Lakeflow Framework specs to Nodester format"
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
        output = args.output or args.input.replace(".json", "_nodester.json")
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
