#!/bin/bash
# TPCH Sample Bundle Deployment (single-catalog UC model)

# Sample-specific constants
BUNDLE_NAME="TPCH Samples Bundle"
# Suggested default namespace; user can override with --schema_namespace.
DEFAULT_TPCH_SCHEMA_NAMESPACE="tpch_sample"

# Source common library and configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Parse command-line arguments
parse_common_args "$@"

# Default the namespace BEFORE prompting so the tpch-specific default is used
# (and the user is not prompted) unless they passed --schema_namespace explicitly.
if [[ -z "$schema_namespace" ]]; then
    schema_namespace="$DEFAULT_TPCH_SCHEMA_NAMESPACE"
fi

# Prompt for any remaining missing parameters
prompt_common_params

# Optional: SQL warehouse id for the Genie space (blank = skip Genie deployment)
prompt_warehouse_optional

# Validate all required parameters
if ! validate_required_params; then
    exit 1
fi

# Set up common bundle environment (catalog, schema_namespace, logical_env, framework path, host)
setup_bundle_env "$BUNDLE_NAME"

# Single catalog, schema-per-layer. Derive the per-pipeline default schema names from the
# namespace + logical environment (mirrors how feature-samples derives its single schema).
export BUNDLE_VAR_bronze_schema="${schema_namespace}_bronze_reference_data${logical_env}"
export BUNDLE_VAR_silver_schema="${schema_namespace}_silver${logical_env}"
export BUNDLE_VAR_gold_schema="${schema_namespace}_gold${logical_env}"
echo "  - BUNDLE_VAR_bronze_schema: $BUNDLE_VAR_bronze_schema"
echo "  - BUNDLE_VAR_silver_schema: $BUNDLE_VAR_silver_schema"
echo "  - BUNDLE_VAR_gold_schema:   $BUNDLE_VAR_gold_schema"

# Update substitutions file (rewrites catalog + namespace prefixes when non-default)
if ! update_tpch_substitutions_file "tpch_sample/src/pipeline_configs/dev_substitutions.json"; then
    log_error "Failed to update substitutions file. Exiting."
    exit 1
fi

# Change to bundle directory for deployment
cd tpch_sample

# Deploy the bundle
deploy_bundle "$BUNDLE_NAME"

# Return to parent directory
cd ..

# Restore original substitutions file
restore_substitutions_file "tpch_sample/src/pipeline_configs/dev_substitutions.json"
