#!/bin/bash

##########
# Lakeflow Framework Deployment and Test Script
#
# Deploys feature-samples and pattern-samples (via deploy.sh), then runs
# feature_samples_run_job and the pattern-samples orchestrator jobs (4-day load).
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
echo "  - Run Feature Samples Job: yes"
echo "  - Number of Pattern Runs: $num_runs"
echo ""

# Step 1: Deploy using deploy.sh (feature-samples + pattern-samples)
log_info "Starting deployment..."
if ! ./deploy.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace"; then
    log_error "Deployment failed. Exiting."
    exit 1
fi

log_success "Deployment completed successfully"
echo ""

# Step 2: Execute feature-samples run job
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Executing Feature Samples Run Job"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

feature_schema="${schema_namespace}_feature${logical_env}"
setup_bundle_env "Feature Samples Test Run" "$feature_schema"

cd "$SCRIPT_DIR/feature-samples" || {
    log_error "Failed to change directory to feature-samples"
    exit 1
}

log_info "Running feature_samples_run_job..."
if databricks bundle run feature_samples_run_job -t dev --profile "$profile" 2>&1; then
    log_success "Feature samples run completed successfully"
else
    log_error "Feature samples run failed"
    exit 1
fi

cd "$SCRIPT_DIR" || exit 1
echo ""

# Step 3: Execute pattern-samples run jobs sequentially
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Executing Pattern Samples Run Jobs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Bundle vars for pattern-samples (same as deploy_pattern_samples.sh)
setup_bundle_env "Pattern Samples Test Run" ""
unset BUNDLE_VAR_schema
export BUNDLE_VAR_bronze_schema="${schema_namespace}_bronze${logical_env}"
export BUNDLE_VAR_silver_schema="${schema_namespace}_silver${logical_env}"
export BUNDLE_VAR_gold_schema="${schema_namespace}_gold${logical_env}"

cd "$SCRIPT_DIR/pattern-samples" || {
    log_error "Failed to change directory to pattern-samples"
    exit 1
}

# Job resource keys (see pattern-samples/resources/*/jobs/pattern_samples_run_*_job.yml)
declare -a job_keys=(
    "pattern_samples_run_1_job"
    "pattern_samples_run_2_job"
    "pattern_samples_run_3_job"
    "pattern_samples_run_4_job"
)

# Execute each run job
for ((i=1; i<=num_runs; i++)); do
    job_key="${job_keys[$((i-1))]}"

    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Executing Pattern Run $i: $job_key"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if databricks bundle run "$job_key" -t dev --profile "$profile" 2>&1; then
        log_success "Pattern run $i completed successfully"
    else
        log_error "Pattern run $i failed"
        exit 1
    fi

    echo ""
done

cd "$SCRIPT_DIR" || exit 1

# Step 4: Execute nodespec samples run job (reads from staging/bronze created by pattern run 1)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Executing Nodespec Samples Run Job"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

nodespec_schema="${schema_namespace}_silver${logical_env}"
setup_bundle_env "Nodespec Samples Test Run" "$nodespec_schema"

cd "$SCRIPT_DIR/nodespec_sample" || {
    log_error "Failed to change directory to nodespec_sample"
    exit 1
}

log_info "Running nodespec_samples_run_job..."
if databricks bundle run nodespec_samples_run_job -t dev --profile "$profile" 2>&1; then
    log_success "Nodespec samples run completed successfully"
else
    log_error "Nodespec samples run failed"
    exit 1
fi

cd "$SCRIPT_DIR" || exit 1
unset MSYS_NO_PATHCONV

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "All operations completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
