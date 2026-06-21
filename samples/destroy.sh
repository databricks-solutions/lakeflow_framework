#!/bin/bash
# Destroy Samples Bundle

# Source common functions and constants
source "$(dirname "$0")/common.sh"

# Parse command-line arguments using common function
parse_common_args "$@"

# Prompt for and validate common parameters
prompt_common_params

##########
# Set up Bundle Vars
setup_bundle_env "Destroy Samples" ""

##########
# Destroy Feature Samples
echo "Destroying Feature Samples Bundle"
export BUNDLE_VAR_schema="${catalog}.${schema_namespace}_feature${logical_env}"
echo "BUNDLE_VAR_schema: $BUNDLE_VAR_schema"
cd feature-samples
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..

##########
# Destroy Nodester Samples
echo "Destroying Nodester Sample Bundle"
export BUNDLE_VAR_schema="${schema_namespace}_silver${logical_env}"
echo "BUNDLE_VAR_schema: $BUNDLE_VAR_schema"
cd nodester_sample
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..

##########
# Destroy Pattern Samples
echo "Destroying Pattern Samples Bundle"
export BUNDLE_VAR_bronze_schema="${catalog}.${schema_namespace}_bronze${logical_env}"
export BUNDLE_VAR_silver_schema="${catalog}.${schema_namespace}_silver${logical_env}"
export BUNDLE_VAR_gold_schema="${catalog}.${schema_namespace}_gold${logical_env}"
echo "BUNDLE_VAR_bronze_schema: $BUNDLE_VAR_bronze_schema"
echo "BUNDLE_VAR_silver_schema: $BUNDLE_VAR_silver_schema"
echo "BUNDLE_VAR_gold_schema:   $BUNDLE_VAR_gold_schema"
cd pattern-samples
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..
