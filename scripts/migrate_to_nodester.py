#!/usr/bin/env python3
"""
Migrate Lakeflow Framework dataflow specs to Nodester format.

Converts standard, flow, and materialized_view specs into the
node-based Nodester specification format.

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


def migrate_spec(spec: Dict) -> Dict:
    """Convert a dataflow spec to nodester format based on its dataFlowType."""
    spec_type = spec.get("dataFlowType", "standard").lower()

    if spec_type == "standard":
        return _migrate_standard(spec)
    elif spec_type == "flow":
        return _migrate_flow(spec)
    elif spec_type == "materialized_view":
        return _migrate_materialized_view(spec)
    else:
        print(f"  Warning: Unknown dataFlowType '{spec_type}', treating as standard")
        return _migrate_standard(spec)


# ─── Standard Spec Migration ─────────────────────────────────────────────────

def _migrate_standard(spec: Dict) -> Dict:
    """Convert a standard spec to nodester."""
    nodes = []

    # Build source node
    source_id = spec.get("sourceViewName", "source").replace("v_", "", 1)
    if not source_id:
        source_id = "source"
    source_node = _build_source_node_from_standard(source_id, spec)
    nodes.append(source_node)

    # Build target node
    target_config, target_type = _build_target_config_from_standard(spec)
    target_id = f"target_{target_config.get('table', target_config.get('name', 'output'))}"
    target_config["input"] = [source_id]
    target_node: Dict[str, Any] = {
        "name": target_id,
        "node_type": "target",
    }
    if target_type != "delta":
        target_node["target_type"] = target_type
    target_node["config"] = target_config
    nodes.append(target_node)

    # Build nodester spec
    result = {
        "data_flow_id": spec.get("dataFlowId"),
        "data_flow_group": spec.get("dataFlowGroup"),
        "data_flow_type": "nodester",
        "nodes": nodes
    }

    if spec.get("dataFlowVersion"):
        result["data_flow_version"] = spec["data_flow_version"]
    if spec.get("tags"):
        result["tags"] = spec["tags"]
    if spec.get("features"):
        result["features"] = spec["features"]

    return result


def _build_source_node_from_standard(source_id: str, spec: Dict) -> Dict:
    """Build a source node from a standard spec's source fields."""
    source_type = spec.get("sourceType", "delta")
    source_details = spec.get("sourceDetails", {})
    mode = spec.get("mode", "stream")

    config: Dict[str, Any] = {}

    if mode:
        config["mode"] = mode

    # Copy source details based on type
    if source_type == "delta":
        for key in ["database", "table", "cdfEnabled", "tablePath"]:
            if key in source_details:
                config[key] = source_details[key]
    elif source_type in ("cloudFiles", "batchFiles"):
        for key in ["path", "readerOptions"]:
            if key in source_details:
                config[key] = source_details[key]
    elif source_type == "python":
        for key in ["functionPath", "pythonModule", "tokens"]:
            if key in source_details:
                config[key] = source_details[key]
    elif source_type == "sql":
        for key in ["sqlPath", "sqlStatement"]:
            if key in source_details:
                config[key] = source_details[key]
    elif source_type == "kafka":
        if "readerOptions" in source_details:
            config["reader_options"] = source_details["readerOptions"]

    # Common optional source properties
    for key in ["selectExp", "whereClause", "schemaPath"]:
        if key in source_details:
            config[key] = source_details[key]

    node: Dict[str, Any] = {"name": source_id, "node_type": "source", "source_type": source_type}
    if config:
        node["config"] = config
    return node


def _build_target_config_from_standard(spec: Dict) -> Tuple[Dict, str]:
    """Build target node config from standard spec's target and spec-level settings.

    Returns (config_dict, target_type_string).
    """
    target_details = spec.get("targetDetails", {})
    target_format = spec.get("targetFormat", "delta")

    config: Dict[str, Any] = {}

    if target_format != "delta":
        # For sinks, copy all target details directly
        for key, val in target_details.items():
            config[key] = val
    else:
        # Delta target
        for key in ["table", "database", "schemaPath", "tableProperties", "path",
                     "partitionColumns", "clusterByColumns", "clusterByAuto",
                     "comment", "sparkConf", "rowFilter", "configFlags"]:
            if key in target_details:
                config[key] = target_details[key]

    # Move spec-level settings to target config
    for key in ["cdc_settings", "cdc_apply_changes", "cdc_snapshot_settings"]:
        if spec.get(key):
            config[key] = spec[key]

    if spec.get("dataQualityExpectationsEnabled"):
        config["data_quality_expectations_enabled"] = spec["data_quality_expectations_enabled"]
    if spec.get("dataQualityExpectationsPath"):
        config["data_quality_expectations_path"] = spec["data_quality_expectations_path"]
    if spec.get("quarantineMode"):
        config["quarantine_mode"] = spec["quarantine_mode"]
    if spec.get("quarantineTargetDetails"):
        config["quarantine_target_details"] = spec["quarantine_target_details"]
    if spec.get("tableMigrationDetails"):
        config["table_migration_details"] = spec["table_migration_details"]

    return config, target_format


