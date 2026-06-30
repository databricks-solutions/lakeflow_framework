#!/bin/bash
# TPCH Sample Bundle Destroy (single-catalog UC model)

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

# Validate all required parameters
if ! validate_required_params; then
    exit 1
fi

# Set up common bundle environment (catalog, schema_namespace, logical_env, framework path, host)
setup_bundle_env "$BUNDLE_NAME"

# Single catalog, schema-per-layer. Derive the per-pipeline default schema names from the
# namespace + logical environment (must match what was deployed by deploy_tpch.sh).
export BUNDLE_VAR_bronze_schema="${schema_namespace}_bronze_reference_data${logical_env}"
export BUNDLE_VAR_silver_schema="${schema_namespace}_silver${logical_env}"
export BUNDLE_VAR_gold_schema="${schema_namespace}_gold${logical_env}"
echo "  - BUNDLE_VAR_bronze_schema: $BUNDLE_VAR_bronze_schema"
echo "  - BUNDLE_VAR_silver_schema: $BUNDLE_VAR_silver_schema"
echo "  - BUNDLE_VAR_gold_schema:   $BUNDLE_VAR_gold_schema"

# Destroy the bundle
echo "Destroying $BUNDLE_NAME"
cd tpch_sample
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..
