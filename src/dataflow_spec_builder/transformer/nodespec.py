"""
Nodespec Spec Transformer.

Converts a node-based dataflow spec (source -> transformation -> target nodes)
into the framework's flow-based spec. Sources/transformations become views;
targets become the spec target table or staging tables (each carrying its own
CDC / data quality / quarantine settings). The terminal target (not consumed by
another node) becomes the backend ``targetDetails``; the rest become staging
tables. ``table_type: "mv"`` targets each become their own flow spec, so a mixed
spec returns a list.

The snake_case -> camelCase translation is centralised: one global key map
(``_KEYS``) plus ``_camel`` (flat) / ``_deep_camel`` (nested blobs). Each builder
copies every config key that isn't "structural" (``_HANDLED`` — input, cdc_*,
quarantine_*, sink_*, ...); everything else is passthrough table/source detail.
"""
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Set, Union

from .base import BaseSpecTransformer
from dataflow.enums import FlowType, Mode, TableType, TargetType


# The single snake_case -> camelCase map. Identity keys (database, table, path,
# comment, name, tokens, private, ...) need no entry. Used both for flat detail
# conversion and recursive conversion of nested blobs (snapshot CDC, table
# migration, sink config).
_KEYS = {
    "schema_path": "schemaPath", "table_properties": "tableProperties",
    "partition_columns": "partitionColumns", "cluster_by_columns": "clusterByColumns",
    "cluster_by_auto": "clusterByAuto", "spark_conf": "sparkConf", "row_filter": "rowFilter",
    "config_flags": "configFlags", "cdf_enabled": "cdfEnabled", "table_path": "tablePath",
    "reader_options": "readerOptions", "sql_path": "sqlPath", "sql_statement": "sqlStatement",
    "function_path": "functionPath", "python_module": "pythonModule", "select_exp": "selectExp",
    "where_clause": "whereClause", "refresh_policy": "refreshPolicy",
    "starting_version_from_dlt_setup": "startingVersionFromDLTSetup",
    "cdf_change_type_override": "cdfChangeTypeOverride",
    # nested snapshot-CDC / table-migration keys
    "snapshot_type": "snapshotType", "source_type": "sourceType", "version_type": "versionType",
    "version_column": "versionColumn", "starting_version": "startingVersion",
    "datetime_format": "datetimeFormat", "deduplicate_mode": "deduplicateMode",
    "catalog_type": "catalogType", "auto_starting_versions_enabled": "autoStartingVersionsEnabled",
    "source_details": "sourceDetails", "table_name": "tableName",
}

# Keys a target config handles specially, so they are NOT copied into details.
_HANDLED = {
    "input", "table", "table_type", "enabled", "once", "name",
    "cdc_settings", "cdc_snapshot_settings",
    "data_quality_expectations_enabled", "data_quality_expectations_path",
    "quarantine_mode", "quarantine_target_details", "table_migration_details",
    "sink_type", "sink_config", "sink_options", "table_details", "source_view",
}


def _camel(cfg: Dict, drop: Set[str] = frozenset()) -> Dict:
    """Flat snake->camel rename of top-level keys (values copied verbatim)."""
    return {_KEYS.get(k, k): v for k, v in cfg.items() if k not in drop}


