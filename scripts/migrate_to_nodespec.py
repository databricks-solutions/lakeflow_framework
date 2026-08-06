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

Specs may be JSON (``*_main.json``) or YAML (``*_main.yaml`` / ``*_main.yml``);
the format is detected from the file extension and preserved in the output, so
a YAML bundle stays YAML. (YAML migration requires PyYAML.)

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
    python migrate_to_nodespec.py --bundle legacy_samples/feature_samples --output-dir samples/feature_samples
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# ─── camelCase -> snake_case key maps ────────────────────────────────────────
# Nodespec is snake_case throughout. Structural keys are renamed; values of
# opaque maps (table properties, reader options, spark conf, tokens) are copied
# verbatim — the rename map only touches known structural keys, so unmapped
# keys inside those blobs pass through unchanged. This mirrors the runtime
# transformer's `_KEYS` map (transformer/nodespec.py) in reverse.

# The single camelCase -> snake_case structural key map. Identity keys
# (database, table, path, comment, name, tokens, private, alias, condition,
# format, keys, enabled, once, mode, sequence_by, scd_type, where, ...) need no
# entry.
_CAMEL_TO_SNAKE = {
    "schemaPath": "schema_path",
    "tableProperties": "table_properties",
    "partitionColumns": "partition_columns",
    "clusterByColumns": "cluster_by_columns",
    "clusterByAuto": "cluster_by_auto",
    "sparkConf": "spark_conf",
    "rowFilter": "row_filter",
    "configFlags": "config_flags",
    "cdfEnabled": "cdf_enabled",
    "tablePath": "table_path",
    "readerOptions": "reader_options",
    "sqlPath": "sql_path",
    "sqlStatement": "sql_statement",
    "functionPath": "function_path",
    "pythonModule": "python_module",
    "pythonTransform": "python_transform",
    "selectExp": "select_exp",
    "whereClause": "where_clause",
    "exceptColumns": "except_columns",
    "refreshPolicy": "refresh_policy",
    "startingVersionFromDLTSetup": "starting_version_from_dlt_setup",
    "cdfChangeTypeOverride": "cdf_change_type_override",
    # nested snapshot-CDC keys
    "snapshotType": "snapshot_type",
    "sourceType": "source_type",
    "versionType": "version_type",
    "versionColumn": "version_column",
    "startingVersion": "starting_version",
    "datetimeFormat": "datetime_format",
    "deduplicateMode": "deduplicate_mode",
    "recursiveFileLookup": "recursive_file_lookup",
    # nested table-migration keys
    "catalogType": "catalog_type",
    "autoStartingVersionsEnabled": "auto_starting_versions_enabled",
    "tableName": "table_name",
    # delta_join source keys
    "joinMode": "join_mode",
    "joinType": "join_type",
    # quarantine target keys
    "targetFormat": "target_format",
}

# Flat (top-level only) rename for a delta target's details block. Leaves the
# values of opaque maps (table_properties, spark_conf) untouched.
_TARGET_DETAIL_MAP = {
    "schemaPath": "schema_path",
    "tableProperties": "table_properties",
    "partitionColumns": "partition_columns",
    "clusterByColumns": "cluster_by_columns",
    "clusterByAuto": "cluster_by_auto",
    "sparkConf": "spark_conf",
    "rowFilter": "row_filter",
    "configFlags": "config_flags",
    "comment": "comment",
}

# Flat rename for a source/view sourceDetails block. reader_options values stay
# opaque.
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

_PYTHON_TRANSFORM_MAP = {
    "functionPath": "function_path",
    "pythonModule": "python_module",
    "module": "module",
}

# Source type enum VALUES: legacy camelCase -> nodespec snake_case.
_SOURCE_TYPE_MAP = {
    "cloudFiles": "cloud_files",
    "batchFiles": "batch_files",
    "deltaJoin": "delta_join",
}

# config_flags enum VALUES: legacy camelCase -> nodespec snake_case.
_CONFIG_FLAG_MAP = {
    "disableOperationalMetadata": "disable_operational_metadata",
}


def _rename(d: Dict, mapping: Dict[str, str]) -> Dict:
    """Return a new dict with top-level keys renamed per mapping; values as-is."""
    if not isinstance(d, dict):
        return d
    return {mapping.get(k, k): v for k, v in d.items()}


