#!/bin/bash
# TPCH Bundle Deployment

# Sample-specific constants
BUNDLE_NAME="TPCH Bundle"
DEFAULT_TPCH_SCHEMA_NAMESPACE="lakeflow_samples_tpch"

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

# Set schemas - use command line if provided, otherwise use constants with logical environment
if [[ -n "$schema_namespace" ]]; then
    # Use schema from command line
    schema_namespace="$schema_namespace"
else
    # Use default schema namespace
    schema_namespace="$DEFAULT_TPCH_SCHEMA_NAMESPACE"
fi

# Set up bundle environment with all schemas
setup_bundle_env "$BUNDLE_NAME"

# Update substitutions file with catalog and schema namespace
if ! update_substitutions_file "tpch_sample/src/pipeline_configs/dev_substitutions.json"; then
    log_error "Failed to update substitutions file. Exiting."
    exit 1
fi

# Change to test_data_and_orchestrator directory for deployment
cd tpch_sample

# Deploy the bundle
deploy_bundle "$BUNDLE_NAME"

# Return to parent directory
cd ..

# Restore original substitutions file
restore_substitutions_file "tpch_sample/src/pipeline_configs/dev_substitutions.json"
