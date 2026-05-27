# `pipeline_bundle_template` — Databricks Asset Bundle custom template

This folder is a [DAB custom template][custom-templates] for scaffolding new Lakeflow Framework
pipeline bundles. End users **don't edit files here** — they run `databricks bundle init` against
this folder and get a new bundle populated from their answers.

[custom-templates]: https://docs.databricks.com/aws/en/dev-tools/bundles/templates#custom-templates

## Initializing a new bundle

From the repo root:

```bash
databricks bundle init ./pipeline_bundle_template --output-dir /path/to/output
```

Or against this folder hosted at a Git URL:

```bash
databricks bundle init https://github.com/liamperritt/lakeflow_framework --template-dir pipeline_bundle_template
```

The CLI will prompt for the values declared in `databricks_template_schema.json` (see below)
and emit a new bundle under `<output-dir>/<project_name>/`.

Requires Databricks CLI `>= 0.218.0`.

## Folder layout

```
pipeline_bundle_template/
├── databricks_template_schema.json     # prompt definitions
└── template/                           # Go-templated source tree
    └── {{.project_name}}/              # root folder is named from the project_name prompt
        ├── databricks.yml.tmpl
        ├── README.md.tmpl
        ├── .skip.tmpl                  # conditional file-skip rules
        ├── resources/
        │   └── {{.pipeline_name}}_pipeline.yml.tmpl
        └── src/
            ├── dataflows/{{.pipeline_name}}/
            │   ├── dataflowspec/[flow]{{.example_target_table}}_main.json.tmpl
            │   ├── dataflowspec/[standard]{{.example_target_table}}_main.json.tmpl
            │   ├── schemas/{{.example_target_table}}_schema.json
            │   └── expectations/{{.example_target_table}}_dqe.json
            └── pipeline_configs/dev_substitutions.json.tmpl
```

The Databricks CLI runs Go's `text/template` engine over every file under `template/` (and over
the path segments themselves). Files with a `.tmpl` suffix have their contents substituted and the
suffix stripped; non-`.tmpl` files are copied verbatim (path segments are still substituted).

## Prompts (`databricks_template_schema.json`)

| Property | Type | Default | Purpose |
|---|---|---|---|
| `project_name` | string | _required_ | bundle name + output root folder |
| `pipeline_name` | string | `my_pipeline` | first pipeline; drives `resources/*.yml` and `src/dataflows/*` folder names |
| `layer` | enum (bronze/silver/gold) | `bronze` | medallion layer; baked into `layer` DAB variable default |
| `catalog` | string | `main` | UC catalog; baked into `catalog` DAB variable default |
| `schema` | string | `{{.project_name}}` | UC schema; baked into `schema` DAB variable default |
| `include_example_dataflows` | enum (yes/no) | `yes` | if `no`, `.skip.tmpl` omits the `src/dataflows/{{.pipeline_name}}` folder |
| `example_target_table` | string | `my_target_table` | (skipped if no examples) target table; drives `dataFlowId`, `flowGroupId`, filenames |
| `example_source_table` | string | `my_source_table` | (skipped if no examples) upstream source table |
| `source_catalog` | string | `{{.catalog}}` | (skipped if no examples) pre-populated into `dev_substitutions.json` as the `SOURCE_CAT_SCHEMA` token |
| `source_schema` | string | `{{.schema}}` | (skipped if no examples) pre-populated into `dev_substitutions.json` |

## What gets derived vs. what stays as scaffolding

Every single-value placeholder in the source dataflow JSON files is **derived** from the prompts
above (no extra typing). For example, in the rendered `[flow]<target>_main.json`:
- `dataFlowId` = `<example_target_table>_flow`
- `dataFlowGroup` = `<pipeline_name>`
- `flowGroupId` = `fg_<example_target_table>`
- `view` key = `v_<example_source_table>`
- `sourceDetails.database` = `{SOURCE_CAT_SCHEMA}` (resolved at pipeline runtime via `dev_substitutions.json`)

A few values are **hardcoded sensible defaults** the user edits if their data source differs:
- `sourceType` = `delta`
- `quarantineMode` = `off`

A few variable-length lists **stay as literal `<...>` scaffolding** because they can't be cleanly
prompted (the count varies):
- Schema fields in `{{.example_target_table}}_schema.json`
- DQE constraints in `{{.example_target_table}}_dqe.json`
- `selectExp` column list in `[standard]{{.example_target_table}}_main.json`
- Extra tokens / `prefix_suffix` entries in `dev_substitutions.json`

## Extending the template

To add a new prompt:

1. Add a property entry to `databricks_template_schema.json` (set `type`, `description`, `default`,
   `order`, plus optional `enum`, `pattern`, `pattern_match_failure_message`, `skip_prompt_if`).
2. Reference it in any `.tmpl` file as `{{.your_new_property}}`.
3. Test with `databricks bundle init ./pipeline_bundle_template --output-dir /tmp/init-test` and
   inspect the generated bundle.

To conditionally skip files based on user answers, extend `template/{{.project_name}}/.skip.tmpl`:

```
{{- if eq .some_property "value" -}}
{{ skip (printf "path/to/%s" .other_property) }}
{{- end -}}
```

The `skip` function takes a glob pattern relative to `template/{{.project_name}}/`. To compose
paths from other properties, use Go template's `printf` — `{{...}}` inside string literals is
**not** re-processed.

## Verification (manual)

```bash
# Init with examples
databricks bundle init ./pipeline_bundle_template --output-dir /tmp/test-init

# Validate
cd /tmp/test-init/<project_name>
databricks bundle validate --target dev

# Init without examples (verify skip path)
databricks bundle init ./pipeline_bundle_template --output-dir /tmp/test-init-skip
# answer 'no' to include_example_dataflows
# confirm src/dataflows/ is absent
```
