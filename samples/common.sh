#!/bin/bash

##########
# Common Library and Configuration for Lakeflow Framework Sample Deployments
##########

# Configuration Constants
DEFAULT_SCHEMA_NAMESPACE="lakeflow_samples"
DEFAULT_PROFILE="DEFAULT"
DEFAULT_COMPUTE="1"  # Serverless
DEFAULT_CATALOG="main"
FRAMEWORK_NAME="lakeflow_framework"
FRAMEWORK_TARGET="dev"

# Common Variables
user=""
host=""
compute=""
profile=""
catalog=""
logical_env=""
# Optional SQL warehouse id (tpch: backs the Genie space). Preserve an inherited value so a
# parent script (e.g. deploy_tpch_and_test.sh) can resolve it once and pass it to child scripts.
warehouse_id="${warehouse_id:-}"
# Set when --warehouse_id was passed explicitly (even as ""), so we don't prompt for it.
warehouse_id_set=""
# Sentinel: when set, the optional warehouse prompt is skipped (already resolved by a parent).
TPCH_WAREHOUSE_RESOLVED="${TPCH_WAREHOUSE_RESOLVED:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse common command-line arguments
parse_common_args() {
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -u|--user) user="$2"
            shift ;;
            -h|--host) host="$2"
            shift ;;
            -c|--compute) compute="$2"
            shift ;;
            -p|--profile) profile="$2"
            shift ;;
            -l|--logical_env) logical_env="$2"
            shift ;;
            --catalog) catalog="$2"
            shift ;;
            --schema) schema="$2"
            shift ;;
            --schema_namespace) schema_namespace="$2"
            shift ;;
            --warehouse_id) warehouse_id="$2"; warehouse_id_set=1
            shift ;;
            *) echo "Unknown parameter: $1"; exit 1 ;;
        esac
        shift
    done
}

# Prompt for and validate common parameters
prompt_common_params() {
    # Prompt for and validate user if not provided
    [[ -z "$user" ]] && read -p "Databricks username: " user
    [[ -z "$user" ]] && { log_error "Databricks username is required."; exit 1; }

    # Prompt for and validate workspace_host if not provided
    [[ -z "$host" ]] && read -p "Databricks workspace host: " host
    [[ -z "$host" ]] && { log_error "Databricks workspace host is required."; exit 1; }

    # Prompt for and validate profile if not provided
    [[ -z "$profile" ]] && read -p "Databricks CLI profile (default: $DEFAULT_PROFILE): " profile
    profile=${profile:-$DEFAULT_PROFILE}

    # Prompt for and validate compute if not provided
    [[ -z "$compute" ]] && read -p "Select Compute (0=Classic, 1=Serverless, default: $DEFAULT_COMPUTE): " compute
    compute=${compute:-$DEFAULT_COMPUTE}

    # Validate compute input
    while [[ "$compute" != "1" && "$compute" != "0" ]]; do
        read -p "Please select from (0=Classic, 1=Serverless): " compute
    done

    # Prompt for and validate catalog if not provided
    [[ -z "$catalog" ]] && read -p "UC catalog (default: $DEFAULT_CATALOG): " catalog
    catalog=${catalog:-$DEFAULT_CATALOG}

    # Prompt for and validate schema_namespace if not provided
    [[ -z "$schema_namespace" ]] && read -p "Schema Namespace (default: $DEFAULT_SCHEMA_NAMESPACE): " schema_namespace
    schema_namespace=${schema_namespace:-${DEFAULT_SCHEMA_NAMESPACE}}

    # Prompt for logical_env if not provided
    [[ -z "$logical_env" ]] && read -p "Logical environment (should start with '_'): " logical_env
}

# Optional prompt for a SQL warehouse id that backs the TPC-H Genie space.
# Genie deployment is OPTIONAL: some users don't have access to a SQL warehouse. Leaving the
# warehouse id blank simply skips Genie-space creation; the rest of the sample is unaffected.
# The prompt is skipped when TPCH_WAREHOUSE_RESOLVED is set (a parent script already resolved it).
prompt_warehouse_optional() {
    # Already resolved (and possibly intentionally left blank) by a parent script — don't re-ask.
    [[ -n "$TPCH_WAREHOUSE_RESOLVED" ]] && return 0

    # Prompt only in an interactive terminal, when no value was supplied and none was passed
    # explicitly via --warehouse_id. This keeps non-interactive / single-command / CI runs from
    # blocking on input (they simply skip Genie unless --warehouse_id was given).
    if [[ -z "$warehouse_id" && -z "$warehouse_id_set" && -t 0 ]]; then
        echo ""
        echo "Optional — AI/BI Genie space:"
        echo "  This sample can deploy a Genie space over the gold schema for natural-language"
        echo "  analytics. It requires a SQL warehouse id. If you don't have access to a SQL"
        echo "  warehouse, leave this blank to SKIP Genie deployment — everything else still"
        echo "  deploys and runs normally."
        read -p "SQL warehouse id for Genie (optional, blank = skip): " warehouse_id
    fi

    if [[ -z "$warehouse_id" ]]; then
        log_info "No SQL warehouse id provided — Genie space deployment will be skipped."
    else
        log_info "Genie space will be deployed against SQL warehouse: $warehouse_id"
    fi

    # Mark as resolved so any child script we invoke inherits the decision and won't re-prompt.
    export warehouse_id
    export TPCH_WAREHOUSE_RESOLVED=1
}

