#!/bin/bash

##########
# TPCH Sample Deployment and Test Script (single-catalog UC model)
#
# Separate from deploy_and_test.sh (which covers feature-samples + pattern-samples).
# Leverages common.sh for shared logic; everything tpch-specialist lives here.
#
# Deploys the tpch_sample bundle (via deploy_tpch.sh), then runs the TPCH jobs in order:
#   0 - Setup and Initialise Staging  ->  1 - Run 1 (full refresh)  ->  2 - Run 2  ->  3 - Run 3
#
# Usage:
#   ./deploy_tpch_and_test.sh -u <user> -h <host> -p <profile> -c <0|1> -l <_env> \
#       --catalog <catalog> --schema_namespace <ns> [--warehouse_id <id>] [--runs 0..3] [--skip-setup]
#
#   --warehouse_id is OPTIONAL: it backs the AI/BI Genie space and the AI/BI (Lakeview) dashboards.
#   Omit it (or leave the prompt blank) to skip both — useful if you don't have SQL warehouse access.
##########

# Sample-specific constants (tpch-specialist)
BUNDLE_NAME="TPCH Samples Bundle"
DEFAULT_TPCH_SCHEMA_NAMESPACE="tpch_sample"

# Source common library and configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# tpch-specialist options:
#   --runs       number of incremental run jobs to execute (0-3). run_1 is a full refresh,
#                runs 2-3 are incremental. 0 = deploy (+ setup) only, no processing runs.
#   --skip-setup skip the one-time setup/staging job (e.g. for a re-run on existing staging).
num_runs=3
run_setup=true

# Pre-process tpch-specific args, pass the rest to parse_common_args
common_args=()
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --runs) num_runs="$2"; shift 2 ;;
        --skip-setup) run_setup=false; shift ;;
        *) common_args+=("$1"); shift ;;
    esac
done

# Parse common arguments using the shared function from common.sh
parse_common_args "${common_args[@]}"

# tpch-specialist: default the namespace BEFORE prompting so the tpch default is used
# (and the user is not prompted) unless they passed --schema_namespace explicitly.
if [[ -z "$schema_namespace" ]]; then
    schema_namespace="$DEFAULT_TPCH_SCHEMA_NAMESPACE"
fi

# Prompt for any remaining missing parameters (shared)
prompt_common_params

# Optional: SQL warehouse id for the Genie space + AI/BI dashboards (blank = skip both).
# Resolved here once; exported + sentinel set so the deploy_tpch.sh child inherits it and
# does not prompt again.
prompt_warehouse_optional

# Validate all required parameters (shared)
if ! validate_required_params; then
    exit 1
fi

# Validate num_runs (tpch-specialist: 0-3)
if ! [[ "$num_runs" =~ ^[0-3]$ ]]; then
    log_error "Number of incremental runs must be between 0 and 3"
    exit 1
fi

# Display deployment and test summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TPCH Samples Deployment and Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Configuration:"
echo "  - User: $user"
echo "  - Host: $host"
echo "  - Profile: $profile"
echo "  - Compute: $([ "$compute" == "0" ] && echo "Classic" || echo "Serverless")"
echo "  - Catalog: $catalog"
echo "  - Schema Namespace: $schema_namespace"
echo "  - Logical Environment: $logical_env"
echo "  - Genie Space + Dashboards: $([ -n "$warehouse_id" ] && echo "yes (warehouse $warehouse_id)" || echo "skipped (no warehouse id)")"
echo "  - Run Setup Job: $([ "$run_setup" == "true" ] && echo "yes" || echo "no")"
echo "  - Number of Run Jobs: $num_runs"
echo ""

# Step 1: Deploy using deploy_tpch.sh (runs in a subshell; its env exports do not propagate)
log_info "Starting TPCH deployment..."
if ! ./deploy_tpch.sh -u "$user" -h "$host" -p "$profile" -c "$compute" -l "$logical_env" --catalog "$catalog" --schema_namespace "$schema_namespace" --warehouse_id "$warehouse_id"; then
    log_error "Deployment failed. Exiting."
    exit 1
fi
log_success "Deployment completed successfully"
echo ""

# Step 2: Re-establish the tpch bundle environment for running jobs.
# (deploy_tpch.sh ran in a subshell, so re-export here. Single catalog, per-layer schemas;
#  mirrors deploy_tpch.sh exactly.)
setup_bundle_env "$BUNDLE_NAME"
export BUNDLE_VAR_bronze_schema="${schema_namespace}_bronze_reference_data${logical_env}"
export BUNDLE_VAR_silver_schema="${schema_namespace}_silver${logical_env}"
export BUNDLE_VAR_gold_schema="${schema_namespace}_gold${logical_env}"
echo "  - BUNDLE_VAR_bronze_schema: $BUNDLE_VAR_bronze_schema"
echo "  - BUNDLE_VAR_silver_schema: $BUNDLE_VAR_silver_schema"
echo "  - BUNDLE_VAR_gold_schema:   $BUNDLE_VAR_gold_schema"
echo ""

cd "$SCRIPT_DIR/tpch_sample" || {
    log_error "Failed to change directory to tpch_sample"
    exit 1
}

# tpch-specialist: databricks.yml includes scratch/resources/*.yml, and deploy_bundle wipes
# that folder after deploying. Repopulate it (for the selected compute) so `bundle run` can
# resolve the job resource keys.
repopulate_resources() {
    rm -rf scratch/resources
    mkdir -p scratch/resources
    if [[ "$compute" == "0" ]]; then
        find resources/classic -name "*.yml" -exec cp {} scratch/resources/ \;
    else
        find resources/serverless -name "*.yml" -exec cp {} scratch/resources/ \;
    fi
}

cleanup_resources() {
    [[ -d "scratch/resources" ]] && rm -rf scratch/resources
}

run_job() {
    local label="$1"
    local job_key="$2"
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Executing $label: $job_key"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    if databricks bundle run "$job_key" -t dev --profile "$profile" 2>&1; then
        log_success "$label completed successfully"
    else
        log_error "$label failed"
        cleanup_resources
        exit 1
    fi
}

repopulate_resources

# Step 3: Setup job (0 - Setup and Initialise Staging)
if [[ "$run_setup" == "true" ]]; then
    run_job "Setup (0 - Setup and Initialise Staging)" "lakeflow_samples_tpch_setup_job"
fi

# Step 4: Run jobs sequentially (run_1 full refresh, run_2/run_3 incremental)
declare -a job_keys=(
    "lakeflow_samples_tpch_run_1_job"
    "lakeflow_samples_tpch_run_2_job"
    "lakeflow_samples_tpch_run_3_job"
)

for ((i=1; i<=num_runs; i++)); do
    run_job "TPCH Run $i" "${job_keys[$((i-1))]}"
done

cleanup_resources

cd "$SCRIPT_DIR" || exit 1
unset MSYS_NO_PATHCONV

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "All TPCH operations completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
