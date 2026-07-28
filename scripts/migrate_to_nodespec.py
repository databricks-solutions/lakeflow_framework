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

Usage:
    python migrate_to_nodespec.py <input_spec> [--output <path>]
    python migrate_to_nodespec.py <input_dir> --output-dir <dir> [--recursive]
    python migrate_to_nodespec.py --bundle <source_bundle> --output-dir <target_bundle> [--overwrite]

Examples:
    # Single file
    python migrate_to_nodespec.py spec_main.json --output nodespec_spec_main.json

    # Directory (all *_main.json files)
    python migrate_to_nodespec.py ./dataflowspec/ --output-dir ./nodespec_dataflowspec/

    # Entire bundle (copy structure, convert specs in the copy)
    python migrate_to_nodespec.py --bundle samples/bronze_sample --output-dir samples/nodespec_sample
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
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
    return result


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
        return spec  # already nodespec
    else:
        print(f"  Warning: Unknown dataFlowType '{spec_type}', treating as standard")
        return _migrate_standard(spec)


def _table_key(name: Optional[str]) -> Optional[str]:
    """Return unqualified table name; preserve template placeholders with dots."""
    if not name:
        return name
    if "${" in name:
        return name
    return name.split(".")[-1]


# ─── Standard Spec Migration ─────────────────────────────────────────────────

def _migrate_standard(spec: Dict) -> Dict:
    """Convert a standard spec to nodespec."""
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
            # spec), nodespec models it as an explicit "internal" source node
            # that reads the staging table; the transformer auto-detects it.
            if not source_node_id and flow_details.get("sourceView"):
                source_view = flow_details["sourceView"]
                staging_key = _table_key(source_view)
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
            target_key = _table_key(target_table)
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
            target_config["input"] = [source_id]

        nodes.append({"name": f"target_{mv_name}", "node_type": "target", "config": target_config})

    return _result_envelope(spec, nodes)


# ─── Template specs ───────────────────────────────────────────────────────────

def is_template_instantiation_spec(spec: Dict) -> bool:
    """True for {template: <name>, parameterSets: [...]} main spec files."""
    return (
        isinstance(spec, dict)
        and isinstance(spec.get("template"), str)
        and "parameterSets" in spec
    )


def is_template_definition(defn: Dict) -> bool:
    """True for template definition files under src/templates/."""
    return (
        isinstance(defn, dict)
        and isinstance(defn.get("name"), str)
        and isinstance(defn.get("parameters"), dict)
        and isinstance(defn.get("template"), dict)
    )