def _deep_camel(obj: Any) -> Any:
    """Recursive snake->camel for nested blobs (snapshot CDC, migration, sink config)."""
    if isinstance(obj, dict):
        return {_KEYS.get(k, k): _deep_camel(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_camel(i) for i in obj]
    return obj


def _first(cfg: Dict, *keys: str) -> Dict:
    """{camel(key): value} for the first present snake key (e.g. sql_path|sql_statement)."""
    for k in keys:
        if k in cfg:
            return {_KEYS.get(k, k): cfg[k]}
    return {}


class NodespecSpecTransformer(BaseSpecTransformer):
    """Transform a nodespec node-graph spec into a flow spec (or list of them)."""

    WARN_INLINE_SOURCE_TRANSFORMATIONS_FROM_OUTPUT = False
    FLOW_GROUP_ID = "nodespec_main"
    FLOW_PREFIX = "f_"
    VIEW_PREFIX = "v_"
    SOURCE, TRANSFORMATION, TARGET = "source", "transformation", "target"

    def _process_spec(self, spec_data: Dict) -> Union[Dict, List[Dict]]:
        """Transform a nodespec spec into one flow spec, or a list (streaming + MV)."""
        nodes = spec_data.get("nodes", [])
        if not nodes:
            raise ValueError("Nodespec spec must contain at least one node")

        sources = [n for n in nodes if n.get("node_type", "").lower() == self.SOURCE]
        targets = [n for n in nodes if n.get("node_type", "").lower() == self.TARGET]
        self._warn_inline_sources(sources)
        self._validate(sources, targets, nodes)

        self.lookup = {n.get("name"): n for n in nodes}
        st = [t for t in targets if not self._is_mv(t)]
        mv = [t for t in targets if self._is_mv(t)]

        specs: List[Dict] = []
        if st:
            self.internal = self._internal_sources(sources, st)
            spec_target, others = self._select_spec_target(st, sources, nodes)
            specs.append(self._streaming_spec(spec_data, spec_target, others))
        for target in mv:
            specs.append(self._mv_spec(spec_data, target, sources))

        if not specs:
            raise ValueError("Nodespec spec must contain at least one target node")
        return specs if len(specs) > 1 else specs[0]

    @staticmethod
    def _is_mv(target: Dict) -> bool:
        return target.get("config", {}).get("table_type") == "mv"

    # -- validation / warnings --

    def _warn_inline_sources(self, sources: List[Dict]) -> None:
        for node in sources:
            st = node.get("source_type", "delta")
            if st in ("sql", "python"):
                self.logger.warning(
                    "Source node '%s' defines an inline %s transformation (source_type: '%s'). "
                    "This is still supported but discouraged and may not be supported in a future "
                    "release. Define a source node and chain a dedicated transformation node off it "
                    "instead.", node.get("name"), st, st)

    def _validate(self, sources: List[Dict], targets: List[Dict], nodes: List[Dict]) -> None:
        names = {n.get("name") for n in nodes}
        for t in targets:
            for view in self._inputs(t):
                if view[1] not in names:
                    raise ValueError(f"Node '{t.get('name')}' references non-existent input '{view[1]}'")
            if self._is_mv(t) and "source_view" in t.get("config", {}):
                raise ValueError(
                    f"Materialized view target '{t.get('name')}' defines an inline 'source_view'. "
                    "This is no longer supported. Declare a source node and chain it into the "
                    "materialized view target via its 'input' array instead.")
        if not targets:
            raise ValueError("Nodespec spec must contain at least one target node")

        mv_inline_sql = all(
            self._is_mv(t) and (t["config"].get("sql_path") or t["config"].get("sql_statement")) for t in targets)
        snapshot = all(t.get("config", {}).get("cdc_snapshot_settings") for t in targets)
        if not sources and not (mv_inline_sql or snapshot):
            raise ValueError("Nodespec spec must contain at least one source node")

    # -- inputs --

    def _inputs(self, node: Dict) -> List[Tuple[Optional[str], str]]:
        """``input`` items as (flow_name, view_name); strings auto-name the flow."""
        pairs = []
        for item in node.get("config", {}).get("input", []) or []:
            if isinstance(item, dict) and item.get("view"):
                pairs.append((item.get("flow"), item["view"]))
            elif not isinstance(item, dict):
                pairs.append((None, item))
        return pairs

    # -- shared settings --

    def _settings(self, dst: Dict, cfg: Dict, *, cdc=False, migration=False, dq_default=False) -> None:
        """Copy CDC / data-quality / quarantine / table-migration settings onto `dst`."""
        if cdc:
            if cfg.get("cdc_settings"):
                dst["cdcSettings"] = cfg["cdc_settings"]
            if cfg.get("cdc_snapshot_settings"):
                dst["cdcSnapshotSettings"] = _deep_camel(cfg["cdc_snapshot_settings"])
        if dq_default:
            dst["dataQualityExpectationsEnabled"] = cfg.get("data_quality_expectations_enabled", False)
        elif cfg.get("data_quality_expectations_enabled"):
            dst["dataQualityExpectationsEnabled"] = cfg["data_quality_expectations_enabled"]
        if cfg.get("data_quality_expectations_path"):
            dst["dataQualityExpectationsPath"] = cfg["data_quality_expectations_path"]
        if cfg.get("quarantine_mode"):
            dst["quarantineMode"] = cfg["quarantine_mode"]
        if cfg.get("quarantine_target_details"):
            dst["quarantineTargetDetails"] = cfg["quarantine_target_details"]
        if migration and cfg.get("table_migration_details"):
            dst["tableMigrationDetails"] = _deep_camel(cfg["table_migration_details"])

    def _base(self, spec_data: Dict) -> Dict:
        base = {k: spec_data.get(c) for k, c in
                (("dataFlowId", "dataFlowId"), ("dataFlowGroup", "dataFlowGroup"), ("dataFlowType", "dataFlowType"))}
        base["features"] = spec_data.get("features", {})
        if spec_data.get("dataFlowVersion"):
            base["dataFlowVersion"] = spec_data["dataFlowVersion"]
        return base

    # -- streaming targets --

    def _select_spec_target(self, targets, sources, nodes) -> Tuple[Dict, List[Dict]]:
        """Terminal target (not consumed by another node) becomes the spec target."""
        if len(targets) == 1:
            return targets[0], []
        consumed = {v for n in nodes for _, v in self._inputs(n)}
        source_tables = {s.get("config", {}).get("table") for s in sources} - {None}
        terminal, other = [], []
        for t in targets:
            table = t.get("config", {}).get("table")
            (other if t.get("name") in consumed or table in source_tables else terminal).append(t)
        if not terminal:
            raise ValueError("Could not determine spec target: all target nodes are consumed by other nodes")
        if len(terminal) > 1:
            self.logger.warning("Multiple terminal targets found %s. Using last target '%s' as spec target.",
                                [t.get("name") for t in terminal], terminal[-1].get("name"))
        return terminal[-1], other + terminal[:-1]

    def _streaming_spec(self, spec_data: Dict, spec_target: Dict, others: List[Dict]) -> Dict:
        cfg = spec_target.get("config", {})
        fmt = spec_target.get("target_type", "delta")
        has_cdc = bool(cfg.get("cdc_settings") or cfg.get("cdc_snapshot_settings"))

        spec = self._base(spec_data)
        spec["targetFormat"] = fmt
        spec["targetDetails"] = self._target_details(cfg) if fmt == "delta" else self._sink_details(cfg)
        spec["tags"] = spec_data.get("tags", {})
        self._settings(spec, cfg, cdc=True, migration=True, dq_default=True)
        spec["flowGroups"] = [self._flow_group(spec_target, others, has_cdc)]
        return spec

    def _target_details(self, cfg: Dict) -> Dict:
        return {"table": cfg.get("table"), "type": TableType.STREAMING, **_camel(cfg, _HANDLED)}

    def _sink_details(self, cfg: Dict) -> Dict:
        details: Dict[str, Any] = {}
        if "name" in cfg:
            details["name"] = cfg["name"]
        if "sink_type" in cfg:
            details["type"] = cfg["sink_type"]
        if "sink_options" in cfg:
            details["sinkOptions"] = cfg["sink_options"]
        if "sink_config" in cfg:
            details["config"] = _deep_camel(cfg["sink_config"])
        return details

    def _flow_group(self, spec_target: Dict, others: List[Dict], has_cdc: bool) -> Dict:
        group = {"flowGroupId": self.FLOW_GROUP_ID, "flows": {}}
        staging = {}
        for t in others:
            cfg = t.get("config", {})
            table = cfg.get("table")
            if table and table not in staging:
                entry = {"type": "ST", **_camel(cfg, _HANDLED)}
                self._settings(entry, cfg, cdc=True)
                staging[table] = entry
        if staging:
            group["stagingTables"] = staging

        registered: Set[str] = set()  # views already attached (avoid SDP "Cannot redefine")
        by_table: Dict[str, List[Dict]] = defaultdict(list)
        for t in others + [spec_target]:
            cfg = t.get("config", {})
            table = cfg.get("table") or cfg.get("name")
            if table:
                by_table[table].append(t)

        counter = 0
        for table, ts in by_table.items():
            for t in ts:
                counter = self._add_flows(group, t, table, spec_target, has_cdc, registered, counter)
        return group

    def _add_flows(self, group, target, table, spec_target, has_cdc, registered, counter) -> int:
        cfg = target.get("config", {})
        name = target.get("name")
        enabled = target.get("enabled", True)
        inputs = self._inputs(target)

        if not inputs:  # only valid for snapshot CDC targets (snapshot reads its source directly)
            if cfg.get("cdc_snapshot_settings"):
                group["flows"][f"{self.FLOW_PREFIX}{name}_{counter}"] = {
                    "flowType": FlowType.MERGE, "flowDetails": {"targetTable": table}, "enabled": enabled}
                counter += 1
            else:
                self.logger.warning(f"Target '{name}' has no inputs, skipping")
            return counter

        merge = bool(cfg.get("cdc_settings") or (has_cdc and target is spec_target))
        for flow_name, view in inputs:
            node = self.lookup.get(view, {})
            sql_source = node.get("node_type", "").lower() == self.SOURCE and node.get("source_type") == "sql"
            ftype = FlowType.MERGE if merge else (FlowType.APPEND_SQL if sql_source else FlowType.APPEND_VIEW)
            key = flow_name or f"{self.FLOW_PREFIX}{view}_{counter}"
            counter += 1

            if ftype == FlowType.APPEND_SQL:
                flow = {"flowType": ftype, "flowDetails": {"targetTable": table}, "enabled": enabled}
                flow["flowDetails"].update(_first(node.get("config", {}), "sql_statement", "sql_path"))
            else:
                source_view, views = self._views_for(view)
                if not source_view:
                    self.logger.warning(f"Could not determine source view for target '{name}' input '{view}'")
                    continue
                flow = {"flowType": ftype, "flowDetails": {"sourceView": source_view, "targetTable": table},
                        "enabled": enabled}
                fresh = {k: v for k, v in views.items() if k not in registered}
                if fresh:
                    flow["views"] = fresh
                registered.update(views)

            if cfg.get("once"):
                flow["flowDetails"]["once"] = True
            group["flows"][key] = flow
        return counter

    # -- materialized views --

    def _mv_spec(self, spec_data: Dict, target: Dict, sources: List[Dict]) -> Dict:
        cfg = target.get("config", {})
        mv = cfg.get("table")
        # config-level details + table_details (the latter overrides on conflict).
        details = {"table": mv, "type": TableType.MATERIALIZED_VIEW,
                   **_camel(cfg, _HANDLED), **_camel(cfg.get("table_details", {}))}

        spec = self._base(spec_data)
        spec.pop("dataFlowVersion", None)  # MV specs do not carry a version
        spec["targetFormat"] = TargetType.DELTA
        spec["targetDetails"] = details
        spec["localPath"] = spec_data.get("localPath")
        self._settings(spec, cfg, dq_default=True)

        group = {"flowGroupId": self.FLOW_GROUP_ID, "flows": {}}
        inputs = self._inputs(target)
        if inputs:
            self.internal = self._internal_sources(sources, [target])
            flow_name, view = inputs[0]
            source_view, views = self._views_for(view)
            if source_view:
                details["sourceView"] = source_view
                flow = {"flowType": FlowType.MATERIALIZED_VIEW, "flowDetails": {"targetTable": mv}}
                if views:
                    for v in views.values():
                        v["mode"] = Mode.BATCH  # MVs use batch reads (spark.sql)
                    flow["views"] = views
                group["flows"][flow_name or f"{self.FLOW_PREFIX}{mv}"] = flow
        spec["flowGroups"] = [group]
        return spec

    # -- views / internal sources --

    def _internal_sources(self, sources: List[Dict], targets: List[Dict]) -> Dict[str, str]:
        """Delta sources reading a table produced by a target here (referenced directly, no view)."""
        produced = {t["config"]["table"]: (t["config"].get("database") or None)
                    for t in targets if t.get("config", {}).get("table")}
        internal = {}
        for s in sources:
            if s.get("source_type", "delta") != "delta":
                continue
            cfg = s.get("config", {})
            table = cfg.get("table", "")
            if table in produced:
                sdb, tdb = cfg.get("database") or None, produced[table]
                if not sdb or not tdb or sdb == tdb:
                    internal[s.get("name")] = table
        return internal

    def _view_name(self, name: str) -> str:
        return name if name.startswith(self.VIEW_PREFIX) else f"{self.VIEW_PREFIX}{name}"

    def _views_for(self, view: str) -> Tuple[Optional[str], Dict]:
        """Resolve an input to (source_view_name, views). A transformation also pulls
        in every source node so SDP can resolve its references."""
        if view in self.internal:  # internal source reads the produced table directly
            return self.internal[view], {}
        node = self.lookup.get(view)
        if not node:
            return self._view_name(view), {}

        name = node.get("output_view_name") or self._view_name(view)
        ntype = node.get("node_type", "").lower()
        views = {}
        if ntype == self.SOURCE:
            views[name] = self._source_view(node)
        elif ntype == self.TRANSFORMATION:
            views[name] = self._transform_view(node)
            for n2, node2 in self.lookup.items():  # register all sources for SDP resolution
                if node2.get("node_type", "").lower() != self.SOURCE:
                    continue
                vn = node2.get("output_view_name") or self._view_name(n2)
                if vn in views:
                    continue
                if n2 in self.internal:  # internal sources need database "live"
                    node2 = {**node2, "config": {**node2.get("config", {}), "database": "live"}}
                views[vn] = self._source_view(node2)
        return name, views

    def _source_view(self, node: Dict) -> Dict:
        st = node.get("source_type", "delta")
        cfg = node.get("config", {})
        details = _camel(cfg, drop={"mode", "python_transform"})
        if st == "delta":
            details.setdefault("cdfEnabled", False)
        if cfg.get("python_transform"):
            details["pythonTransform"] = self._py_transform(cfg["python_transform"])
        return {"mode": cfg.get("mode", Mode.STREAM), "sourceType": st, "sourceDetails": details}

    def _transform_view(self, node: Dict) -> Dict:
        cfg = node.get("config", {})
        if node.get("transformation_type", "sql") != "python":
            return {"mode": Mode.BATCH, "sourceType": "sql",
                    "sourceDetails": _first(cfg, "sql_path", "sql_statement")}
        # python transform: its own view reading the inferred upstream via apply_transform(df).
        view, mode = self._python_upstream(node)
        pt: Dict[str, Any] = {}
        if cfg.get("function_path"):
            pt["functionPath"] = cfg["function_path"]
        elif cfg.get("python_module"):
            pt["module"] = cfg["python_module"]
        if cfg.get("tokens"):
            pt["tokens"] = cfg["tokens"]
        return {"mode": mode, "sourceType": "delta",
                "sourceDetails": {"database": "live", "table": view, "pythonTransform": pt}}

    @staticmethod
    def _py_transform(pt: Dict) -> Dict:
        out: Dict[str, Any] = {}
        if pt.get("function_path") or pt.get("functionPath"):
            out["functionPath"] = pt.get("function_path") or pt.get("functionPath")
        if pt.get("python_module") or pt.get("module"):
            out["module"] = pt.get("python_module") or pt.get("module")
        if pt.get("tokens"):
            out["tokens"] = pt["tokens"]
        return out

    def _python_upstream(self, node: Dict) -> Tuple[str, str]:
        """Infer the upstream view a python transform reads (it has no textual ref)."""
        sources = [n for n in self.lookup.values() if n.get("node_type", "").lower() == self.SOURCE]
        if not sources:
            self.logger.warning("Python transformation '%s' has no upstream source node to read from.",
                                node.get("name"))
            return self._view_name(node.get("name")), Mode.STREAM
        if len(sources) > 1:
            self.logger.warning("Python transformation '%s' has multiple upstream sources %s; reading from '%s'.",
                                node.get("name"), [s.get("name") for s in sources], sources[0].get("name"))
        up = sources[0]
        return up.get("output_view_name") or self._view_name(up.get("name")), up.get("config", {}).get("mode", Mode.STREAM)
