#!/usr/bin/env python3
"""
Lakeflow Framework Pipeline Bundle Scaffolder

Generates a complete, deploy-ready Lakeflow Framework pipeline bundle with:
- databricks.yml (DAB bundle definition)
- Pipeline resource YAMLs (SDP pipeline definitions)
- Data Flow Specs (standard, flows, or materialized_view)
- Schema JSON files (StructType format)
- Data quality expectation files
- SQL transform files (for silver/gold)
- Substitution configs (per environment)
- Template definitions (for multiple similar tables)
- Python extension stubs (if requested)

Usage:
    python scaffold_lakeflow_bundle.py \
        --name "energy_bronze" \
        --catalog main \
        --schema energy_workshop \
        --layer bronze \
        --pattern basic_1_1 \
        --tables "raw_customers,raw_meter_readings,raw_billing" \
        --format json \
        --workspace-host "https://my-workspace.cloud.databricks.com"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional


PATTERNS = {
    "basic_1_1": {
        "dataFlowType": "standard",
        "layer": "bronze",
        "description": "Basic 1:1 streaming ingestion (Bronze)",
    },
    "stream_static": {
        "dataFlowType": "flow",
        "layer": "silver",
        "description": "Stream-static join pattern (Silver)",
    },
    "multi_source_streaming": {
        "dataFlowType": "flow",
        "layer": "silver",
        "description": "Multi-source streaming merge (Silver)",
    },
    "cdc_snapshot": {
        "dataFlowType": "standard",
        "layer": "bronze",
        "description": "CDC from historical snapshots (Bronze)",
    },
    "materialized_view": {
        "dataFlowType": "materialized_view",
        "layer": "gold",
        "description": "Materialized views for aggregations (Gold)",
    },
}


def create_directory_structure(base_path: Path, tables: List[str], pattern: str, use_template: bool) -> None:
    dirs = [
        base_path / "resources",
        base_path / "src" / "pipeline_configs",
        base_path / "fixtures",
        base_path / "scratch",
    ]

    if use_template:
        dirs.append(base_path / "src" / "templates")
        dirs.append(base_path / "src" / "dataflows" / "dataflowspec")
        dirs.append(base_path / "src" / "dataflows" / "schemas")
        dirs.append(base_path / "src" / "dataflows" / "expectations")
    else:
        for table in tables:
            table_dir = base_path / "src" / "dataflows" / table
            dirs.extend([
                table_dir / "dataflowspec",
                table_dir / "schemas",
                table_dir / "expectations",
                table_dir / "dml",
            ])

    pattern_info = PATTERNS.get(pattern, {})
    if pattern_info.get("dataFlowType") == "flow":
        dirs.append(base_path / "src" / "extensions")

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def generate_databricks_yml(
    base_path: Path,
    bundle_name: str,
    catalog: str,
    schema: str,
    layer: str,
    workspace_host: str,
    framework_path: str,
    environments: List[str],
) -> None:
    content = f"""bundle:
  name: {bundle_name}

