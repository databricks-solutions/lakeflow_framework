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
# Destroy Test Data and Orchestrator
echo "Destroying Test Data and Orchestrator Bundle"
cd test_data_and_orchestrator
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..

##########
# Destroy Bronze Samples
echo "Destroying Bronze Sample Bundle"
export BUNDLE_VAR_schema="${catalog}.${schema_namespace}_bronze${logical_env}"
echo "BUNDLE_VAR_schema: $BUNDLE_VAR_schema"
cd bronze_sample
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..

##########
# Destroy Silver Samples
echo "Destroying Silver Sample Bundle"
export BUNDLE_VAR_schema="${catalog}.${schema_namespace}_silver${logical_env}"
echo "BUNDLE_VAR_schema: $BUNDLE_VAR_schema"
cd silver_sample
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..

##########
# Destroy Gold Samples
echo "Destroying Gold Sample Bundle"
export BUNDLE_VAR_schema="${catalog}.${schema_namespace}_gold${logical_env}"
echo "BUNDLE_VAR_schema: $BUNDLE_VAR_schema"
cd gold_sample
databricks bundle destroy -t dev --profile "$profile" --auto-approve
echo ""
cd ..
