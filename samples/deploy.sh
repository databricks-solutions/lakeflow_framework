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

# Deploy Bronze Sample
./deploy_bronze.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"

# Deploy Silver Sample
./deploy_silver.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"

# Deploy Gold Sample
./deploy_gold.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"

# Deploy YAML Sample
./deploy_yaml.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"

# Deploy test data and orchestrator
./deploy_orchestrator.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"