# Trash any Genie space(s) whose title matches, via the Databricks CLI. Idempotent and
# best-effort: safe when no space exists, and never aborts the caller (always returns 0).
# The Genie space is created imperatively (not a bundle resource), so `bundle destroy` cannot
# remove it — this is how destroy_tpch.sh cleans it up. Args: <title> <profile>.
trash_genie_spaces_by_title() {
    local title="$1"
    local prof="$2"

    if ! command -v databricks >/dev/null 2>&1; then
        log_warning "databricks CLI not found; skipping Genie space cleanup"
        return 0
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        log_warning "python3 not found; skipping Genie space cleanup"
        return 0
    fi

    log_info "Checking for Genie space to remove: $title"
    local token="" found=0
    while :; do
        local page
        if [[ -n "$token" ]]; then
            page=$(databricks genie list-spaces -o json --page-size 100 --page-token "$token" --profile "$prof" 2>/dev/null)
        else
            page=$(databricks genie list-spaces -o json --page-size 100 --profile "$prof" 2>/dev/null)
        fi
        [[ -z "$page" ]] && break

        local ids
        ids=$(printf '%s' "$page" | python3 -c 'import sys,json
d=json.load(sys.stdin)
for s in (d.get("spaces") or []):
    if s.get("title")==sys.argv[1]: print(s.get("space_id"))' "$title" 2>/dev/null)

        local id
        for id in $ids; do
            if databricks genie trash-space "$id" --profile "$prof" >/dev/null 2>&1; then
                log_success "Trashed Genie space $id ($title)"
                found=$((found+1))
            else
                log_warning "Failed to trash Genie space $id (trash it manually in the Genie UI)"
            fi
        done

        token=$(printf '%s' "$page" | python3 -c 'import sys,json
print(json.load(sys.stdin).get("next_page_token") or "")' 2>/dev/null)
        [[ -z "$token" ]] && break
    done

    [[ "$found" -eq 0 ]] && log_info "No Genie space titled '$title' found — nothing to remove."
    return 0
}

# Set up common bundle environment variables
setup_bundle_env() {
    local bundle_name="$1"
    local schema="$2"
    
    # In case of Git Bash, disable MSYS2 path conversion
    export MSYS_NO_PATHCONV=1
    
    # Set up Bundle Vars
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$bundle_name Deployment"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Bundle Environment:"
    
    export BUNDLE_VAR_logical_env=$logical_env
    echo "  - BUNDLE_VAR_logical_env: $BUNDLE_VAR_logical_env"
    
    export BUNDLE_VAR_catalog=$catalog
    echo "  - BUNDLE_VAR_catalog: $BUNDLE_VAR_catalog"
    
    if [[ -n "$schema" ]]; then
        export BUNDLE_VAR_schema=$schema
        echo "  - BUNDLE_VAR_schema: $BUNDLE_VAR_schema"
    fi
    
    if [[ -n "$schema_namespace" ]]; then
        export BUNDLE_VAR_schema_namespace=$schema_namespace
        echo "  - BUNDLE_VAR_schema_namespace: $BUNDLE_VAR_schema_namespace"
    fi
    
    # Use framework constants from config.sh
    export BUNDLE_VAR_framework_source_path="/Workspace/Users/$user/.bundle/$FRAMEWORK_NAME/$FRAMEWORK_TARGET/current/files/src"
    echo "  - BUNDLE_VAR_framework_source_path: $BUNDLE_VAR_framework_source_path"
    
    export BUNDLE_VAR_workspace_host=$host
    echo "  - BUNDLE_VAR_workspace_host: $BUNDLE_VAR_workspace_host"

    # Optional: only export when a warehouse id was supplied. When empty, the bundle's
    # warehouse_id default ("") is used and the Genie-space step no-ops.
    if [[ -n "$warehouse_id" ]]; then
        export BUNDLE_VAR_warehouse_id=$warehouse_id
        echo "  - BUNDLE_VAR_warehouse_id: $BUNDLE_VAR_warehouse_id"
    fi

    echo ""
}

# Deploy bundle with compute-specific resources
deploy_bundle() {
    local bundle_name="$1"
    
    log_info "Deploying $bundle_name"
    
    # Remove resources subfolder under scratch if it exists
    if [[ -d "scratch/resources" ]]; then
        rm -rf scratch/resources
    fi
    
    # Copy resource files to scratch folder based on compute setting
    if [[ "$compute" == "0" ]]; then
        log_info "Deploying to classic-compute target"
        mkdir -p scratch/resources
        find resources/classic -name "*.yml" -exec cp {} scratch/resources/ \;
    else
        log_info "Deploying to serverless-compute target"
        mkdir -p scratch/resources
        find resources/serverless -name "*.yml" -exec cp {} scratch/resources/ \;
    fi
    
    # Deploy the bundle
    if databricks bundle deploy -t dev --profile "$profile"; then
        log_success "$bundle_name deployed successfully"
    else
        log_error "Failed to deploy $bundle_name"
        return 1
    fi
    
    # Clean up resources
    if [[ -d "scratch/resources" ]]; then
        rm -rf scratch/resources
    fi
    
    echo ""
    
    # In case of Git Bash, remove unset MSYS_NO_PATHCONV variable
    unset MSYS_NO_PATHCONV
}

# Validate required parameters
validate_required_params() {
    local missing_params=()
    
    [[ -z "$user" ]] && missing_params+=("user")
    [[ -z "$host" ]] && missing_params+=("host")
    [[ -z "$compute" ]] && missing_params+=("compute")
    [[ -z "$profile" ]] && missing_params+=("profile")
    [[ -z "$catalog" ]] && missing_params+=("catalog")
    [[ -z "$schema_namespace" ]] && missing_params+=("schema_namespace")
    [[ -z "$logical_env" ]] && missing_params+=("logical_env")
    
    if [[ ${#missing_params[@]} -gt 0 ]]; then
        log_error "Missing required parameters: ${missing_params[*]}"
        return 1
    fi
    
    return 0
}

# Function to update substitutions file with catalog and schema namespace
update_substitutions_file() {
    local substitutions_file="$1"
    
    # Only update if using non-default values
    if [[ "$catalog" == "$DEFAULT_CATALOG" && "$schema_namespace" == "$DEFAULT_SCHEMA_NAMESPACE" ]]; then
        return 0
    fi
    
    log_info "Updating substitutions file: $substitutions_file"
    log_info "Using catalog: $catalog (default: $DEFAULT_CATALOG), schema namespace: $schema_namespace (default: $DEFAULT_SCHEMA_NAMESPACE)"
    
    # Check if file exists
    if [[ ! -f "$substitutions_file" ]]; then
        log_error "Substitutions file not found: $substitutions_file"
        return 1
    fi
    
    # Handle backup file - the .backup file is the master original and must be preserved
    if [[ -f "${substitutions_file}.backup" ]]; then
        # A backup already exists from a previous run (possibly failed)
        # The .backup is the original master - restore from it first to ensure clean state
        log_warning "Existing backup found from previous run, restoring original before proceeding"
        cp "${substitutions_file}.backup" "$substitutions_file"
        log_info "Restored original from existing backup: ${substitutions_file}.backup"
    else
        # No backup exists - create one from the current file
        cp "$substitutions_file" "${substitutions_file}.backup"
        log_info "Created backup: ${substitutions_file}.backup"
    fi
    
    # Detect file format (YAML vs JSON) and use appropriate sed patterns
    if [[ "$substitutions_file" == *.yaml || "$substitutions_file" == *.yml ]]; then
        # YAML format: key: value (with 2-space indent under tokens:)
        log_info "Detected YAML format"
        
        # Update staging_schema
        perl -i -pe "s|staging_schema:.*|staging_schema: $catalog.${schema_namespace}_staging${logical_env}|" "$substitutions_file"
        
        # Update bronze_schema
        perl -i -pe "s|bronze_schema:.*|bronze_schema: $catalog.${schema_namespace}_bronze${logical_env}|" "$substitutions_file"
        
        # Update silver_schema
        perl -i -pe "s|silver_schema:.*|silver_schema: $catalog.${schema_namespace}_silver${logical_env}|" "$substitutions_file"
        
        # Update gold_schema (if present)
        perl -i -pe "s|gold_schema:.*|gold_schema: $catalog.${schema_namespace}_gold${logical_env}|" "$substitutions_file"
        
        # Update dpm_schema (if present)
        perl -i -pe "s|dpm_schema:.*|dpm_schema: $catalog.${schema_namespace}_dpm${logical_env}|" "$substitutions_file"

        # Update feature_schema (if present — feature-samples bundle)
        perl -i -pe "s|feature_schema:.*|feature_schema: $catalog.${schema_namespace}_feature${logical_env}|" "$substitutions_file"

        # Update sample_file_location — handles both _staging and _feature volume paths
        perl -i -pe "s|sample_file_location:.*staging.*|sample_file_location: /Volumes/$catalog/${schema_namespace}_staging${logical_env}/stg_volume|" "$substitutions_file"
        perl -i -pe "s|sample_file_location:.*feature.*|sample_file_location: /Volumes/$catalog/${schema_namespace}_feature${logical_env}/stg_volume|" "$substitutions_file"
    else
        # JSON format: "key": "value"
        log_info "Detected JSON format"
        
        # Update staging_schema
        perl -i -pe "s|\"staging_schema\": \"[^\"]*\"|\"staging_schema\": \"$catalog.${schema_namespace}_staging${logical_env}\"|" "$substitutions_file"
        
        # Update bronze_schema
        perl -i -pe "s|\"bronze_schema\": \"[^\"]*\"|\"bronze_schema\": \"$catalog.${schema_namespace}_bronze${logical_env}\"|" "$substitutions_file"
        
        # Update silver_schema
        perl -i -pe "s|\"silver_schema\": \"[^\"]*\"|\"silver_schema\": \"$catalog.${schema_namespace}_silver${logical_env}\"|" "$substitutions_file"
        
        # Update gold_schema
        perl -i -pe "s|\"gold_schema\": \"[^\"]*\"|\"gold_schema\": \"$catalog.${schema_namespace}_gold${logical_env}\"|" "$substitutions_file"
        
        # Update dpm_schema (if present)
        perl -i -pe "s|\"dpm_schema\": \"[^\"]*\"|\"dpm_schema\": \"$catalog.${schema_namespace}_dpm${logical_env}\"|" "$substitutions_file"

        # Update feature_schema (if present — feature-samples bundle)
        perl -i -pe "s|\"feature_schema\": \"[^\"]*\"|\"feature_schema\": \"$catalog.${schema_namespace}_feature${logical_env}\"|" "$substitutions_file"

        # Update sample_file_location — handles both _staging and _feature volume paths
        perl -i -pe "s|\"sample_file_location\": \"[^/]*/[^/]*/[^_]*_staging[^\"]*\"|\"sample_file_location\": \"/Volumes/$catalog/${schema_namespace}_staging${logical_env}/stg_volume\"|" "$substitutions_file"
        perl -i -pe "s|\"sample_file_location\": \"[^/]*/[^/]*/[^_]*_feature[^\"]*\"|\"sample_file_location\": \"/Volumes/$catalog/${schema_namespace}_feature${logical_env}/stg_volume\"|" "$substitutions_file"
    fi
    
    log_success "Successfully updated substitutions file"
    # Set flag to indicate file was modified
    export SUBSTITUTIONS_FILE_MODIFIED=true
    
    # Display the updated content
    log_info "Updated substitutions file content:"
    cat "$substitutions_file"
    echo ""
}

# Function to restore substitutions file from backup
restore_substitutions_file() {
    local substitutions_file="$1"
    
    # Only restore if file was actually modified (backup exists and flag is set)
    if [[ -f "${substitutions_file}.backup" && "$SUBSTITUTIONS_FILE_MODIFIED" == "true" ]]; then
        log_info "Restoring original substitutions file"
        cp "${substitutions_file}.backup" "$substitutions_file"
        rm -f "${substitutions_file}.backup"
        log_success "Restored original substitutions file"
        # Clear the flag
        unset SUBSTITUTIONS_FILE_MODIFIED
    fi
}

# Function to update substitutions for the TPC-H sample (single-catalog model).
# The tpch sample keeps every medallion layer in ONE catalog, separated by schema
# (tpch_sample_<layer>[_<source>]{logical_env}). The schema tokens carry both the catalog
# prefix ("main.") and the namespace prefix ("tpch_sample") plus the {logical_env}
# placeholder, which the framework resolves at runtime from the pipeline's logicalEnv config.
# Only the catalog and/or namespace prefixes are rewritten when non-default values are supplied.
update_tpch_substitutions_file() {
    local substitutions_file="$1"
    local default_namespace="tpch_sample"
    local default_catalog="$DEFAULT_CATALOG"

    # Both at defaults — values already baked into the file; nothing to rewrite.
    if [[ "$catalog" == "$default_catalog" && "$schema_namespace" == "$default_namespace" ]]; then
        return 0
    fi

    log_info "Updating tpch substitutions file: $substitutions_file"
    log_info "Using catalog: $catalog (default: $default_catalog), schema namespace: $schema_namespace (default: $default_namespace)"

    if [[ ! -f "$substitutions_file" ]]; then
        log_error "Substitutions file not found: $substitutions_file"
        return 1
    fi

    # Preserve the original master via .backup (same convention as update_substitutions_file)
    if [[ -f "${substitutions_file}.backup" ]]; then
        log_warning "Existing backup found from previous run, restoring original before proceeding"
        cp "${substitutions_file}.backup" "$substitutions_file"
    else
        cp "$substitutions_file" "${substitutions_file}.backup"
        log_info "Created backup: ${substitutions_file}.backup"
    fi

    # Rewrite the catalog prefix: the leading "main." in schema tokens and the /Volumes/main/ path.
    if [[ "$catalog" != "$default_catalog" ]]; then
        perl -i -pe "s|\"${default_catalog}\.|\"${catalog}.|g" "$substitutions_file"
        perl -i -pe "s|/Volumes/${default_catalog}/|/Volumes/${catalog}/|g" "$substitutions_file"
    fi

    # Rewrite the namespace prefix across all schema tokens and the volume path.
    if [[ "$schema_namespace" != "$default_namespace" ]]; then
        perl -i -pe "s|${default_namespace}|${schema_namespace}|g" "$substitutions_file"
    fi

    log_success "Successfully updated tpch substitutions file"
    export SUBSTITUTIONS_FILE_MODIFIED=true

    log_info "Updated substitutions file content:"
    cat "$substitutions_file"
    echo ""
}

# Function to update pipeline bundle global.json|yaml with table_migration_state_volume_path (same catalog/schema rules as substitutions)
update_pipeline_global_config_file() {
    local global_config_file="$1"
    local checkpoint_path="/Volumes/$catalog/${schema_namespace}_staging${logical_env}/stg_volume/checkpoint_state"

    # Only update if using non-default values (match update_substitutions_file)
    if [[ "$catalog" == "$DEFAULT_CATALOG" && "$schema_namespace" == "$DEFAULT_SCHEMA_NAMESPACE" ]]; then
        return 0
    fi

    if [[ ! -f "$global_config_file" ]]; then
        log_error "Pipeline global config file not found: $global_config_file"
        return 1
    fi

    if ! grep -q 'table_migration_state_volume_path' "$global_config_file"; then
        log_info "No table_migration_state_volume_path in $global_config_file, skipping global config update"
        return 0
    fi

    log_info "Updating pipeline global config: $global_config_file"
    log_info "Using table_migration_state_volume_path: $checkpoint_path"

    if [[ -f "${global_config_file}.backup" ]]; then
        log_warning "Existing backup found from previous run, restoring original before proceeding"
        cp "${global_config_file}.backup" "$global_config_file"
        log_info "Restored original from existing backup: ${global_config_file}.backup"
    else
        cp "$global_config_file" "${global_config_file}.backup"
        log_info "Created backup: ${global_config_file}.backup"
    fi

    if [[ "$global_config_file" == *.yaml || "$global_config_file" == *.yml ]]; then
        log_info "Detected YAML format for global config"
        perl -i -pe "s|table_migration_state_volume_path:.*|table_migration_state_volume_path: $checkpoint_path|" "$global_config_file"
    else
        log_info "Detected JSON format for global config"
        perl -i -pe "s|\"table_migration_state_volume_path\": \"[^\"]*\"|\"table_migration_state_volume_path\": \"$checkpoint_path\"|" "$global_config_file"
    fi

    log_success "Successfully updated pipeline global config file"
    export PIPELINE_GLOBAL_CONFIG_MODIFIED=true

    log_info "Updated pipeline global config content:"
    cat "$global_config_file"
    echo ""
}

# Function to restore pipeline global config from backup
restore_pipeline_global_config_file() {
    local global_config_file="$1"

    if [[ -f "${global_config_file}.backup" && "$PIPELINE_GLOBAL_CONFIG_MODIFIED" == "true" ]]; then
        log_info "Restoring original pipeline global config file"
        cp "${global_config_file}.backup" "$global_config_file"
        rm -f "${global_config_file}.backup"
        log_success "Restored original pipeline global config file"
        unset PIPELINE_GLOBAL_CONFIG_MODIFIED
    fi
}