# ─── Flow Spec Migration ─────────────────────────────────────────────────────

def _migrate_flow(spec: Dict) -> Dict:
    """Convert a flow spec to nodester."""
    nodes = []
    node_ids = set()

    flow_groups = spec.get("flowGroups", [])

    # Collect all staging table names (these become target nodes)
    staging_table_names = set()
    for fg in flow_groups:
        for name in fg.get("stagingTables", {}).keys():
            staging_table_names.add(name)

    # Process each flow group
    for fg in flow_groups:
        staging_tables = fg.get("stagingTables", {})
        flows = fg.get("flows", {})

        # Create target nodes for staging tables
        for stg_name, stg_config in staging_tables.items():
            target_id = f"target_{stg_name}"
            if target_id in node_ids:
                continue
            node_ids.add(target_id)

            target_config = _build_target_config_from_staging(stg_name, stg_config)
            target_config["input"] = []  # placeholder, filled when processing flows
            nodes.append({
                "name": target_id,
                "node_type": "target",
                "config": target_config,
            })

        # Process flows
        for flow_name, flow_config in flows.items():
            flow_type = flow_config.get("flowType")
            flow_details = flow_config.get("flowDetails", {})
            target_table = flow_details.get("targetTable")
            views = flow_config.get("views", {})

            # Create source/transform nodes from views
            source_node_id = None
            for view_name, view_config in views.items():
                if view_name in node_ids:
                    continue
                node_ids.add(view_name)

                view_source_details = view_config.get("sourceDetails", {})
                view_source_type = view_config.get("sourceType", "delta")
                view_mode = view_config.get("mode", "stream")

                # Check if this view reads from a staging table (internal source)
                view_db = view_source_details.get("database", "")
                view_table = view_source_details.get("table", "")
                is_internal = (
                    view_db == "live" and view_table in staging_table_names
                )

                # Build source node config
                src_config: Dict[str, Any] = {}
                if view_mode:
                    src_config["mode"] = view_mode

                # Copy source details
                for key, val in view_source_details.items():
                    src_config[key] = val

                src_node: Dict[str, Any] = {
                    "name": view_name,
                    "node_type": "source",
                    "source_type": view_source_type,
                }
                if src_config:
                    src_node["config"] = src_config
                nodes.append(src_node)
                source_node_id = view_name

            # Handle append_sql flows (SQL is in flowDetails, not views)
            if flow_type == "append_sql":
                sql_source_id = f"sql_{flow_name}"
                if sql_source_id not in node_ids:
                    node_ids.add(sql_source_id)
                    sql_config: Dict[str, Any] = {}
                    if flow_details.get("sqlStatement"):
                        sql_config["sql_statement"] = flow_details["sql_statement"]
                    elif flow_details.get("sqlPath"):
                        sql_config["sql_path"] = flow_details["sql_path"]
                    sql_node: Dict[str, Any] = {
                        "name": sql_source_id,
                        "node_type": "source",
                        "source_type": "sql",
                    }
                    if sql_config:
                        sql_node["config"] = sql_config
                    nodes.append(sql_node)
                    source_node_id = sql_source_id

            # If no views and not append_sql, use the sourceView reference
            if not source_node_id and flow_details.get("sourceView"):
                source_node_id = flow_details["source_view"]

            # Connect flow to target
            if target_table and source_node_id:
                # Find the target node
                target_node_id = f"target_{target_table}"
                target_found = False
                for node in nodes:
                    if node["name"] == target_node_id:
                        if source_node_id not in node.get("inputs", []):
                            node.setdefault("config", {}).setdefault("input", []).append(source_node_id)
                        target_found = True
                        break

                if not target_found:
                    # This is the main target
                    if target_node_id not in node_ids:
                        node_ids.add(target_node_id)
                        main_target_config = _build_target_config_from_spec_level(spec)
                        # Add once flag if present
                        if flow_details.get("once"):
                            main_target_config["once"] = True
                        main_target_config["input"] = [source_node_id]
                        nodes.append({
                            "name": target_node_id,
                            "node_type": "target",
                            "config": main_target_config
                        })
                    else:
                        # Find existing and add input
                        for node in nodes:
                            if node["name"] == target_node_id:
                                node.setdefault("config", {}).setdefault("input", []).append(source_node_id)
                                break

    # Clean up empty inputSources
    for node in nodes:
        config = node.get("config", {})
        if config.get("input") == []:
            del config["input"]

    result = {
        "data_flow_id": spec.get("dataFlowId"),
        "data_flow_group": spec.get("dataFlowGroup"),
        "data_flow_type": "nodester",
        "nodes": nodes
    }

    if spec.get("dataFlowVersion"):
        result["data_flow_version"] = spec["data_flow_version"]
    if spec.get("tags"):
        result["tags"] = spec["tags"]
    if spec.get("features"):
        result["features"] = spec["features"]

    return result


