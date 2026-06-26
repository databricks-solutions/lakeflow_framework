"""
Nodester Spec Transformer

Converts a node-based dataflow spec into the Lakeflow Framework's flow-based
spec. A nodester spec is a graph of three node kinds:

    source  ->  transformation  ->  target

- source nodes        become views (or direct table references for internal tables)
- transformation nodes become SQL/Python views
- target nodes        become the spec target table or staging tables, each
                      carrying its own settings (CDC, data quality, quarantine, ...)

How nodes connect:
- A target node lists what feeds it in `config.input`. Each input is either a
  view/node name (string) or `{"view": ..., "flow": ...}` to set the flow name.
- Source and transformation nodes reference their upstream inside their own
  definition (for example a transform's SQL names the view it reads).

Spec target selection:
- The backend needs one `targetDetails`. It is auto-selected as the terminal
  target (a target not consumed by any other node). The remaining targets become
  staging tables. With multiple terminal targets the last one is used.

Materialized views:
- Targets with `table_type: "mv"` each become their own flow spec, so a spec with
  both streaming and MV targets returns a list of flow specs.

Casing: nodester input is snake_case; the emitted flow spec is the backend's
camelCase. `_rename_keys` / `_to_backend_keys` do that translation.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Set, Union

from .base import BaseSpecTransformer
from dataflow.enums import FlowType, Mode, TableType, TargetType


# Explicit snake_case -> backend key map for nested blobs that are copied
# wholesale (CDC snapshot settings, table migration, sink config). The backend
# mixes camelCase and snake_case, so only the keys listed here are renamed.
_NODESTER_TO_BACKEND_KEYS = {
    # CDC snapshot settings
    "snapshot_type": "snapshotType",
    "source_type": "sourceType",
    "version_type": "versionType",
    "version_column": "versionColumn",
    "starting_version": "startingVersion",
    "datetime_format": "datetimeFormat",
    "reader_options": "readerOptions",
    "schema_path": "schemaPath",
    "select_exp": "selectExp",
    "deduplicate_mode": "deduplicateMode",
    # Table migration details
    "catalog_type": "catalogType",
    "auto_starting_versions_enabled": "autoStartingVersionsEnabled",
    "source_details": "sourceDetails",
    "table_name": "tableName",
    # Source nested fields / sink config
    "function_path": "functionPath",
    "python_module": "pythonModule",
    "sql_path": "sqlPath",
    "sql_statement": "sqlStatement",
    "table_properties": "tableProperties",
}


def _to_backend_keys(obj: Any) -> Any:
    """Recursively rename known snake_case keys to their backend equivalents."""
    if isinstance(obj, dict):
        return {_NODESTER_TO_BACKEND_KEYS.get(k, k): _to_backend_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_backend_keys(i) for i in obj]
    return obj


def _rename_keys(source: Dict, mapping: Dict[str, str]) -> Dict:
    """Copy keys present in `source` into a new dict, renaming src -> dst."""
    return {dst: source[src] for src, dst in mapping.items() if src in source}


class NodesterSpecTransformer(BaseSpecTransformer):
    """Transform a nodester node-graph spec into a flow spec (or list of them)."""

    # Nodester warns about inline source transformations at the node level (where
    # source and transformation nodes are distinguishable), so the base class
    # should not re-derive that warning from the produced flow spec.
    WARN_INLINE_SOURCE_TRANSFORMATIONS_FROM_OUTPUT = False

    FLOW_GROUP_ID = "nodester_main"
    FLOW_PREFIX = "f_"
    VIEW_PREFIX = "v_"

    SOURCE = "source"
    TRANSFORMATION = "transformation"
    TARGET = "target"

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def _process_spec(self, spec_data: Dict) -> Union[Dict, List[Dict]]:
        """Transform a nodester spec into one flow spec, or a list when it
        produces both streaming-table and materialized-view targets."""
        nodes = spec_data.get("nodes", [])
        if not nodes:
            raise ValueError("Nodester spec must contain at least one node")

        sources, transforms, targets = self._categorize_nodes(nodes)
        self._warn_inline_source_transformations(sources)
        self._validate_node_graph(sources, targets, nodes)

        mv_targets = [t for t in targets if self._is_mv(t)]
        st_targets = [t for t in targets if not self._is_mv(t)]

        specs: List[Dict] = []
        if st_targets:
            specs.append(self._build_streaming_spec(spec_data, st_targets, sources, nodes))
        if mv_targets:
            specs.extend(self._build_mv_specs(spec_data, mv_targets, sources, nodes))

        if not specs:
            raise ValueError("Nodester spec must contain at least one target node")
        return specs if len(specs) > 1 else specs[0]

    @staticmethod
    def _is_mv(target: Dict) -> bool:
        return target.get("config", {}).get("table_type") == "mv"

    # ------------------------------------------------------------------ #
    # Node organisation, validation, warnings
    # ------------------------------------------------------------------ #
    def _categorize_nodes(self, nodes: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Split nodes into (sources, transformations, targets)."""
        sources, transforms, targets = [], [], []
        buckets = {self.SOURCE: sources, self.TRANSFORMATION: transforms, self.TARGET: targets}
        for node in nodes:
            bucket = buckets.get(node.get("node_type", "").lower())
            if bucket is None:
                self.logger.warning(
                    f"Unknown node type '{node.get('node_type')}' for node '{node.get('name')}'"
                )
            else:
                bucket.append(node)
        return sources, transforms, targets

    def _warn_inline_source_transformations(self, source_nodes: List[Dict]) -> None:
        """Warn when a source node embeds SQL/Python transformation logic.

        Declaring a SQL or Python transformation directly on a source node (via
        ``source_type: "sql"`` / ``"python"``) is still supported for backward
        compatibility but discouraged: it hides transformation logic inside the
        data-origin node. The recommended pattern is a plain source node chained
        into a dedicated transformation node.
        """
        for node in source_nodes:
            source_type = node.get("source_type", "delta")
            if source_type in ("sql", "python"):
                self.logger.warning(
                    "Source node '%s' defines an inline %s transformation "
                    "(source_type: '%s'). This is still supported but "
                    "discouraged and may not be supported in a future release. "
                    "Define a source node and chain a dedicated transformation "
                    "node off it instead.",
                    node.get("name"), source_type, source_type,
                )

    def _validate_node_graph(self, sources: List[Dict], targets: List[Dict], all_nodes: List[Dict]) -> None:
        """Validate references, the removed MV source_view, and source presence."""
        node_names = {node.get("name") for node in all_nodes}

        for target in targets:
            for view in self._input_views(target):
                if view not in node_names:
                    raise ValueError(
                        f"Node '{target.get('name')}' references non-existent input '{view}'"
                    )

        # Inline source views on MV targets are no longer supported: authors must
        # declare a source node and chain it into the MV target via `input`.
        for target in targets:
            if self._is_mv(target) and "source_view" in target.get("config", {}):
                raise ValueError(
                    f"Materialized view target '{target.get('name')}' defines an inline "
                    "'source_view'. This is no longer supported. Declare a source node and "
                    "chain it into the materialized view target via its 'input' array instead."
                )

        if not targets:
            raise ValueError("Nodester spec must contain at least one target node")

        # A source node is unnecessary only when every target reads its data
        # without one: an MV defined by inline SQL, or a snapshot CDC target.
        all_mv_inline_sql = all(
            self._is_mv(t) and (t["config"].get("sql_path") or t["config"].get("sql_statement"))
            for t in targets
        )
        all_snapshot = all(t.get("config", {}).get("cdc_snapshot_settings") for t in targets)
        if not sources and not (all_mv_inline_sql or all_snapshot):
            raise ValueError("Nodester spec must contain at least one source node")

    # ------------------------------------------------------------------ #
    # input handling
    # ------------------------------------------------------------------ #
    def _normalize_inputs(self, inputs: List) -> List[Tuple[Optional[str], str]]:
        """Normalize a target's ``input`` list into (flow_name, view_name) pairs.

        Each item is either a string (upstream node name; flow name auto-generated)
        or ``{"view": ..., "flow": ...}`` where ``flow`` defines the SDP flow name.
        Defining the flow name keeps it stable across edits, which matters because
        renaming a flow forces a full refresh in SDP.
        """
        pairs: List[Tuple[Optional[str], str]] = []
        for item in inputs or []:
            if isinstance(item, dict):
                if item.get("view"):
                    pairs.append((item.get("flow"), item["view"]))
            else:
                pairs.append((None, item))
        return pairs

    def _input_views(self, node: Dict) -> List[str]:
        """Return the upstream view/node names a node's ``input`` references."""
        return [view for _, view in self._normalize_inputs(node.get("config", {}).get("input", []))]

    # ------------------------------------------------------------------ #
    # Streaming-table targets
    # ------------------------------------------------------------------ #
    def _build_streaming_spec(
        self, spec_data: Dict, targets: List[Dict], sources: List[Dict], all_nodes: List[Dict]
    ) -> Dict:
        """Build a single flow spec for the streaming-table targets."""
        internal_sources = self._identify_internal_sources(sources, targets)
        spec_target, other_targets = self._select_spec_target(targets, sources, all_nodes)
        return self._build_flow_spec(spec_data, spec_target, other_targets, all_nodes, internal_sources)

    def _select_spec_target(
        self, targets: List[Dict], sources: List[Dict], all_nodes: List[Dict]
    ) -> Tuple[Dict, List[Dict]]:
        """Pick the terminal target as the spec target; the rest are staging."""
        if len(targets) == 1:
            return targets[0], []

        consumed = {view for node in all_nodes for view in self._input_views(node)}
        source_tables = {s.get("config", {}).get("table") for s in sources}
        source_tables.discard(None)

        terminal, other = [], []
        for target in targets:
            table = target.get("config", {}).get("table")
            is_consumed = target.get("name") in consumed or (table in source_tables)
            (other if is_consumed else terminal).append(target)

        if not terminal:
            raise ValueError(
                "Could not determine spec target: all target nodes are consumed by other nodes"
            )
        if len(terminal) > 1:
            self.logger.warning(
                "Multiple terminal targets found %s. Using last target '%s' as spec target.",
                [t.get("name") for t in terminal], terminal[-1].get("name"),
            )
        return terminal[-1], other + terminal[:-1]

    def _build_flow_spec(
        self, spec_data: Dict, spec_target: Dict, other_targets: List[Dict],
        all_nodes: List[Dict], internal_sources: Dict[str, str],
    ) -> Dict:
        """Assemble the flow spec for the streaming targets (camelCase output)."""
        node_lookup = {node.get("name"): node for node in all_nodes}
        config = spec_target.get("config", {})
        target_format = spec_target.get("target_type", "delta")

        if target_format == "delta":
            target_details = self._build_target_details(config)
        else:
            target_details = self._build_sink_target_details(config)

        cdc_settings = config.get("cdc_settings") or config.get("cdc_apply_changes")
        cdc_snapshot_settings = config.get("cdc_snapshot_settings")
        has_cdc = cdc_settings is not None or cdc_snapshot_settings is not None

        flow_spec = {
            "dataFlowId": spec_data.get("dataFlowId"),
            "dataFlowGroup": spec_data.get("dataFlowGroup"),
            "dataFlowType": spec_data.get("dataFlowType"),
            "targetFormat": target_format,
            "targetDetails": target_details,
            "tags": spec_data.get("tags", {}),
            "features": spec_data.get("features", {}),
        }
        if spec_data.get("dataFlowVersion"):
            flow_spec["dataFlowVersion"] = spec_data["dataFlowVersion"]
        if cdc_settings:
            flow_spec["cdcSettings"] = cdc_settings
        if cdc_snapshot_settings:
            flow_spec["cdcSnapshotSettings"] = _to_backend_keys(cdc_snapshot_settings)

        flow_spec["dataQualityExpectationsEnabled"] = config.get("data_quality_expectations_enabled", False)
        if config.get("data_quality_expectations_path"):
            flow_spec["dataQualityExpectationsPath"] = config["data_quality_expectations_path"]
        if config.get("quarantine_mode"):
            flow_spec["quarantineMode"] = config["quarantine_mode"]
        if config.get("quarantine_target_details"):
            flow_spec["quarantineTargetDetails"] = config["quarantine_target_details"]
        if config.get("table_migration_details"):
            flow_spec["tableMigrationDetails"] = _to_backend_keys(config["table_migration_details"])

        flow_spec["flowGroups"] = [
            self._build_flow_group(spec_target, other_targets, node_lookup, has_cdc, internal_sources)
        ]
        return flow_spec

    def _build_target_details(self, config: Dict) -> Dict:
        """Build targetDetails for a delta (streaming table) target."""
        target_details = {"table": config.get("table"), "type": TableType.STREAMING}
        target_details.update(_rename_keys(config, {
            "database": "database", "schema_path": "schemaPath",
            "table_properties": "tableProperties", "path": "path",
            "partition_columns": "partitionColumns",
            "cluster_by_columns": "clusterByColumns", "cluster_by_auto": "clusterByAuto",
            "comment": "comment", "spark_conf": "sparkConf",
            "row_filter": "rowFilter", "config_flags": "configFlags",
        }))
        return target_details

    def _build_sink_target_details(self, config: Dict) -> Dict:
        """Build targetDetails for a sink target (delta_sink / foreach_batch / custom)."""
        target_details = _rename_keys(config, {"name": "name", "sink_type": "type", "sink_options": "sinkOptions"})
        if "sink_config" in config:
            target_details["config"] = _to_backend_keys(config["sink_config"])
        return target_details

    def _build_flow_group(
        self, spec_target: Dict, other_targets: List[Dict], node_lookup: Dict[str, Dict],
        has_cdc: bool, internal_sources: Dict[str, str],
    ) -> Dict:
        """Build the single flow group: staging tables plus one flow per input."""
        flow_group = {"flowGroupId": self.FLOW_GROUP_ID, "flows": {}}

        staging_tables = self._build_staging_tables(other_targets)
        if staging_tables:
            flow_group["stagingTables"] = staging_tables

        # Views already attached to a flow, so we don't redefine them (SDP errors
        # on "Cannot redefine"). Shared across all flows in the group.
        registered_views: Set[str] = set()

        # Group targets by output table, preserving first-seen order.
        table_to_targets: Dict[str, List[Dict]] = defaultdict(list)
        for target in other_targets + [spec_target]:
            config = target.get("config", {})
            table = config.get("table") or config.get("name")
            if table:
                table_to_targets[table].append(target)

        flow_counter = 0
        for table_name, targets in table_to_targets.items():
            for target in targets:
                flow_counter = self._add_target_flows(
                    flow_group, target, table_name, spec_target, node_lookup,
                    has_cdc, internal_sources, registered_views, flow_counter,
                )
        return flow_group

    def _build_staging_tables(self, other_targets: List[Dict]) -> Dict:
        """Build the stagingTables map from the non-spec targets."""
        staging: Dict[str, Dict] = {}
        for target in other_targets:
            config = target.get("config", {})
            table = config.get("table")
            if not table or table in staging:
                continue

            entry = {"type": "ST"}
            entry.update(_rename_keys(config, {
                "database": "database", "schema_path": "schemaPath",
                "table_properties": "tableProperties",
                "cluster_by_columns": "clusterByColumns", "cluster_by_auto": "clusterByAuto",
                "partition_columns": "partitionColumns", "config_flags": "configFlags",
            }))

            cdc = config.get("cdc_settings") or config.get("cdc_apply_changes")
            if cdc:
                entry["cdcSettings"] = cdc
            if config.get("cdc_snapshot_settings"):
                entry["cdcSnapshotSettings"] = _to_backend_keys(config["cdc_snapshot_settings"])
            if config.get("data_quality_expectations_enabled"):
                entry["dataQualityExpectationsEnabled"] = config["data_quality_expectations_enabled"]
            if config.get("data_quality_expectations_path"):
                entry["dataQualityExpectationsPath"] = config["data_quality_expectations_path"]
            if config.get("quarantine_mode"):
                entry["quarantineMode"] = config["quarantine_mode"]
            if config.get("quarantine_target_details"):
                entry["quarantineTargetDetails"] = config["quarantine_target_details"]

            staging[table] = entry
        return staging

    def _add_target_flows(
        self, flow_group: Dict, target: Dict, table_name: str, spec_target: Dict,
        node_lookup: Dict[str, Dict], has_cdc: bool, internal_sources: Dict[str, str],
        registered_views: Set[str], flow_counter: int,
    ) -> int:
        """Add the flow(s) that write into `target`. Returns the next flow counter."""
        config = target.get("config", {})
        target_name = target.get("name")
        inputs = self._normalize_inputs(config.get("input", []))
        enabled = target.get("enabled", True)

        # No inputs: only valid for snapshot CDC targets (the snapshot system
        # reads its source directly), otherwise there is nothing to write.
        if not inputs:
            if config.get("cdc_snapshot_settings"):
                flow_group["flows"][f"{self.FLOW_PREFIX}{target_name}_{flow_counter}"] = {
                    "flowType": FlowType.MERGE,
                    "flowDetails": {"targetTable": table_name},
                    "enabled": enabled,
                }
                flow_counter += 1
            else:
                self.logger.warning(f"Target '{target_name}' has no inputs, skipping")
            return flow_counter

        target_cdc = config.get("cdc_settings") or config.get("cdc_apply_changes")
        for explicit_flow, view in inputs:
            input_node = node_lookup.get(view, {})
            is_sql_source = (
                input_node.get("node_type", "").lower() == self.SOURCE
                and input_node.get("source_type") == "sql"
            )

            if target_cdc or (has_cdc and target is spec_target):
                flow_type = FlowType.MERGE
            elif is_sql_source:
                flow_type = FlowType.APPEND_SQL
            else:
                flow_type = FlowType.APPEND_VIEW

            flow_name = explicit_flow or f"{self.FLOW_PREFIX}{view}_{flow_counter}"
            flow_counter += 1

            if flow_type == FlowType.APPEND_SQL:
                flow = {
                    "flowType": flow_type,
                    "flowDetails": {"targetTable": table_name},
                    "enabled": enabled,
                }
                input_config = input_node.get("config", {})
                if input_config.get("sql_statement"):
                    flow["flowDetails"]["sqlStatement"] = input_config["sql_statement"]
                elif input_config.get("sql_path"):
                    flow["flowDetails"]["sqlPath"] = input_config["sql_path"]
            else:
                source_view, views = self._trace_inputs_to_views([view], node_lookup, internal_sources)
                if not source_view:
                    self.logger.warning(
                        f"Could not determine source view for target '{target_name}' input '{view}'"
                    )
                    continue
                flow = {
                    "flowType": flow_type,
                    "flowDetails": {"sourceView": source_view, "targetTable": table_name},
                    "enabled": enabled,
                }
                new_views = {k: v for k, v in views.items() if k not in registered_views}
                if new_views:
                    flow["views"] = new_views
                registered_views.update(views.keys())

            if config.get("once"):
                flow["flowDetails"]["once"] = True

            flow_group["flows"][flow_name] = flow
        return flow_counter

    # ------------------------------------------------------------------ #
    # Materialized-view targets
    # ------------------------------------------------------------------ #
    def _build_mv_specs(
        self, spec_data: Dict, mv_targets: List[Dict], sources: List[Dict], all_nodes: List[Dict]
    ) -> List[Dict]:
        """Build one flow spec per materialized-view target."""
        node_lookup = {node.get("name"): node for node in all_nodes}
        return [self._build_mv_spec(spec_data, t, sources, node_lookup) for t in mv_targets]

    def _build_mv_spec(
        self, spec_data: Dict, mv_target: Dict, sources: List[Dict], node_lookup: Dict[str, Dict]
    ) -> Dict:
        """Build the flow spec for a single materialized-view target."""
        config = mv_target.get("config", {})
        mv_name = config.get("table")

        target_details = {"table": mv_name, "type": TableType.MATERIALIZED_VIEW}
        target_details.update(_rename_keys(config, {
            "sql_path": "sqlPath", "sql_statement": "sqlStatement", "refresh_policy": "refreshPolicy",
        }))
        # table_details wins over the same key on config (back-compat fallback).
        detail_map = {
            "private": "private", "comment": "comment", "spark_conf": "sparkConf",
            "config_flags": "configFlags", "table_properties": "tableProperties",
            "cluster_by_columns": "clusterByColumns", "cluster_by_auto": "clusterByAuto",
        }
        target_details.update({
            **_rename_keys(config, detail_map),
            **_rename_keys(config.get("table_details", {}), detail_map),
        })

        flow_spec = {
            "dataFlowId": spec_data.get("dataFlowId"),
            "dataFlowGroup": spec_data.get("dataFlowGroup"),
            "dataFlowType": spec_data.get("dataFlowType"),
            "features": spec_data.get("features", {}),
            "targetFormat": TargetType.DELTA,
            "targetDetails": target_details,
            "dataQualityExpectationsEnabled": config.get("data_quality_expectations_enabled", False),
            "localPath": spec_data.get("localPath"),
        }
        if config.get("data_quality_expectations_path"):
            flow_spec["dataQualityExpectationsPath"] = config["data_quality_expectations_path"]
        if config.get("quarantine_mode"):
            flow_spec["quarantineMode"] = config["quarantine_mode"]
        if config.get("quarantine_target_details"):
            flow_spec["quarantineTargetDetails"] = config["quarantine_target_details"]

        flow_group = {"flowGroupId": self.FLOW_GROUP_ID, "flows": {}}
        inputs = self._normalize_inputs(config.get("input", []))
        if inputs:
            internal_sources = self._identify_internal_sources(sources, [mv_target])
            explicit_flow, view = inputs[0]
            source_view, views = self._trace_inputs_to_views([view], node_lookup, internal_sources)
            if source_view:
                target_details["sourceView"] = source_view
                flow = {"flowType": FlowType.MATERIALIZED_VIEW, "flowDetails": {"targetTable": mv_name}}
                if views:
                    for v in views.values():
                        v["mode"] = Mode.BATCH  # MVs use batch reads (spark.sql)
                    flow["views"] = views
                flow_group["flows"][explicit_flow or f"{self.FLOW_PREFIX}{mv_name}"] = flow

        flow_spec["flowGroups"] = [flow_group]
        return flow_spec

    # ------------------------------------------------------------------ #
    # Views and internal sources
    # ------------------------------------------------------------------ #
    def _identify_internal_sources(
        self, source_nodes: List[Dict], target_nodes: List[Dict]
    ) -> Dict[str, str]:
        """Map source-node name -> table for sources that read a table produced by
        a target in this same spec. Such sources reference the produced table
        directly instead of getting their own view."""
        target_tables = {
            t["config"]["table"]: (t["config"].get("database") or None)
            for t in target_nodes if t.get("config", {}).get("table")
        }

        internal: Dict[str, str] = {}
        for source in source_nodes:
            if source.get("source_type", "delta") != "delta":
                continue
            config = source.get("config", {})
            table = config.get("table", "")
            if table not in target_tables:
                continue
            source_db = config.get("database") or None
            target_db = target_tables[table]
            if not source_db or not target_db or source_db == target_db:
                internal[source.get("name")] = table
        return internal

    def _trace_inputs_to_views(
        self, inputs: List[str], node_lookup: Dict[str, Dict], internal_sources: Dict[str, str]
    ) -> Tuple[Optional[str], Dict]:
        """Resolve an input to its source view name and the views it needs.

        When the input is a transformation, every source node in the spec is also
        emitted as a view so SDP can resolve the references inside that
        transformation's SQL/Python.
        """
        views: Dict[str, Dict] = {}
        immediate_input = inputs[0] if inputs else None
        if not immediate_input:
            return None, views

        # An internal source reads the produced table directly: no view needed.
        if immediate_input in internal_sources:
            return internal_sources[immediate_input], views

        source_view_name = None
        references_transformation = False
        for node_name in inputs:
            if node_name in internal_sources:
                continue
            node = node_lookup.get(node_name)
            if not node:
                continue

            node_type = node.get("node_type", "").lower()
            view_name = node.get("output_view_name") or self._view_name(node_name)
            if node_type == self.SOURCE:
                views[view_name] = self._build_source_view(node)
            elif node_type == self.TRANSFORMATION:
                views[view_name] = self._build_transform_view(node, node_lookup)
                references_transformation = True
            else:
                continue
            if source_view_name is None and node_name == immediate_input:
                source_view_name = view_name

        # Register every source node so SDP can resolve the transformation's refs.
        if references_transformation:
            for name, node in node_lookup.items():
                if node.get("node_type", "").lower() != self.SOURCE:
                    continue
                view_name = node.get("output_view_name") or self._view_name(name)
                if view_name in views:
                    continue
                if name in internal_sources:
                    # Internal sources need database "live" so SDP resolves them
                    # within the pipeline context.
                    node = {**node, "config": {**node.get("config", {}), "database": "live"}}
                views[view_name] = self._build_source_view(node)

        if source_view_name is None:
            source_view_name = self._view_name(immediate_input)
        return source_view_name, views

    def _view_name(self, node_name: str) -> str:
        """View name for a node: the node name, prefixed with v_ if needed."""
        return node_name if node_name.startswith(self.VIEW_PREFIX) else f"{self.VIEW_PREFIX}{node_name}"

    def _build_source_view(self, node: Dict) -> Dict:
        """Build a view definition from a source node (camelCase output)."""
        source_type = node.get("source_type", "delta")
        config = node.get("config", {})
        details: Dict[str, Any] = {}

        if source_type == "delta":
            if "database" in config:
                details["database"] = config["database"]
            if "table" in config:
                details["table"] = config["table"]
            details["cdfEnabled"] = config.get("cdf_enabled", False)
            if "table_path" in config:
                details["tablePath"] = config["table_path"]
        elif source_type in ("cloudFiles", "batchFiles"):
            details.update(_rename_keys(config, {"path": "path", "reader_options": "readerOptions"}))
        elif source_type == "sql":
            details.update(self._first_present(config, [("sql_path", "sqlPath"), ("sql_statement", "sqlStatement")]))
        elif source_type == "python":
            details.update(self._first_present(config, [("function_path", "functionPath"), ("python_module", "pythonModule")]))
            details.update(_rename_keys(config, {"tokens": "tokens"}))
        elif source_type == "kafka":
            details.update(_rename_keys(config, {"reader_options": "readerOptions"}))

        details.update(_rename_keys(config, {
            "select_exp": "selectExp", "where_clause": "whereClause", "schema_path": "schemaPath",
            "starting_version_from_dlt_setup": "startingVersionFromDLTSetup",
            "cdf_change_type_override": "cdfChangeTypeOverride",
        }))

        # Backward compatibility: a source may carry an inline python transform
        # that post-processes the read DataFrame via apply_transform(df).
        python_transform = config.get("python_transform")
        if python_transform:
            mapped: Dict[str, Any] = {}
            if python_transform.get("function_path"):
                mapped["functionPath"] = python_transform["function_path"]
            elif python_transform.get("functionPath"):
                mapped["functionPath"] = python_transform["functionPath"]
            if python_transform.get("python_module"):
                mapped["module"] = python_transform["python_module"]
            elif python_transform.get("module"):
                mapped["module"] = python_transform["module"]
            if python_transform.get("tokens"):
                mapped["tokens"] = python_transform["tokens"]
            details["pythonTransform"] = mapped

        return {"mode": config.get("mode", Mode.STREAM), "sourceType": source_type, "sourceDetails": details}

    def _build_transform_view(self, node: Dict, node_lookup: Dict[str, Dict]) -> Dict:
        """Build a view definition from a transformation node (camelCase output)."""
        transform_type = node.get("transformation_type", "sql")
        config = node.get("config", {})

        if transform_type == "python":
            # A python transformation is its own view: it reads its upstream view
            # and applies apply_transform(df) via the framework's pythonTransform.
            # The upstream is inferred from the graph; SDP resolves the live ref.
            upstream_view, upstream_mode = self._infer_python_transform_upstream(node, node_lookup)
            python_transform: Dict[str, Any] = {}
            if config.get("function_path"):
                python_transform["functionPath"] = config["function_path"]
            elif config.get("python_module"):
                python_transform["module"] = config["python_module"]
            if config.get("tokens"):
                python_transform["tokens"] = config["tokens"]
            return {
                "mode": upstream_mode,
                "sourceType": "delta",
                "sourceDetails": {
                    "database": "live",
                    "table": upstream_view,
                    "pythonTransform": python_transform,
                },
            }

        # sql
        details = self._first_present(config, [("sql_path", "sqlPath"), ("sql_statement", "sqlStatement")])
        return {"mode": Mode.BATCH, "sourceType": "sql", "sourceDetails": details}

    def _infer_python_transform_upstream(self, node: Dict, node_lookup: Dict[str, Dict]) -> Tuple[str, str]:
        """Infer the upstream view a python transformation reads, plus its mode.

        Python transforms operate on a DataFrame, so (unlike SQL transforms) they
        carry no textual reference to their input. SDP resolves view dependencies
        automatically, so the upstream is inferred from the graph: the spec's
        source feeds the transform. With several sources the first is used and a
        warning is logged.
        """
        sources = [n for n in node_lookup.values()
                   if n.get("node_type", "").lower() == self.SOURCE]
        if not sources:
            self.logger.warning(
                "Python transformation '%s' has no upstream source node to read from.",
                node.get("name"),
            )
            return self._view_name(node.get("name")), Mode.STREAM
        if len(sources) > 1:
            self.logger.warning(
                "Python transformation '%s' has multiple upstream sources %s; reading from '%s'.",
                node.get("name"), [s.get("name") for s in sources], sources[0].get("name"),
            )
        upstream = sources[0]
        view = upstream.get("output_view_name") or self._view_name(upstream.get("name"))
        mode = upstream.get("config", {}).get("mode", Mode.STREAM)
        return view, mode

    @staticmethod
    def _first_present(config: Dict, candidates: List[Tuple[str, str]]) -> Dict:
        """Return {dst: config[src]} for the first (src, dst) whose src is set."""
        for src, dst in candidates:
            if src in config:
                return {dst: config[src]}
        return {}
