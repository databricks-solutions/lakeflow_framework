# Scripts

This directory contains utility scripts and tools for the Lakeflow Framework project.

## Available Scripts

### `validate_dataflows.py`

Validates dataflow JSON/YAML specification files against the project's JSON schemas.

**Usage:**
```bash
# Validate all dataflow files in the project (with version mapping by default)
python scripts/validate_dataflows.py

# Validate files in a specific directory
python scripts/validate_dataflows.py samples/bronze_sample/

# Validate a single file
python scripts/validate_dataflows.py samples/bronze_sample/src/dataflows/base_samples/dataflowspec/customer_main.json

# Validate without version mapping (strict mode - validates against current schema only)
python scripts/validate_dataflows.py --no-mapping samples/bronze_sample/

# Verbose output
python scripts/validate_dataflows.py -v
```

**What it validates:**
- Searches for all `*_main.json` files in `dataflows/**/dataflowspec/` directories
- Validates against `src/schemas/main.json` (which routes to appropriate sub-schemas)
- Reports validation errors with clear messages

**Version Mapping (enabled by default):**
- Automatically detects `dataFlowVersion` property in spec files
- Applies version-specific transformations from `src/config/dataflow_spec_mapping/{version}/`
- Transforms old property names to current schema (e.g., `cdcApplyChanges` → `cdcSettings`)
- Useful for validating legacy spec files against the current schema
- Shows which files had mappings applied with a version indicator `[v0.1.0]`
- Use `--no-mapping` flag to disable this behavior and validate strictly against current schema

**Requirements:**
- Python 3.9+
- `jsonschema` package (install with: `pip install jsonschema`)

**Exit codes:**
- `0`: All validations passed
- `1`: One or more validations failed or error occurred

---

### `convert_json_to_yaml.py`

Converts Lakeflow Framework pipeline bundles from JSON format to YAML format, with optional validation.

**Features:**
- Converts dataflow specifications, flow groups, expectations, substitutions, and secrets files
- Automatically updates file extensions (e.g., `*_main.json` → `*_main.yaml`)
- Updates references to DQE files (`.json` → `.yaml` in `dataQualityExpectationsPath`)
- Optional validation using `validate_dataflows.py`
- Bundle-level or single-file conversion
- Dry-run mode to preview changes

**Usage:**
```bash
# Convert a single file
python scripts/convert_json_to_yaml.py --file path/to/file.json

# Convert an entire bundle
python scripts/convert_json_to_yaml.py --bundle samples/bronze_sample --output samples/bronze_sample_yaml

# Convert with overwrite
python scripts/convert_json_to_yaml.py --bundle samples/bronze_sample --output samples/bronze_sample_yaml --overwrite

# Dry run (preview changes without making them)
python scripts/convert_json_to_yaml.py --bundle samples/bronze_sample --dry-run

# Convert without validation
python scripts/convert_json_to_yaml.py --bundle samples/bronze_sample --no-validate
```

**Command-Line Options:**
- `--file PATH` - Convert a single JSON file to YAML
- `--bundle PATH` - Convert an entire bundle directory
- `--output PATH` - Output location (file or directory)
- `--overwrite` - Overwrite existing files/directories
- `--convert-schemas` - Also convert schema JSON files (default: skip)
- `--no-validate` - Skip validation (validation using `validate_dataflows.py` is enabled by default)
- `--dry-run` - Preview changes without modifying files

**File Type Conversions:**
| Original (JSON) | Converted (YAML) |
|----------------|------------------|
| `*_main.json` | `*_main.yaml` |
| `*_flow.json` | `*_flow.yaml` |
| `*_dqe.json` | `*_expectations.yaml` |
| `*_substitutions.json` | `*_substitutions.yaml` |
| `*_secrets.json` | `*_secrets.yaml` |

**Validation:**
- By default, runs `validate_dataflows.py` on converted files
- Validates all `*_main.yaml` dataflow specifications
- Uses version mapping to support legacy specs
- Reports validation results in the conversion summary

**Example Output:**
```
Converting bundle from samples/bronze_sample to samples/bronze_sample_yaml
Copying bundle structure...
Scanning for JSON files to convert...
Found 34 JSON files to convert
  Converting: src/dataflows/base_samples/dataflowspec/customer_main.json -> customer_main.yaml
  Converting: src/pipeline_configs/dev_substitutions.json -> dev_substitutions.yaml
...

================================================================================
Validating converted files...
================================================================================
Validating 30 file(s) (with version mapping)...
✓ All dataflow files validated successfully

================================================================================
Conversion Summary:
================================================================================
Files converted: 34
  - Main specs: 30
  - Flow groups: 0
  - Expectations: 2
  - Secrets: 1
  - Substitutions: 1
Files removed: 34
Validation: PASSED
================================================================================
```

**Requirements:**
- Python 3.9+
- `pyyaml` package (install with: `pip install pyyaml`)
- `jsonschema` package (for validation, install with: `pip install jsonschema`)

**Exit codes:**
- `0`: Success (all files converted successfully)
- `1`: Error occurred (validation failures, conversion errors, or missing files)

**Programmatic Usage:**
```python
from convert_json_to_yaml import json_to_yaml_basic, convert_bundle, convert_json_file_to_yaml

# Convert a single file
convert_json_file_to_yaml(
    input_path="path/to/file.json",
    output_path="path/to/file.yaml"
)

# Convert an entire bundle
stats = convert_bundle(
    source_bundle_path="samples/bronze_sample",
    target_bundle_path="samples/bronze_sample_yaml",
    validate=True,
    overwrite=True
)

print(f"Converted {stats['converted_files']} files")
```

---

## Notes

- The converted YAML files are fully compatible with the Lakeflow Framework's YAML support
- Both JSON and YAML formats are supported by the framework
- Schema files typically remain in JSON format (use `--convert-schemas` if needed)

