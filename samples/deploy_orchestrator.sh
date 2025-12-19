#!/bin/bash
# Test Data and Orchestrator Bundle Deployment

# Sample-specific constants
BUNDLE_NAME="Test Data and Orchestrator Bundle"

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
    schema_namespace="$DEFAULT_SCHEMA_NAMESPACE"
fi

# Set up bundle environment with all schemas
setup_bundle_env "$BUNDLE_NAME"

# Change to test_data_and_orchestrator directory for deployment
cd test_data_and_orchestrator

# Deploy the bundle
deploy_bundle "$BUNDLE_NAME"

# Return to parent directory
cd ..