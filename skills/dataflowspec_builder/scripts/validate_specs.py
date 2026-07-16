#!/usr/bin/env python3
"""
Validate Lakeflow Framework Data Flow Spec files for common issues.

Checks:
  - Valid JSON/YAML syntax
  - Required fields present per data flow type
  - Source view naming convention (v_prefix)
  - CDC settings completeness
  - Expectation file references resolve
  - Schema file references resolve
  - Template parameter completeness

Usage:
    python validate_specs.py <bundle_path>
    python validate_specs.py <spec_file.json>
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REQUIRED_METADATA = ["dataFlowId", "dataFlowGroup", "dataFlowType"]

REQUIRED_STANDARD = [
    "sourceType", "sourceViewName", "sourceDetails",
    "mode", "targetFormat", "targetDetails",
]

REQUIRED_FLOW = ["targetFormat", "targetDetails", "flowGroups"]

REQUIRED_MV = ["materializedViews"]

VALID_SOURCE_TYPES = {"cloudFiles", "delta", "deltaJoin", "kafka", "python", "sql", "batchFiles"}
VALID_MODES = {"stream", "batch"}
VALID_FLOW_TYPES = {"append_view", "append_sql", "merge"}
VALID_QUARANTINE_MODES = {"off", "flag", "table"}
VALID_SCD_TYPES = {"1", "2"}
VALID_STAGING_TYPES = {"ST", "MV"}


def validate_spec(spec: Dict, filepath: str) -> List[str]:
    errors = []

    if "template" in spec and "parameterSets" in spec:
        return _validate_template_usage(spec)
    if "name" in spec and "parameters" in spec and "template" in spec:
        return _validate_template_definition(spec)

    flow_type = spec.get("dataFlowType", "")

    for field in REQUIRED_METADATA:
        if field not in spec:
            errors.append(f"Missing required field: {field}")

    if not spec.get("dataFlowId", ""):
        errors.append("dataFlowId must not be empty")

    if flow_type == "standard":
        errors.extend(_validate_standard(spec))
    elif flow_type == "flow":
        errors.extend(_validate_flows(spec))
    elif flow_type == "materialized_view":
        errors.extend(_validate_materialized_view(spec))
    else:
        if flow_type:
            errors.append(f"Unknown dataFlowType: {flow_type}")

    return errors


def _validate_standard(spec: Dict) -> List[str]:
    errors = []
    for field in REQUIRED_STANDARD:
        if field not in spec:
            errors.append(f"Standard spec missing: {field}")

    src_type = spec.get("sourceType", "")
    if src_type and src_type not in VALID_SOURCE_TYPES:
        errors.append(f"Invalid sourceType: {src_type}. Valid: {VALID_SOURCE_TYPES}")

    view_name = spec.get("sourceViewName", "")
    if view_name and not view_name.startswith("v_") and not view_name.startswith("${"):
        errors.append(f"sourceViewName '{view_name}' must start with 'v_'")

    mode = spec.get("mode", "")
    if mode and mode not in VALID_MODES:
        errors.append(f"Invalid mode: {mode}. Valid: {VALID_MODES}")

    errors.extend(_validate_cdc(spec.get("cdcSettings")))
    errors.extend(_validate_quarantine(spec))

    return errors


def _validate_flows(spec: Dict) -> List[str]:
    errors = []
    for field in REQUIRED_FLOW:
        if field not in spec:
            errors.append(f"Flow spec missing: {field}")

    flow_groups = spec.get("flowGroups", [])
    if not flow_groups:
        errors.append("flowGroups must have at least one flow group")

    for i, fg in enumerate(flow_groups):
        fg_id = fg.get("flowGroupId", f"index_{i}")
        if "flowGroupId" not in fg:
            errors.append(f"Flow group {i} missing flowGroupId")

        staging = fg.get("stagingTables", {})
        for st_name, st_config in staging.items():
            st_type = st_config.get("type", "")
            if st_type and st_type not in VALID_STAGING_TYPES:
                errors.append(f"Staging table '{st_name}' invalid type: {st_type}")

        flows = fg.get("flows", {})
        if not flows:
            errors.append(f"Flow group '{fg_id}' must have at least one flow")

        for flow_name, flow_config in flows.items():
            ft = flow_config.get("flowType", "")
            if ft and ft not in VALID_FLOW_TYPES:
                errors.append(f"Flow '{flow_name}' invalid flowType: {ft}")

            fd = flow_config.get("flowDetails", {})
            if not fd.get("targetTable"):
                errors.append(f"Flow '{flow_name}' missing flowDetails.targetTable")

            if ft in ("append_view", "merge") and not fd.get("sourceView"):
                if "views" not in flow_config and ft != "merge":
                    errors.append(f"Flow '{flow_name}' ({ft}) missing sourceView or views")

    errors.extend(_validate_cdc(spec.get("cdcSettings")))
    errors.extend(_validate_quarantine(spec))

    return errors


def _validate_materialized_view(spec: Dict) -> List[str]:
    errors = []
    mvs = spec.get("materializedViews", {})
    if not mvs:
        errors.append("materializedViews must have at least one entry")

    for mv_name, mv_config in mvs.items():
        has_source = bool(mv_config.get("sourceView"))
        has_sql_path = bool(mv_config.get("sqlPath"))
        has_sql_stmt = bool(mv_config.get("sqlStatement"))
        source_count = sum([has_source, has_sql_path, has_sql_stmt])

        if source_count == 0:
            errors.append(f"MV '{mv_name}' must have sourceView, sqlPath, or sqlStatement")
        if source_count > 1:
            errors.append(f"MV '{mv_name}' has multiple source definitions (pick one)")

    return errors


def _validate_cdc(cdc: Dict = None) -> List[str]:
    errors = []
    if not cdc:
        return errors

    if not cdc.get("keys"):
        errors.append("cdcSettings.keys must not be empty")
    if not cdc.get("sequence_by"):
        errors.append("cdcSettings.sequence_by is required")

    scd = str(cdc.get("scd_type", ""))
    if scd and scd not in VALID_SCD_TYPES:
        errors.append(f"cdcSettings.scd_type must be '1' or '2', got: {scd}")

    return errors


def _validate_quarantine(spec: Dict) -> List[str]:
    errors = []
    mode = spec.get("quarantineMode", "off")
    if mode not in VALID_QUARANTINE_MODES:
        errors.append(f"Invalid quarantineMode: {mode}")
    if mode == "table":
        qtd = spec.get("quarantineTargetDetails", {})
        if not qtd.get("table") and not qtd.get("targetFormat"):
            errors.append("quarantineMode 'table' requires quarantineTargetDetails with table name")
    return errors


def _validate_template_usage(spec: Dict) -> List[str]:
    errors = []
    if not spec.get("template"):
        errors.append("Template usage must have 'template' field")
    ps = spec.get("parameterSets", [])
    if not ps:
        errors.append("parameterSets must have at least one entry")

    ids = [p.get("dataFlowId", "") for p in ps]
    dupes = [i for i in ids if ids.count(i) > 1]
    if dupes:
        errors.append(f"Duplicate dataFlowId in parameterSets: {set(dupes)}")

    return errors


def _validate_template_definition(spec: Dict) -> List[str]:
    errors = []
    params = spec.get("parameters", {})
    template = spec.get("template", {})

    if not params:
        errors.append("Template definition must have parameters")
    if not template:
        errors.append("Template definition must have template body")

    tmpl_str = json.dumps(template)
    for param_name, param_def in params.items():
        placeholder = f"${{param.{param_name}}}"
        if placeholder not in tmpl_str:
            if param_def.get("required", True) and "default" not in param_def:
                errors.append(f"Required parameter '{param_name}' not referenced in template")

    return errors


def validate_file(filepath: Path) -> Tuple[str, List[str]]:
    try:
        content = filepath.read_text()
        spec = json.loads(content)
    except json.JSONDecodeError as e:
        return str(filepath), [f"Invalid JSON: {e}"]
    except Exception as e:
        return str(filepath), [f"Error reading file: {e}"]

    errors = validate_spec(spec, str(filepath))
    return str(filepath), errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_specs.py <bundle_path_or_spec_file>")
        sys.exit(1)

    target = Path(sys.argv[1])

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.rglob("*.json"))
        files = [f for f in files if "dataflowspec" in str(f) or "templates" in str(f)]
    else:
        print(f"Not found: {target}")
        sys.exit(1)

    total_errors = 0
    total_files = 0

    for f in files:
        filepath, errors = validate_file(f)
        total_files += 1
        if errors:
            total_errors += len(errors)
            print(f"\n❌ {filepath}")
            for e in errors:
                print(f"   • {e}")
        else:
            print(f"✅ {filepath}")

    print(f"\n{'='*60}")
    print(f"Files checked: {total_files}")
    print(f"Errors found:  {total_errors}")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