def _deep_snake(obj: Any) -> Any:
    """Recursively rename structural keys camelCase -> snake_case in nested blobs.

    Used for snapshot CDC, table migration, delta_join sources/joins, and sink
    config/options. Unmapped keys (e.g. literal reader-option keys or table
    property names) pass through unchanged, and scalar values are never touched.
    """
    if isinstance(obj, dict):
        return {_CAMEL_TO_SNAKE.get(k, k): _deep_snake(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_snake(i) for i in obj]
    return obj


def _fix_config_flags(config: Dict) -> None:
    """Rewrite config_flags enum values to snake_case, in place."""
    flags = config.get("config_flags")
    if isinstance(flags, list):
        config["config_flags"] = [_CONFIG_FLAG_MAP.get(f, f) for f in flags]


def _map_source_type(source_type: str) -> str:
    """Map a legacy source type enum value to its nodespec snake_case form."""
    return _SOURCE_TYPE_MAP.get(source_type, source_type)


def _convert_source_details(details: Dict) -> Dict:
    """camelCase -> snake_case for a source/view sourceDetails block."""
    out = _rename(details, _SOURCE_DETAIL_MAP)
    if isinstance(out.get("python_transform"), dict):
        out["python_transform"] = _rename(out["python_transform"], _PYTHON_TRANSFORM_MAP)
    return out


def _convert_snapshot(cs: Dict) -> Dict:
    """camelCase -> snake_case for cdcSnapshotSettings, including nested source.

    `source_type` / `source` values (file/table etc.) are enum values and stay
    as-is; only structural keys are renamed.
    """
    return _deep_snake(cs)


def _convert_table_migration(tm: Dict) -> Dict:
    """camelCase -> snake_case for tableMigrationDetails.

    The nested legacy ``sourceDetails`` block becomes ``source`` (the nodespec
    field name the runtime transformer reads).
    """
    out: Dict[str, Any] = {}
    for k, v in tm.items():
        if k in ("sourceDetails", "source_details", "source"):
            out["source"] = _deep_snake(v)
        else:
            out[_CAMEL_TO_SNAKE.get(k, k)] = _deep_snake(v)
    return out


def _get(src: Dict, camel: str, snake: str):
    """Read a value that may be present under either camelCase or snake_case."""
    if camel in src:
        return src[camel]
    return src.get(snake)


def _add_target_settings(config: Dict, src: Dict) -> None:
    """Copy CDC / DQ / quarantine / table-migration settings onto a target config.

    `src` is the spec (standard), a staging-table config (flow), or an MV config.
    Reads either casing; writes the current nested nodespec shape:
      - cdcSettings / cdcApplyChanges -> ``cdc_settings``
      - cdcSnapshotSettings           -> ``cdc_snapshot_settings``
      - data quality + quarantine     -> nested ``data_quality`` (with nested
                                         ``quarantine`` for quarantine settings)
      - tableMigrationDetails         -> ``table_migration`` (inner ``source``)
    """
    # cdcSettings and cdcApplyChanges both map to the single nodespec
    # ``cdc_settings`` object the transformer reads.
    cdc = (_get(src, "cdcSettings", "cdc_settings")
           or _get(src, "cdcApplyChanges", "cdc_apply_changes"))
    if cdc:
        config["cdc_settings"] = cdc
    snapshot = _get(src, "cdcSnapshotSettings", "cdc_snapshot_settings")
    if snapshot:
        config["cdc_snapshot_settings"] = _convert_snapshot(snapshot)

    _add_data_quality(config, src)

    table_migration = _get(src, "tableMigrationDetails", "table_migration_details")
    if table_migration:
        config["table_migration"] = _convert_table_migration(table_migration)


def _add_data_quality(config: Dict, src: Dict) -> None:
    """Build the nested ``data_quality`` object from legacy flat DQ/quarantine keys.

    The nodespec ``data_quality`` object requires ``expectations_path``; a spec
    with expectations disabled and no path (and a quarantine mode of ``off``)
    has no data quality to express, so the whole object is omitted.
    """
    dq_enabled = _get(src, "dataQualityExpectationsEnabled", "data_quality_expectations_enabled")
    dq_path = _get(src, "dataQualityExpectationsPath", "data_quality_expectations_path")
    quarantine_mode = _get(src, "quarantineMode", "quarantine_mode")
    quarantine_details = _get(src, "quarantineTargetDetails", "quarantine_target_details")

    # A quarantine mode of "off" (or missing) means no quarantine.
    if quarantine_mode in (None, "off", "none", ""):
        quarantine_mode = None
        quarantine_details = None

    # Without an expectations path there is nothing valid to emit (path is
    # required), so drop DQ entirely — matching hand-authored nodespec specs.
    if not dq_path:
        return

    data_quality: Dict[str, Any] = {}
    if dq_enabled is not None:
        data_quality["enabled"] = dq_enabled
    data_quality["expectations_path"] = dq_path

    if quarantine_mode or quarantine_details:
        quarantine: Dict[str, Any] = {}
        if quarantine_mode:
            quarantine["mode"] = quarantine_mode
        if quarantine_details:
            quarantine["target"] = _deep_snake(quarantine_details)
        data_quality["quarantine"] = quarantine

    config["data_quality"] = data_quality


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


def _flow_name(view: str) -> str:
    """The SDP flow name the framework derives for a source view.

    The legacy standard/materialized_view transformers name the flow
    ``f_{sourceViewName}`` verbatim (e.g. ``v_customer`` -> ``f_v_customer``),
    so the ``f_`` prefix is added without stripping the view's ``v_`` prefix.
    The nodespec transformer derives the identical name, so a migrated spec does
    not need to restate it — this helper exists only for comparison/testing.
    """
    return f"f_{view}"


def _source_entry(view: str, flow: Optional[str] = None) -> Any:
    """A single ``sources`` entry.

    Only emit an explicit flow name when the legacy spec *authored* one (flow
    specs name their flows). Standard/materialized_view specs never named their
    flow — the framework derived ``f_{sourceViewName}`` at runtime — so those
    migrate to a bare view name and let the transformer derive the same name.
    That keeps the SDP flow (and its streaming checkpoint) identical without
    inventing a name the author never wrote.
    """
    if flow is None or flow == _flow_name(view):
        return view
    return {"view": view, "flow": flow}


def _is_historical_snapshot(spec: Dict) -> bool:
    """True for a snapshot spec that reads files/tables directly (no source node)."""
    cs = _get(spec, "cdcSnapshotSettings", "cdc_snapshot_settings") or {}
    stype = cs.get("snapshotType") or cs.get("snapshot_type")
    return stype == "historical"


# ─── Standard Spec Migration ─────────────────────────────────────────────────

def _migrate_standard(spec: Dict) -> Dict:
    """Convert a standard spec to nodespec."""
    target_config, target_type = _build_spec_target(spec)

    nodes: List[Dict] = []
    # Historical snapshots have no source node — the snapshot reads its
    # files/table directly via cdc_snapshot_settings.source, and the target
    # takes no sources.
    if not _is_historical_snapshot(spec) and (spec.get("sourceViewName") or spec.get("sourceDetails")):
        source_id = spec.get("sourceViewName") or "v_source"
        nodes.append(_build_source_node(source_id, spec.get("sourceType", "delta"),
                                        spec.get("sourceDetails", {}), spec.get("mode", "stream")))
        target_config["sources"] = [_source_entry(source_id)]

    target_name = target_config.get("table") or target_config.get("name") or "output"
    target_node: Dict[str, Any] = {"name": f"target_{target_name}", "node_type": "target"}
    if target_type != "delta":
        target_node["target_type"] = target_type
    target_node["config"] = target_config
    nodes.append(target_node)

    return _result_envelope(spec, nodes)


def _build_source_node(name: str, source_type: str, source_details: Dict, mode: str) -> Dict:
    """Build a nodespec source node (snake_case) from camelCase source details."""
    source_type = _map_source_type(source_type)

    config: Dict[str, Any] = {}
    if mode:
        config["mode"] = mode
    if source_type == "delta_join":
        # delta_join sources carry `sources`/`joins` arrays (deeply nested).
        config.update(_deep_snake(source_details))
    else:
        config.update(_convert_source_details(source_details))

    node: Dict[str, Any] = {"name": name, "node_type": "source", "source_type": source_type}
    if config:
        node["config"] = config
    return node


def _build_sql_transformation_node(name: str, source_details: Dict) -> Dict:
    """Build a nodespec SQL transformation node from a flow view's SQL details.

    A SQL view inside a flow reshapes upstream views; in nodespec it is a
    transformation node (node_type=transformation, transformation_type=sql), not
    a source. The transformer registers every sibling source into the
    transformation's flow so SDP can resolve the views its SQL references.
    """
    config: Dict[str, Any] = {}
    sql_statement = _get(source_details, "sqlStatement", "sql_statement")
    sql_path = _get(source_details, "sqlPath", "sql_path")
    if sql_statement is not None:
        config["sql_statement"] = sql_statement
    elif sql_path is not None:
        config["sql_path"] = sql_path
    node: Dict[str, Any] = {"name": name, "node_type": "transformation", "transformation_type": "sql"}
    if config:
        node["config"] = config
    return node


def _build_spec_target(spec: Dict) -> Tuple[Dict, str]:
    """Build the spec-level target config (delta or sink). Returns (config, target_type)."""
    target_details = spec.get("targetDetails", {})
    target_format = spec.get("targetFormat", "delta")

    if target_format != "delta":
        # Sink target: map the known sink fields; deep-convert the nested blobs.
        config = {}
        if "name" in target_details:
            config["name"] = target_details["name"]
        if "type" in target_details:
            config["sink_type"] = target_details["type"]
        if "config" in target_details:
            config["sink_config"] = _deep_snake(target_details["config"])
        sink_options = _get(target_details, "sinkOptions", "sink_options")
        if sink_options is not None:
            config["sink_options"] = _deep_snake(sink_options)
    else:
        config = _rename(target_details, _TARGET_DETAIL_MAP)
        _fix_config_flags(config)

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

        # Staging tables -> target nodes (sources filled while processing flows).
        for stg_name, stg_config in staging_tables.items():
            target_id = f"target_{stg_name}"
            if target_id in node_ids:
                continue
            node_ids.add(target_id)
            config = _build_target_config_from_staging(stg_name, stg_config)
            config["sources"] = []
            nodes.append({"name": target_id, "node_type": "target", "config": config})

        for flow_name, flow_config in flows.items():
            flow_type = flow_config.get("flowType")
            flow_details = flow_config.get("flowDetails", {})
            target_table = flow_details.get("targetTable")
            views = flow_config.get("views", {})

            source_node_id = None
            declared_source_view = flow_details.get("sourceView")

            # Views -> source (or transformation) nodes. A SQL view reshapes
            # upstream views and must be a *transformation* node — the
            # transformer then pulls every sibling source into its flow so SDP
            # can resolve references like STREAM(live.<sibling>). Modeling it as
            # a SQL *source* would orphan those sibling views
            # (TABLE_OR_VIEW_NOT_FOUND at runtime).
            for view_name, view_config in views.items():
                if view_name not in node_ids:
                    node_ids.add(view_name)
                    if view_config.get("sourceType") == "sql":
                        nodes.append(_build_sql_transformation_node(
                            view_name, view_config.get("sourceDetails", {})))
                    else:
                        nodes.append(_build_source_node(
                            view_name,
                            view_config.get("sourceType", "delta"),
                            view_config.get("sourceDetails", {}),
                            view_config.get("mode", "stream"),
                        ))
                # Wire the flow's declared sourceView as the input (the SQL
                # transformation, when present); otherwise the sole/last view.
                if declared_source_view == view_name or source_node_id is None:
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
            # spec) named directly — i.e. the flow has no matching `views` entry
            # for it — legacy read that table straight into the flow with no
            # intermediate view (FlowMerge/append pass the bare sourceView name
            # to the reader). Nodespec models this with an "internal" source node
            # with `as_view: false`, keeping it out of a standalone SDP view so
            # the direct ST->ST chain flows straight into the next target and the
            # lineage matches legacy exactly. `as_view` defaults to true, so a
            # view-backed read (append_view, which has a `views` block) is never
            # emitted with as_view at all — only this direct-read case sets false.
            #
            # We deliberately do NOT add cdf_enabled here: legacy read this table
            # as a plain stream (the staging tables carry no enableChangeDataFeed
            # unless the source spec declared it), and CDF is only used where the
            # legacy spec explicitly declared `cdfEnabled` on a view (which comes
            # through as its own explicit source node). The migration's job is to
            # replicate legacy faithfully; a full-refresh (`DLT REFRESH`) is
            # tolerated because the flow name is preserved, so the stream keeps
            # its checkpoint and never rewinds across the refresh boundary.
            if not source_node_id and flow_details.get("sourceView"):
                source_view = flow_details["sourceView"]
                staging_key = _table_key(source_view)
                if staging_key in staging_table_names:
                    internal_id = source_view if source_view.startswith("v_") else f"v_{staging_key}"
                    if internal_id not in node_ids:
                        node_ids.add(internal_id)
                        internal_config: Dict[str, Any] = {
                            "mode": "stream", "table": staging_key, "as_view": False,
                        }
                        nodes.append({
                            "name": internal_id,
                            "node_type": "source",
                            "source_type": "delta",
                            "config": internal_config,
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
                target_node["config"].setdefault("sources", []).append(
                    _source_entry(source_node_id, flow_name))
            else:
                # Main (spec-level) target (delta or sink).
                target_id = f"target_{target_key}"
                if target_id not in node_ids:
                    node_ids.add(target_id)
                    main_config, target_type = _build_spec_target(spec)
                    if flow_details.get("once"):
                        main_config["once"] = True
                    main_config["sources"] = [_source_entry(source_node_id, flow_name)]
                    main_node: Dict[str, Any] = {"name": target_id, "node_type": "target"}
                    if target_type != "delta":
                        main_node["target_type"] = target_type
                    main_node["config"] = main_config
                    nodes.append(main_node)

    # Drop placeholder empty sources lists.
    for node in nodes:
        config = node.get("config", {})
        if config.get("sources") == []:
            del config["sources"]

    return _result_envelope(spec, nodes)


def _build_target_config_from_staging(table_name: str, stg_config: Dict) -> Dict:
    """Build a target config from a flow staging-table definition."""
    # Settings handled by _add_target_settings — dropped here so they aren't
    # copied verbatim, then re-added in the correct nested snake_case form.
    _settings_keys = (
        "cdcSettings", "cdc_settings", "cdcApplyChanges", "cdc_apply_changes",
        "cdcSnapshotSettings", "cdc_snapshot_settings",
        "dataQualityExpectationsEnabled", "data_quality_expectations_enabled",
        "dataQualityExpectationsPath", "data_quality_expectations_path",
        "quarantineMode", "quarantine_mode",
        "quarantineTargetDetails", "quarantine_target_details",
        "tableMigrationDetails", "table_migration_details",
    )
    config: Dict[str, Any] = {"table": table_name}
    config.update(_rename(
        {k: v for k, v in stg_config.items() if k != "type" and k not in _settings_keys},
        _TARGET_DETAIL_MAP,
    ))
    _fix_config_flags(config)
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

        # tableDetails is no longer a nested block — its fields (comment,
        # spark_conf, config_flags, private, ...) live directly on the config.
        table_details = _get(mv_config, "tableDetails", "table_details")
        if table_details:
            target_config.update(_rename(table_details, _TARGET_DETAIL_MAP))
            _fix_config_flags(target_config)

        _add_target_settings(target_config, mv_config)

        # MV source views are no longer inlined on the target: emit a source node
        # and chain it into the MV via `sources`.
        source_view = _get(mv_config, "sourceView", "source_view")
        if isinstance(source_view, dict) and source_view:
            source_id = (source_view.get("sourceViewName")
                         or source_view.get("source_view_name")
                         or f"v_source_{mv_name}")
            src_node = _build_source_node(
                source_id,
                source_view.get("sourceType") or source_view.get("source_type", "delta"),
                source_view.get("sourceDetails") or source_view.get("source_details", {}),
                "batch",
            )
            # A materialized view reads its source in batch; CDF is a streaming
            # concept. The runtime applies a `_change_type` filter whenever
            # cdf_enabled is set, which fails on a batch read (the column does
            # not exist), so strip CDF settings from an MV source node.
            src_cfg = src_node.get("config", {})
            src_cfg.pop("cdf_enabled", None)
            src_cfg.pop("cdf_change_type_override", None)
            nodes.append(src_node)
            target_config["sources"] = [_source_entry(source_id)]

        nodes.append({"name": f"target_{mv_name}", "node_type": "target", "config": target_config})

    return _result_envelope(spec, nodes)


# ─── Template specs ───────────────────────────────────────────────────────────

def is_template_instantiation_spec(spec: Dict) -> bool:
    """True for {template: <name>, parameter_sets: [...]} main spec files."""
    return (
        isinstance(spec, dict)
        and isinstance(spec.get("template"), str)
        and ("parameter_sets" in spec or "parameterSets" in spec)
    )


def migrate_template_instantiation_spec(spec: Dict) -> Dict:
    """Snake-case the framework key on a template instantiation spec.

    Only the framework-owned ``parameterSets`` key is renamed to
    ``parameter_sets``. The parameter sets themselves are user input (the values
    passed into the template) and are copied through verbatim — their keys are
    the template's parameter names and must not be touched, even when the author
    wrote them in camelCase.
    """
    result: Dict[str, Any] = {}
    for key, value in spec.items():
        if key in ("parameterSets", "parameter_sets"):
            result["parameter_sets"] = value
        else:
            result[key] = value
    return result


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

# Main spec files end in _main.json / _main.yaml / _main.yml.
_MAIN_SPEC_SUFFIXES = ("_main.json", "_main.yaml", "_main.yml")
_SPEC_EXTENSIONS = (".json", ".yaml", ".yml")


def _is_dataflowspec_main(path: Path) -> bool:
    """True for dataflow main spec files (JSON or YAML) under a dataflowspec directory."""
    return (
        path.name.endswith(_MAIN_SPEC_SUFFIXES)
        and "dataflowspec" in path.parts
    )


def find_dataflowspec_main_files(root: Path) -> List[Path]:
    """Return sorted paths to all *_main.{json,yaml,yml} files under dataflowspec/."""
    return sorted(
        path
        for path in root.rglob("*_main.*")
        if _is_dataflowspec_main(path)
    )


def find_template_definition_files(root: Path) -> List[Path]:
    """Return sorted template definition files (JSON or YAML) under templates/."""
    return sorted(
        path
        for path in root.rglob("*")
        if "templates" in path.parts
        and path.is_file()
        and path.suffix.lower() in _SPEC_EXTENSIONS
    )


# Spec files may be JSON or YAML; the migration logic is format-agnostic (it
# works on plain dicts), so only load/write is format-aware. The output keeps
# the same format as the input so a YAML bundle stays YAML.
_YAML_SUFFIXES = (".yaml", ".yml")


def _is_yaml(path: str) -> bool:
    return path.lower().endswith(_YAML_SUFFIXES)


def _import_yaml():
    """Import PyYAML lazily so JSON-only migrations don't require it installed."""
    try:
        import yaml  # noqa: PLC0415
        return yaml
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "PyYAML is required to migrate YAML specs. Install it with `pip install pyyaml`."
        ) from exc


def _load_spec_file(path: str) -> Dict:
    """Load a spec file as a dict, detecting JSON vs YAML from the extension."""
    with open(path, "r", encoding="utf-8") as f:
        if _is_yaml(path):
            return _import_yaml().safe_load(f)
        return json.load(f)


def _write_spec_file(path: str, data: Dict) -> None:
    """Write a spec dict back in the format implied by the path's extension."""
    with open(path, "w", encoding="utf-8") as f:
        if _is_yaml(path):
            _import_yaml().safe_dump(data, f, sort_keys=False, default_flow_style=False)
        else:
            json.dump(data, f, indent=4)
            f.write("\n")


def _ensure_output_file(input_path: str, output_path: str, data: Optional[Dict] = None) -> str:
    """Write the converted spec (in the input's format) or copy the source file."""
    if output_path is None:
        output_path = input_path
    if data is not None:
        _write_spec_file(output_path, data)
    elif output_path != input_path:
        shutil.copy2(input_path, output_path)
    return output_path


def process_file(input_path: str, output_path: Optional[str] = None) -> Tuple[str, str]:
    """Process a single dataflow main spec file.

    Returns:
        Tuple of (output path, status): ``converted``, ``skipped``, or ``unchanged``.
    """
    spec = _load_spec_file(input_path)

    if is_template_instantiation_spec(spec):
        if "parameterSets" in spec:
            result = migrate_template_instantiation_spec(spec)
            out = _ensure_output_file(input_path, output_path or input_path, result)
            return out, "converted"
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
    defn = _load_spec_file(input_path)

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
            spec = _load_spec_file(str(spec_path))
            if is_template_instantiation_spec(spec) and "parameterSets" not in spec:
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
            defn = _load_spec_file(str(template_path))
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
        stem, ext = os.path.splitext(args.input)
        output = args.output or f"{stem}_nodespec{ext}"
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
                if fname.endswith(_MAIN_SPEC_SUFFIXES):
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