def _build_target_config_from_staging(table_name: str, stg_config: Dict) -> Dict:
    """Build target config from staging table definition."""
    config: Dict[str, Any] = {"table": table_name}

    for key in ["tableProperties", "schemaPath", "clusterByColumns",
                 "clusterByAuto", "partitionColumns", "database", "configFlags"]:
        if key in stg_config:
            config[key] = stg_config[key]

    # CDC settings
    for key in ["cdc_settings", "cdc_apply_changes", "cdc_snapshot_settings"]:
        if key in stg_config:
            config[key] = stg_config[key]

    # DQ settings
    if stg_config.get("dataQualityExpectationsEnabled"):
        config["data_quality_expectations_enabled"] = stg_config["data_quality_expectations_enabled"]
    if stg_config.get("dataQualityExpectationsPath"):
        config["data_quality_expectations_path"] = stg_config["data_quality_expectations_path"]

    # Quarantine
    if stg_config.get("quarantineMode"):
        config["quarantine_mode"] = stg_config["quarantine_mode"]
    if stg_config.get("quarantineTargetDetails"):
        config["quarantine_target_details"] = stg_config["quarantine_target_details"]

    return config


def _build_target_config_from_spec_level(spec: Dict) -> Dict:
    """Build main target config from spec-level target details and settings."""
    target_details = spec.get("targetDetails", {})
    config: Dict[str, Any] = {}

    for key in ["table", "database", "schema_path", "table_properties", "path",
                 "partition_columns", "cluster_by_columns", "cluster_by_auto",
                 "comment", "spark_conf", "row_filter", "config_flags"]:
        if key in target_details:
            config[key] = target_details[key]

    # Spec-level settings → target config
    for key in ["cdc_settings", "cdc_apply_changes", "cdc_snapshot_settings"]:
        if spec.get(key):
            config[key] = spec[key]

    if spec.get("dataQualityExpectationsEnabled"):
        config["data_quality_expectations_enabled"] = spec["data_quality_expectations_enabled"]
    if spec.get("dataQualityExpectationsPath"):
        config["data_quality_expectations_path"] = spec["data_quality_expectations_path"]
    if spec.get("quarantineMode"):
        config["quarantine_mode"] = spec["quarantine_mode"]
    if spec.get("quarantineTargetDetails"):
        config["quarantine_target_details"] = spec["quarantine_target_details"]
    if spec.get("tableMigrationDetails"):
        config["table_migration_details"] = spec["table_migration_details"]

    return config


# ─── Materialized View Spec Migration ─────────────────────────────────────────

def _migrate_materialized_view(spec: Dict) -> Dict:
    """Convert a materialized_view spec to nodester."""
    materialized_views = spec.get("materializedViews", {})
    nodes = []

    for mv_name, mv_config in materialized_views.items():
        target_config: Dict[str, Any] = {
            "table": mv_name,
            "table_type": "mv"
        }

        # Copy MV properties
        for key in ["sql_path", "sql_statement", "refresh_policy"]:
            if key in mv_config:
                target_config[key] = mv_config[key]

        # Copy table details
        if mv_config.get("tableDetails"):
            target_config["table_details"] = mv_config["table_details"]

        # Copy DQ settings
        if mv_config.get("dataQualityExpectationsEnabled"):
            target_config["data_quality_expectations_enabled"] = mv_config["data_quality_expectations_enabled"]
        if mv_config.get("dataQualityExpectationsPath"):
            target_config["data_quality_expectations_path"] = mv_config["data_quality_expectations_path"]
        if mv_config.get("quarantineMode"):
            target_config["quarantine_mode"] = mv_config["quarantine_mode"]
        if mv_config.get("quarantineTargetDetails"):
            target_config["quarantine_target_details"] = mv_config["quarantine_target_details"]

        # Handle source view: MV source views are no longer inlined on the
        # target. Emit a source node and chain it into the MV via `input`.
        source_view = mv_config.get("source_view")
        input_sources = []
        if source_view:
            source_id = source_view.get("sourceViewName", f"source_{mv_name}")
            # Create a source node for the view
            src_config: Dict[str, Any] = {"mode": "stream"}
            for key, val in source_view.get("sourceDetails", {}).items():
                src_config[key] = val
            nodes.append({
                "name": source_id,
                "node_type": "source",
                "source_type": source_view.get("sourceType", "delta"),
                "config": src_config
            })
            input_sources = [source_id]

        target_node: Dict[str, Any] = {
            "name": f"target_{mv_name}",
            "node_type": "target",
            "config": target_config
        }
        if input_sources:
            target_config["input"] = input_sources
        nodes.append(target_node)

    result = {
        "data_flow_id": spec.get("dataFlowId"),
        "data_flow_group": spec.get("dataFlowGroup"),
        "data_flow_type": "nodester",
        "nodes": nodes
    }

    if spec.get("tags"):
        result["tags"] = spec["tags"]
    if spec.get("features"):
        result["features"] = spec["features"]

    return result


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

        pattern = "*_main.json"
        count = 0
        for root, dirs, files in os.walk(args.input):
            for fname in sorted(files):
                if fname.endswith("_main.json") or fname.endswith(".json"):
                    input_path = os.path.join(root, fname)

                    # Compute relative path for output
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
