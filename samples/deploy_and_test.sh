#!/bin/bash

##########
# Lakeflow Framework Deployment and Test Script
##########

# Source common library and configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Additional variable for number of runs
num_runs=4

# Pre-process arguments to extract --runs and build array for common args
common_args=()
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --runs)
            num_runs="$2"
            shift 2
            ;;
        *)
            common_args+=("$1")
            shift
            ;;
    esac
done

# Parse common arguments using the function from common.sh
parse_common_args "${common_args[@]}"

# Prompt for missing parameters
prompt_common_params

# Validate all required parameters
if ! validate_required_params; then
    exit 1
fi

# Validate num_runs
if ! [[ "$num_runs" =~ ^[1-4]$ ]]; then
    log_error "Number of runs must be between 1 and 4"
    exit 1
fi

# Display deployment and test summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Lakeflow Framework Deployment and Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Configuration:"
echo "  - User: $user"
echo "  - Host: $host"
echo "  - Profile: $profile"
echo "  - Compute: $([ "$compute" == "0" ] && echo "Enhanced" || echo "Serverless")"
echo "  - Catalog: $catalog"
echo "  - Schema Namespace: $schema_namespace"
echo "  - Logical Environment: $logical_env"
echo "  - Number of Runs: $num_runs"
echo ""

# Step 1: Deploy using deploy.sh
log_info "Starting deployment..."
./deploy.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"

# if [ $? -ne 0 ]; then
#     log_error "Deployment failed. Exiting."
#     exit 1
# fi

log_success "Deployment completed successfully"
echo ""

# Step 2: Execute run jobs sequentially
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Executing Run Jobs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Change to the test_data_and_orchestrator directory
cd "$SCRIPT_DIR/test_data_and_orchestrator" || {
    log_error "Failed to change directory to test_data_and_orchestrator"
    exit 1
}

# Job keys for each run
declare -a job_keys=(
    "lakeflow_samples_day_1_load_and_schema_initialization"
    "lakeflow_samples_day_2_load"
    "lakeflow_samples_day_3_load"
    "lakeflow_samples_day_4_load"
)

# Execute each run job
for ((i=1; i<=num_runs; i++)); do
    job_key="${job_keys[$((i-1))]}"
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Executing Run $i: $job_key"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Run the job and wait for completion
    if databricks bundle run "$job_key" --profile "$profile" --var logical_env="$logical_env" 2>&1; then
        log_success "Run $i completed successfully"
    else
        log_error "Run $i failed"
        exit 1
    fi
    
    echo ""
done

# Return to original directory
cd "$SCRIPT_DIR" || exit 1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "All operations completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