def migrate_template_definition(defn: Dict) -> Dict:
    """Convert the embedded spec inside a template definition to nodespec."""
    return {
        "name": defn["name"],
        "parameters": defn["parameters"],
        "template": migrate_spec(defn["template"]),
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _is_dataflowspec_main(path: Path) -> bool:
    """True for dataflow main spec files under a dataflowspec directory."""
    return (
        path.name.endswith("_main.json")
        and "dataflowspec" in path.parts
    )


def find_dataflowspec_main_files(root: Path) -> List[Path]:
    """Return sorted paths to all *_main.json files under dataflowspec/."""
    return sorted(
        path
        for path in root.rglob("*_main.json")
        if _is_dataflowspec_main(path)
    )


def find_template_definition_files(root: Path) -> List[Path]:
    """Return sorted template definition JSON files under templates/."""
    return sorted(
        path
        for path in root.rglob("*.json")
        if "templates" in path.parts and path.is_file()
    )


def _write_json(path: str, data: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def _ensure_output_file(input_path: str, output_path: str, data: Optional[Dict] = None) -> str:
    """Write converted JSON or copy the source file when paths differ."""
    if output_path is None:
        output_path = input_path
    if data is not None:
        _write_json(output_path, data)
    elif output_path != input_path:
        shutil.copy2(input_path, output_path)
    return output_path


def process_file(input_path: str, output_path: Optional[str] = None) -> Tuple[str, str]:
    """Process a single dataflow main spec file.

    Returns:
        Tuple of (output path, status): ``converted``, ``skipped``, or ``unchanged``.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    if is_template_instantiation_spec(spec):
        return _ensure_output_file(input_path, output_path or input_path), "unchanged"

    spec_type = (spec.get("dataFlowType") or spec.get("data_flow_type") or "").lower()
    if spec_type == "nodespec":
        return _ensure_output_file(input_path, output_path or input_path), "skipped"

    result = migrate_spec(spec)
    out = _ensure_output_file(input_path, output_path or input_path, result)
    return out, "converted"


def process_template_definition_file(
    input_path: str,
    output_path: Optional[str] = None,
) -> Tuple[str, str]:
    """Migrate the embedded spec inside a template definition file."""
    with open(input_path, "r", encoding="utf-8") as f:
        defn = json.load(f)

    if not is_template_definition(defn):
        return _ensure_output_file(input_path, output_path or input_path), "unchanged"

    inner = defn["template"]
    inner_type = (inner.get("dataFlowType") or inner.get("data_flow_type") or "").lower()
    if inner_type == "nodespec":
        return _ensure_output_file(input_path, output_path or input_path), "skipped"

    result = migrate_template_definition(defn)
    out = _ensure_output_file(input_path, output_path or input_path, result)
    return out, "converted"


def migrate_bundle(
    source_bundle_path: str,
    target_bundle_path: str,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Copy a bundle and convert dataflow specs in the copy to nodespec format."""
    source_path = Path(source_bundle_path)
    target_path = Path(target_bundle_path)

    if not source_path.is_dir():
        raise FileNotFoundError(f"Source bundle not found: {source_path}")

    if target_path.exists():
        if not overwrite:
            raise FileExistsError(
                f"Target bundle already exists: {target_path}. Use --overwrite to replace."
            )
        if not dry_run:
            shutil.rmtree(target_path)

    stats: Dict[str, Any] = {
        "copied_bundle": str(target_path),
        "converted_files": 0,
        "converted_templates": 0,
        "skipped_files": 0,
        "unchanged_files": 0,
        "errors": [],
    }

    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}Migrating bundle from {source_path} to {target_path}")

    if not dry_run:
        shutil.copytree(source_path, target_path)

    bundle_root = target_path if not dry_run else source_path

    spec_files = find_dataflowspec_main_files(bundle_root)
    print(f"{prefix}Found {len(spec_files)} dataflow spec file(s) to process")

    for spec_path in spec_files:
        rel = spec_path.relative_to(bundle_root)
        if dry_run:
            with open(spec_path, encoding="utf-8") as f:
                spec = json.load(f)
            if is_template_instantiation_spec(spec):
                print(f"  Would leave unchanged (template spec): {rel}")
                stats["unchanged_files"] += 1
            else:
                print(f"  Would convert: {rel}")
                stats["converted_files"] += 1
            continue

        try:
            _, status = process_file(str(spec_path), str(spec_path))
            if status == "unchanged":
                print(f"  - {rel} (template spec, unchanged)")
                stats["unchanged_files"] += 1
            elif status == "skipped":
                print(f"  - {rel} (already nodespec)")
                stats["skipped_files"] += 1
            else:
                print(f"  ✓ {rel}")
                stats["converted_files"] += 1
        except Exception as exc:  # pylint: disable=broad-except
            message = f"{rel}: {exc}"
            print(f"  ✗ {message}")
            stats["errors"].append(message)

    template_files = find_template_definition_files(bundle_root)
    if template_files:
        print(f"{prefix}Found {len(template_files)} template definition file(s) to process")

    for template_path in template_files:
        rel = template_path.relative_to(bundle_root)
        if dry_run:
            with open(template_path, encoding="utf-8") as f:
                defn = json.load(f)
            if not is_template_definition(defn):
                continue
            inner_type = (
                defn["template"].get("dataFlowType")
                or defn["template"].get("data_flow_type")
                or ""
            ).lower()
            if inner_type == "nodespec":
                print(f"  Would skip template (already nodespec): {rel}")
                stats["skipped_files"] += 1
            else:
                print(f"  Would convert template: {rel}")
                stats["converted_templates"] += 1
            continue

        try:
            _, status = process_template_definition_file(str(template_path), str(template_path))
            if status == "skipped":
                print(f"  - {rel} (template already nodespec)")
                stats["skipped_files"] += 1
            elif status == "converted":
                print(f"  ✓ {rel}")
                stats["converted_templates"] += 1
        except Exception as exc:  # pylint: disable=broad-except
            message = f"{rel}: {exc}"
            print(f"  ✗ {message}")
            stats["errors"].append(message)

    print("\n" + "=" * 80)
    print("Migration Summary:")
    print("=" * 80)
    print(f"Target bundle: {target_path}")
    print(f"Specs converted: {stats['converted_files']}")
    print(f"Template definitions converted: {stats['converted_templates']}")
    print(f"Template specs left unchanged: {stats['unchanged_files']}")
    print(f"Specs skipped (already nodespec): {stats['skipped_files']}")
    if stats["errors"]:
        print(f"Errors: {len(stats['errors'])}")
    print("=" * 80)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Lakeflow Framework specs to Nodespec format"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input spec file or directory (not used with --bundle)",
    )
    parser.add_argument(
        "--bundle",
        metavar="PATH",
        help="Source bundle directory to copy and migrate",
    )
    parser.add_argument("--output", "-o", help="Output file (single file mode)")
    parser.add_argument(
        "--output-dir", "-d",
        help="Output directory (directory or bundle mode)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing target bundle (bundle mode only)",
    )
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="Process directories recursively")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without writing files")

    args = parser.parse_args()

    if args.bundle:
        if not args.output_dir:
            parser.error("--bundle requires --output-dir <target_bundle>")
        try:
            stats = migrate_bundle(
                args.bundle,
                args.output_dir,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, FileExistsError) as exc:
            print(f"Error: {exc}")
            sys.exit(1)
        if stats["errors"]:
            sys.exit(1)
        return

    if not args.input:
        parser.error("input path is required unless --bundle is used")

    if os.path.isfile(args.input):
        output = args.output or args.input.replace(".json", "_nodespec.json")
        if args.dry_run:
            print(f"Would convert: {args.input} → {output}")
        else:
            result, status = process_file(args.input, output)
            if status == "unchanged":
                print(f"Left unchanged (template spec): {args.input}")
            elif status == "skipped":
                print(f"Skipped (already nodespec): {args.input}")
            else:
                print(f"Converted: {args.input} → {result}")

    elif os.path.isdir(args.input):
        output_dir = args.output_dir or args.input
        os.makedirs(output_dir, exist_ok=True)

        count = 0
        skipped = 0
        unchanged = 0
        for root, _, files in os.walk(args.input):
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
                            _, status = process_file(input_path, output_path)
                            if status == "unchanged":
                                print(f"  - {fname} (template spec, unchanged)")
                                unchanged += 1
                            elif status == "skipped":
                                print(f"  - {fname} (already nodespec)")
                                skipped += 1
                            else:
                                print(f"  ✓ {fname}")
                                count += 1
                        except Exception as e:
                            print(f"  ✗ {fname}: {e}")

            if not args.recursive:
                break

        if not args.dry_run:
            print(f"\nConverted {count} files to {output_dir}")
            if unchanged:
                print(f"Left {unchanged} template spec file(s) unchanged")
            if skipped:
                print(f"Skipped {skipped} file(s) already in nodespec format")
    else:
        print(f"Error: {args.input} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
