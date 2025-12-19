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
        cp resources/classic/*.yml scratch/resources/
    else
        log_info "Deploying to serverless-compute target"
        mkdir -p scratch/resources
        cp resources/serverless/*.yml scratch/resources/
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
        sed -i '' "s|staging_schema:.*|staging_schema: $catalog.${schema_namespace}_staging${logical_env}|" "$substitutions_file"
        
        # Update bronze_schema
        sed -i '' "s|bronze_schema:.*|bronze_schema: $catalog.${schema_namespace}_bronze${logical_env}|" "$substitutions_file"
        
        # Update silver_schema
        sed -i '' "s|silver_schema:.*|silver_schema: $catalog.${schema_namespace}_silver${logical_env}|" "$substitutions_file"
        
        # Update gold_schema (if present)
        sed -i '' "s|gold_schema:.*|gold_schema: $catalog.${schema_namespace}_gold${logical_env}|" "$substitutions_file"
        
        # Update dpm_schema (if present)
        sed -i '' "s|dpm_schema:.*|dpm_schema: $catalog.${schema_namespace}_dpm${logical_env}|" "$substitutions_file"
        
        # Update sample_file_location
        sed -i '' "s|sample_file_location:.*|sample_file_location: /Volumes/$catalog/${schema_namespace}_staging${logical_env}/stg_volume|" "$substitutions_file"
    else
        # JSON format: "key": "value"
        log_info "Detected JSON format"
        
        # Update staging_schema
        sed -i '' "s|\"staging_schema\": \"[^\"]*\"|\"staging_schema\": \"$catalog.${schema_namespace}_staging${logical_env}\"|" "$substitutions_file"
        
        # Update bronze_schema
        sed -i '' "s|\"bronze_schema\": \"[^\"]*\"|\"bronze_schema\": \"$catalog.${schema_namespace}_bronze${logical_env}\"|" "$substitutions_file"
        
        # Update silver_schema
        sed -i '' "s|\"silver_schema\": \"[^\"]*\"|\"silver_schema\": \"$catalog.${schema_namespace}_silver${logical_env}\"|" "$substitutions_file"
        
        # Update gold_schema
        sed -i '' "s|\"gold_schema\": \"[^\"]*\"|\"gold_schema\": \"$catalog.${schema_namespace}_gold${logical_env}\"|" "$substitutions_file"
        
        # Update dpm_schema
        sed -i '' "s|\"dpm_schema\": \"[^\"]*\"|\"dpm_schema\": \"$catalog.${schema_namespace}_dpm${logical_env}\"|" "$substitutions_file"
        
        # Update sample_file_location
        sed -i '' "s|\"sample_file_location\": \"[^\"]*\"|\"sample_file_location\": \"/Volumes/$catalog/${schema_namespace}_staging${logical_env}/stg_volume\"|" "$substitutions_file"
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