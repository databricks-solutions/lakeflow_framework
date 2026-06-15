#!/bin/bash

##########
# Main Lakeflow Framework Deployment Script
##########

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

# Display deployment summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Lakeflow Framework Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Deployment Configuration:"
echo "  - User: $user"
echo "  - Host: $host"
echo "  - Profile: $profile"
echo "  - Compute: $([ "$compute" == "0" ] && echo "Enhanced" || echo "Serverless")"
echo "  - Catalog: $catalog"
echo "  - Schema Namespace: $schema_namespace"
echo "  - Logical Environment: $logical_env"
echo ""

# Deploy Feature Samples (all framework feature demonstrations, single feature schema)
./deploy_feature_samples.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"

# Deploy Pattern Samples (end-to-end medallion patterns: bronze → silver → gold)
./deploy_pattern_samples.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"

# Note: Kafka samples are deployed as part of feature-samples but require external Kafka infrastructure.
#       Run ./deploy_feature_samples.sh separately and then trigger the kafka_samples_run_job manually.
# Note: TPCH sample is deployed separately via ./deploy_tpch.sh
# Note: YAML sample is deferred — use ./deploy_yaml.sh when ready
