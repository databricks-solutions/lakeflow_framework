#!/bin/bash
# Feature Samples Bundle Deployment

# Sample-specific constants
BUNDLE_NAME="Feature Samples Bundle"

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

# Set schema — single feature schema for the entire bundle
schema="${schema_namespace}_feature${logical_env}"

# Set up bundle environment
setup_bundle_env "$BUNDLE_NAME" "$schema"

# Update substitutions file with catalog and schema namespace
if ! update_substitutions_file "feature-samples/src/pipeline_configs/dev_substitutions.json"; then
    log_error "Failed to update substitutions file. Exiting."
    exit 1
fi

# Update pipeline global config with table migration state volume path
if ! update_pipeline_global_config_file "feature-samples/src/pipeline_configs/global.json"; then
    log_error "Failed to update pipeline global config file. Exiting."
    exit 1
fi

# Change to feature-samples directory for deployment
cd feature-samples

# Deploy the bundle
deploy_bundle "$BUNDLE_NAME"

# Return to parent directory
cd ..

# Restore original files
restore_substitutions_file "feature-samples/src/pipeline_configs/dev_substitutions.json"
restore_pipeline_global_config_file "feature-samples/src/pipeline_configs/global.json"
