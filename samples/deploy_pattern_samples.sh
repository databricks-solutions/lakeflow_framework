#!/bin/bash
# Pattern Samples Bundle Deployment

# Sample-specific constants
BUNDLE_NAME="Pattern Samples Bundle"

# Source common library and configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Parse command-line arguments
parse_common_args "$@"

# Prompt for missing parameters
prompt_common_params

# Validate all required parameters
if ! validate_required_params; then
    exit 1
fi

# Set up bundle environment (no single schema — each layer has its own)
setup_bundle_env "$BUNDLE_NAME"

# Export per-layer schema variables
export BUNDLE_VAR_bronze_schema="${schema_namespace}_bronze${logical_env}"
export BUNDLE_VAR_silver_schema="${schema_namespace}_silver${logical_env}"
export BUNDLE_VAR_gold_schema="${schema_namespace}_gold${logical_env}"
echo "  - BUNDLE_VAR_bronze_schema: $BUNDLE_VAR_bronze_schema"
echo "  - BUNDLE_VAR_silver_schema: $BUNDLE_VAR_silver_schema"
echo "  - BUNDLE_VAR_gold_schema:   $BUNDLE_VAR_gold_schema"

# Update substitutions file with catalog and schema namespace
if ! update_substitutions_file "pattern-samples/src/pipeline_configs/dev_substitutions.json"; then
    log_error "Failed to update substitutions file. Exiting."
    exit 1
fi

# Change to pattern-samples directory for deployment
cd pattern-samples

# Deploy the bundle
deploy_bundle "$BUNDLE_NAME"

# Return to parent directory
cd ..

# Restore original substitutions file
restore_substitutions_file "pattern-samples/src/pipeline_configs/dev_substitutions.json"