include:
  - resources/*.yml

variables:
  owner:
    description: The owner of the bundle
    default: ${{workspace.current_user.userName}}
  catalog:
    description: The target UC catalog
    default: {catalog}
  schema:
    description: The target UC schema
    default: {schema}
  layer:
    description: The target medallion layer
    default: {layer}
  framework_source_path:
    description: Path to the deployed Lakeflow Framework source
    default: {framework_path}

targets:
"""
    for i, env in enumerate(environments):
        is_default = "true" if i == 0 else "false"
        mode_line = "    mode: development\n" if env == "dev" else ""
        content += f"""  {env}:
{mode_line}    default: {is_default}
    workspace:
      host: {workspace_host}
      root_path: /Workspace/Users/${{workspace.current_user.userName}}/.bundle/${{bundle.name}}/${{bundle.target}}
    variables:
      framework_source_path: /Workspace/Users/${{var.owner}}/.bundle/lakeflow_framework/{env}/current/files/src
"""

    (base_path / "databricks.yml").write_text(content)


def generate_pipeline_resource(
    base_path: Path,
    pipeline_name: str,
    layer: str,
    table_filter: Optional[str] = None,
    group_filter: Optional[str] = None,
) -> None:
    filters = ""
    if table_filter:
        filters += f"\n          pipeline.targetTableFilter: {table_filter}"
    if group_filter:
        filters += f"\n          pipeline.dataFlowGroupFilter: {group_filter}"

    content = f"""resources:
  pipelines:
    {pipeline_name}:
      name: {pipeline_name}
      catalog: ${{var.catalog}}
      schema: ${{var.schema}}
      channel: CURRENT
      serverless: true
      libraries:
        - notebook:
            path: ${{var.framework_source_path}}/dlt_pipeline

      configuration:
        bundle.sourcePath: /Workspace/${{workspace.file_path}}/src
        framework.sourcePath: /Workspace/${{var.framework_source_path}}
        workspace.host: ${{workspace.host}}
        bundle.target: ${{bundle.target}}
        pipeline.layer: ${{var.layer}}{filters}
"""

    (base_path / "resources" / f"{pipeline_name}.yml").write_text(content)


def generate_standard_dataflow_spec(
    table: str,
    group: str,
    source_db: str,
    source_table: str,
    target_table: str,
    mode: str = "stream",
    source_type: str = "delta",
    cdc_enabled: bool = True,
    scd_type: str = "1",
    primary_keys: Optional[List[str]] = None,
    sequence_by: str = "updated_at",
    dq_enabled: bool = True,
    quarantine_mode: str = "off",
) -> Dict:
    pk = primary_keys or [f"{table}_id"]

    spec: Dict = {
        "dataFlowId": f"{table}_ingestion",
        "dataFlowGroup": group,
        "dataFlowType": "standard",
        "sourceType": source_type,
        "sourceSystem": "source",
        "sourceViewName": f"v_{source_table}",
        "sourceDetails": {
            "database": source_db,
            "table": source_table,
            "cdfEnabled": cdc_enabled,
            "schemaPath": f"schemas/{source_table}_schema.json",
        },
        "mode": mode,
        "targetFormat": "delta",
        "targetDetails": {
            "table": target_table,
            "tableProperties": {
                "delta.autoOptimize.optimizeWrite": "true",
                "delta.autoOptimize.autoCompact": "true",
            },
        },
    }

    if cdc_enabled:
        spec["cdcSettings"] = {
            "keys": pk,
            "sequence_by": sequence_by,
            "scd_type": scd_type,
            "ignore_null_updates": True,
            "except_column_list": [],
        }

    spec["dataQualityExpectationsEnabled"] = dq_enabled
    if dq_enabled:
        spec["dataQualityExpectationsPath"] = f"{target_table}_dqe.json"

    spec["quarantineMode"] = quarantine_mode
    if quarantine_mode == "table":
        spec["quarantineTargetDetails"] = {
            "targetFormat": "delta",
            "table": f"{target_table}_quarantine",
            "tableProperties": {},
        }
    else:
        spec["quarantineTargetDetails"] = {}

    return spec


def generate_flows_dataflow_spec(
    flow_id: str,
    group: str,
    target_table: str,
    sources: List[Dict],
    primary_keys: List[str],
    sequence_by: str = "updated_at",
    scd_type: str = "1",
    dq_enabled: bool = False,
) -> Dict:
    staging_table = f"staging_{target_table}_apnd"

    flows = {}
    for src in sources:
        view_name = f"v_{src['table']}"
        flows[f"f_{src['table']}"] = {
            "flowType": "append_view",
            "flowDetails": {
                "targetTable": staging_table,
                "sourceView": view_name,
            },
            "views": {
                view_name: {
                    "mode": "stream",
                    "sourceType": "delta",
                    "sourceDetails": {
                        "database": src["database"],
                        "table": src["table"],
                        "cdfEnabled": src.get("cdfEnabled", True),
                        "selectExp": src.get("selectExp", ["*"]),
                        "whereClause": src.get("whereClause", []),
                    },
                },
            },
        }

    flows["f_merge"] = {
        "flowType": "merge",
        "flowDetails": {
            "targetTable": target_table,
            "sourceView": staging_table,
        },
    }

    spec: Dict = {
        "dataFlowId": flow_id,
        "dataFlowGroup": group,
        "dataFlowType": "flow",
        "targetFormat": "delta",
        "targetDetails": {
            "table": target_table,
            "tableProperties": {
                "delta.enableChangeDataFeed": "true",
            },
        },
        "cdcSettings": {
            "keys": primary_keys,
            "sequence_by": sequence_by,
            "scd_type": scd_type,
            "ignore_null_updates": True,
            "except_column_list": [],
        },
        "dataQualityExpectationsEnabled": dq_enabled,
        "quarantineMode": "off",
        "quarantineTargetDetails": {},
        "flowGroups": [
            {
                "flowGroupId": f"fg_{target_table}",
                "stagingTables": {
                    staging_table: {
                        "type": "ST",
                        "schemaPath": "",
                    }
                },
                "flows": flows,
            }
        ],
    }

    return spec


def generate_materialized_view_spec(
    mv_id: str,
    group: str,
    views: List[Dict],
) -> Dict:
    mv_dict = {}
    for v in views:
        mv_entry: Dict = {}
        if v.get("sqlStatement"):
            mv_entry["sqlStatement"] = v["sqlStatement"]
        elif v.get("sqlPath"):
            mv_entry["sqlPath"] = v["sqlPath"]
        else:
            mv_entry["sourceView"] = {
                "sourceViewName": f"v_{v['name']}",
                "sourceType": v.get("sourceType", "delta"),
                "sourceDetails": {
                    "database": v["database"],
                    "table": v["sourceTable"],
                },
            }

        if v.get("clusterByColumns"):
            mv_entry.setdefault("tableDetails", {})["clusterByColumns"] = v["clusterByColumns"]
        if v.get("database"):
            mv_entry.setdefault("tableDetails", {})["database"] = v.get("targetDatabase", v["database"])

        mv_entry["dataQualityExpectationsEnabled"] = v.get("dq_enabled", False)
        mv_entry["quarantineMode"] = "off"
        mv_entry["quarantineTargetDetails"] = {}

        mv_dict[v["name"]] = mv_entry

    return {
        "dataFlowId": mv_id,
        "dataFlowGroup": group,
        "dataFlowType": "materialized_view",
        "materializedViews": mv_dict,
    }


def generate_schema_file(table_name: str, columns: List[Dict]) -> Dict:
    fields = []
    for col in columns:
        field = {
            "name": col["name"],
            "type": col.get("type", "string"),
            "nullable": col.get("nullable", True),
            "metadata": col.get("metadata", {}),
        }
        fields.append(field)

    return {"type": "struct", "fields": fields}


def generate_expectations_file(
    table_name: str,
    expectations: Optional[Dict] = None,
) -> Dict:
    if expectations:
        return expectations

    return {
        "expect": [
            {
                "name": f"{table_name}_not_null_id",
                "constraint": f"{table_name}_id IS NOT NULL",
                "tag": "completeness",
                "enabled": True,
            }
        ],
        "expect_or_drop": [],
        "expect_or_fail": [],
    }


def generate_substitutions(
    base_path: Path,
    env: str,
    catalog: str,
    schema: str,
    layer: str,
) -> None:
    schema_token = f"{catalog}.{layer}_{schema}"
    if env != "dev":
        schema_token = f"{catalog}.{layer}_{schema}_{env}"

    content = {
        "tokens": {
            f"{layer}_schema": schema_token,
            "landing_path": f"/Volumes/{catalog}/{schema}/landing",
        },
        "prefix_suffix": {},
    }

    filepath = base_path / "src" / "pipeline_configs" / f"{env}_substitutions.json"
    filepath.write_text(json.dumps(content, indent=4) + "\n")


def generate_template(
    base_path: Path,
    template_name: str,
    pattern: str,
    source_type: str = "delta",
) -> Dict:
    if pattern in ("basic_1_1", "cdc_snapshot"):
        template = {
            "name": template_name,
            "parameters": {
                "dataFlowId": {"type": "string", "required": True},
                "sourceTable": {"type": "string", "required": True},
                "targetTable": {"type": "string", "required": True},
                "schemaPath": {"type": "string", "required": False, "default": ""},
                "keyColumns": {"type": "list", "required": True},
                "sequenceBy": {"type": "string", "required": True},
                "scdType": {"type": "string", "required": False, "default": "1"},
            },
            "template": {
                "dataFlowId": "${param.dataFlowId}",
                "dataFlowGroup": template_name.replace("_template", ""),
                "dataFlowType": "standard",
                "sourceType": source_type,
                "sourceSystem": "source",
                "sourceViewName": "v_${param.sourceTable}",
                "sourceDetails": {
                    "database": f"{{{template_name.replace('_template', '')}_schema}}",
                    "table": "${param.sourceTable}",
                    "cdfEnabled": True,
                    "schemaPath": "${param.schemaPath}",
                },
                "mode": "stream",
                "targetFormat": "delta",
                "targetDetails": {
                    "table": "${param.targetTable}",
                    "tableProperties": {
                        "delta.autoOptimize.optimizeWrite": "true",
                        "delta.autoOptimize.autoCompact": "true",
                    },
                },
                "cdcSettings": {
                    "keys": "${param.keyColumns}",
                    "sequence_by": "${param.sequenceBy}",
                    "scd_type": "${param.scdType}",
                    "ignore_null_updates": True,
                    "except_column_list": [],
                },
                "dataQualityExpectationsEnabled": True,
                "quarantineMode": "off",
                "quarantineTargetDetails": {},
            },
        }
    else:
        template = {
            "name": template_name,
            "parameters": {
                "dataFlowId": {"type": "string", "required": True},
                "mvName": {"type": "string", "required": True},
                "sqlStatement": {"type": "string", "required": True},
                "clusterByColumns": {"type": "list", "required": False, "default": []},
            },
            "template": {
                "dataFlowId": "${param.dataFlowId}",
                "dataFlowGroup": template_name.replace("_template", ""),
                "dataFlowType": "materialized_view",
                "materializedViews": {
                    "${param.mvName}": {
                        "sqlStatement": "${param.sqlStatement}",
                        "tableDetails": {
                            "clusterByColumns": "${param.clusterByColumns}",
                        },
                        "dataQualityExpectationsEnabled": False,
                        "quarantineMode": "off",
                        "quarantineTargetDetails": {},
                    }
                },
            },
        }

    filepath = base_path / "src" / "templates" / f"{template_name}.json"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(template, indent=4) + "\n")
    return template


def generate_template_usage(
    base_path: Path,
    template_name: str,
    parameter_sets: List[Dict],
) -> None:
    content = {
        "template": template_name,
        "parameterSets": parameter_sets,
    }
    filepath = base_path / "src" / "dataflows" / "dataflowspec" / f"{template_name}_main.json"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(content, indent=4) + "\n")


def generate_extension_stubs(base_path: Path) -> None:
    ext_dir = base_path / "src" / "extensions"
    ext_dir.mkdir(parents=True, exist_ok=True)

    (ext_dir / "__init__.py").write_text("")

    (ext_dir / "sources.py").write_text('''from pyspark.sql import DataFrame, SparkSession
from typing import Dict


def get_custom_source(spark: SparkSession, tokens: Dict) -> DataFrame:
    """Custom source function — modify for your use case."""
    source_table = tokens["sourceTable"]
    return spark.readStream.option("readChangeFeed", "true").table(source_table)
''')

    (ext_dir / "transforms.py").write_text('''from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from typing import Dict


def clean_and_deduplicate(df: DataFrame) -> DataFrame:
    """Remove duplicates and add processing metadata."""
    return (
        df.dropDuplicates()
        .withColumn("_processed_at", F.current_timestamp())
    )


def clean_with_tokens(df: DataFrame, tokens: Dict) -> DataFrame:
    """Transform with configurable parameters from the data flow spec."""
    id_column = tokens.get("idColumn", "id")
    return df.dropDuplicates([id_column])
''')

    (ext_dir / "sinks.py").write_text('''from pyspark.sql import DataFrame
from typing import Dict


def write_to_external(df: DataFrame, batch_id: int, tokens: Dict) -> None:
    """Foreach batch sink — modify for your external target."""
    target = tokens.get("target", "console")
    if target == "console":
        df.show(truncate=False)
    else:
        records = df.toJSON().collect()
        for record in records:
            print(f"Batch {batch_id}: {record}")
''')


def write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4) + "\n")


def scaffold_bundle(args: argparse.Namespace) -> None:
    base_path = Path(args.output_dir) / args.name
    tables = [t.strip() for t in args.tables.split(",")] if args.tables else []
    environments = [e.strip() for e in args.environments.split(",")] if args.environments else ["dev"]
    pattern = args.pattern or "basic_1_1"
    layer = args.layer or PATTERNS.get(pattern, {}).get("layer", "bronze")
    use_template = args.use_template and len(tables) > 1 and pattern in ("basic_1_1", "cdc_snapshot", "materialized_view")

    print(f"Scaffolding Lakeflow Framework pipeline bundle: {args.name}")
    print(f"  Pattern: {pattern} ({PATTERNS.get(pattern, {}).get('description', 'custom')})")
    print(f"  Layer: {layer}")
    print(f"  Tables: {tables}")
    print(f"  Format: {args.format}")
    print(f"  Template mode: {use_template}")
    print(f"  Environments: {environments}")
    print()

    create_directory_structure(base_path, tables, pattern, use_template)

    fw_path = args.framework_path or f"/Workspace/Users/${{var.owner}}/.bundle/lakeflow_framework/dev/current/files/src"
    generate_databricks_yml(
        base_path, args.name, args.catalog, args.schema, layer,
        args.workspace_host or "https://WORKSPACE.cloud.databricks.com",
        fw_path, environments,
    )

    generate_pipeline_resource(
        base_path,
        pipeline_name=f"{args.name}_pipeline",
        layer=layer,
        group_filter=args.name if len(tables) > 3 else None,
    )

    for env in environments:
        generate_substitutions(base_path, env, args.catalog, args.schema, layer)

    if use_template:
        template_name = f"{args.name}_template"
        generate_template(base_path, template_name, pattern)

        param_sets = []
        for table in tables:
            target = table.replace("raw_", f"{layer}_") if table.startswith("raw_") else f"{layer}_{table}"
            param_sets.append({
                "dataFlowId": f"{table}_ingestion",
                "sourceTable": table,
                "targetTable": target,
                "schemaPath": f"schemas/{table}_schema.json",
                "keyColumns": [f"{table.replace('raw_', '')}_id"],
                "sequenceBy": "updated_at",
            })
        generate_template_usage(base_path, template_name, param_sets)

        for table in tables:
            default_schema = generate_schema_file(table, [
                {"name": f"{table.replace('raw_', '')}_id", "type": "integer", "nullable": False},
                {"name": "created_at", "type": "timestamp"},
                {"name": "updated_at", "type": "timestamp"},
            ])
            write_json(base_path / "src" / "dataflows" / "schemas" / f"{table}_schema.json", default_schema)

            target = table.replace("raw_", f"{layer}_") if table.startswith("raw_") else f"{layer}_{table}"
            dq = generate_expectations_file(table.replace("raw_", ""))
            write_json(base_path / "src" / "dataflows" / "expectations" / f"{target}_dqe.json", dq)

    else:
        for table in tables:
            target = table.replace("raw_", f"{layer}_") if table.startswith("raw_") else f"{layer}_{table}"
            source_db = f"{{{args.name}_schema}}"

            if pattern in ("basic_1_1", "cdc_snapshot"):
                spec = generate_standard_dataflow_spec(
                    table=table.replace("raw_", ""),
                    group=args.name,
                    source_db=source_db,
                    source_table=table,
                    target_table=target,
                    source_type="delta",
                    cdc_enabled=True,
                    scd_type="1",
                    dq_enabled=True,
                    quarantine_mode="off",
                )
                write_json(
                    base_path / "src" / "dataflows" / table / "dataflowspec" / f"{table}_main.json",
                    spec,
                )

            default_schema = generate_schema_file(table, [
                {"name": f"{table.replace('raw_', '')}_id", "type": "integer", "nullable": False},
                {"name": "created_at", "type": "timestamp"},
                {"name": "updated_at", "type": "timestamp"},
            ])
            write_json(
                base_path / "src" / "dataflows" / table / "schemas" / f"{table}_schema.json",
                default_schema,
            )

            dq = generate_expectations_file(table.replace("raw_", ""))
            write_json(
                base_path / "src" / "dataflows" / table / "expectations" / f"{target}_dqe.json",
                dq,
            )

    if PATTERNS.get(pattern, {}).get("dataFlowType") == "flow" or args.extensions:
        generate_extension_stubs(base_path)

    readme = f"""# {args.name}

Lakeflow Framework Pipeline Bundle — generated by `scaffold_lakeflow_bundle.py`.

## Pattern
**{PATTERNS.get(pattern, {}).get('description', pattern)}**

## Tables
{chr(10).join(f'- `{t}`' for t in tables)}

## Deploy

```bash
# Validate
databricks bundle validate -t dev

# Deploy
databricks bundle deploy -t dev

# Run the pipeline
databricks bundle run -t dev {args.name}_pipeline
```

## Structure
```
{args.name}/
├── databricks.yml
├── resources/
│   └── {args.name}_pipeline.yml
└── src/
    ├── dataflows/
    │   └── ...
    ├── pipeline_configs/
    │   └── {environments[0]}_substitutions.json
    └── {'templates/' if use_template else 'extensions/'}
```
"""
    (base_path / "README.md").write_text(readme)

    print(f"Bundle scaffolded at: {base_path}")
    print(f"Next steps:")
    print(f"  1. Review and customize the generated Data Flow Specs")
    print(f"  2. Update schema files with actual column definitions")
    print(f"  3. Add data quality expectations")
    print(f"  4. Run: cd {base_path} && databricks bundle validate -t dev")
    print(f"  5. Deploy: databricks bundle deploy -t dev")


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a Lakeflow Framework Pipeline Bundle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bronze ingestion for 3 tables
  %(prog)s --name energy_bronze --catalog main --schema energy --layer bronze \\
    --pattern basic_1_1 --tables "raw_customers,raw_billing,raw_outages"

  # Silver multi-source streaming
  %(prog)s --name energy_silver --catalog main --schema energy --layer silver \\
    --pattern multi_source_streaming --tables "silver_customer_360"

  # Gold materialized views with template
  %(prog)s --name energy_gold --catalog main --schema energy --layer gold \\
    --pattern materialized_view --tables "kpi_revenue,kpi_reliability,kpi_demand" \\
    --use-template

  # Full multi-env setup
  %(prog)s --name energy_bronze --catalog main --schema energy --layer bronze \\
    --pattern basic_1_1 --tables "raw_customers,raw_meter_readings" \\
    --environments "dev,staging,prod" --use-template
""",
    )

    parser.add_argument("--name", required=True, help="Bundle name")
    parser.add_argument("--catalog", required=True, help="Unity Catalog name")
    parser.add_argument("--schema", required=True, help="Target schema")
    parser.add_argument("--layer", choices=["bronze", "silver", "gold"], help="Medallion layer")
    parser.add_argument(
        "--pattern",
        choices=list(PATTERNS.keys()),
        default="basic_1_1",
        help="Pipeline pattern",
    )
    parser.add_argument("--tables", required=True, help="Comma-separated list of table names")
    parser.add_argument("--format", choices=["json", "yaml"], default="json", help="Spec format")
    parser.add_argument("--workspace-host", help="Databricks workspace URL")
    parser.add_argument(
        "--framework-path",
        help="Path to deployed framework source (default: auto-computed from owner)",
    )
    parser.add_argument(
        "--environments",
        default="dev",
        help="Comma-separated environments (default: dev)",
    )
    parser.add_argument(
        "--use-template",
        action="store_true",
        help="Generate a reusable template instead of individual specs",
    )
    parser.add_argument(
        "--extensions",
        action="store_true",
        help="Include Python extension stubs",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory (default: current directory)",
    )

    args = parser.parse_args()
    scaffold_bundle(args)


if __name__ == "__main__":
    main()
