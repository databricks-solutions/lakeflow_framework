#!/bin/bash
# Silver Sample Bundle Deployment

# Sample-specific constants
BUNDLE_NAME="Silver Sample Bundle"
SCHEMA="${DEFAULT_SCHEMA_NAMESPACE}_silver"

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

# Set schema - use command line if provided, otherwise use constant with logical environment
if [[ -n "$schema_namespace" ]]; then
    # Use schema from command line
    schema="${schema_namespace}_silver$logical_env"
else
    # Use schema constant with logical environment
    schema="$SCHEMA$logical_env"
fi

# Set up bundle environment
setup_bundle_env "$BUNDLE_NAME" "$schema"

# Update substitutions file with catalog and schema namespace
if ! update_substitutions_file "silver_sample/src/pipeline_configs/dev_substitutions.json"; then
    log_error "Failed to update substitutions file. Exiting."
    exit 1
fi

# Change to silver_sample directory for deployment
cd silver_sample

# Deploy the bundle
deploy_bundle "$BUNDLE_NAME"

# Return to parent directory
cd ..

# Restore original substitutions file
restore_substitutions_file "silver_sample/src/pipeline_configs/dev_substitutions.json"