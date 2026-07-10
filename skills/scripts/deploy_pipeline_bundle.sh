#!/usr/bin/env bash
# Deploy a Lakeflow Framework pipeline bundle to a Databricks workspace.
#
# Usage:
#   ./deploy_pipeline_bundle.sh -b <bundle_path> [options]
#
# Options:
#   -b, --bundle       Path to the pipeline bundle directory (required)
#   -t, --target       DABs target environment (default: dev)
#   -p, --profile      Databricks CLI profile (default: DEFAULT)
#   -r, --run          Also run the pipeline after deployment
#   --pipeline-name    Pipeline name to run (required with -r, auto-detected if single)
#   --destroy          Destroy the bundle instead of deploying
#   -h, --help         Show this help message

set -euo pipefail

BUNDLE_PATH=""
TARGET="dev"
PROFILE="DEFAULT"
RUN=false
PIPELINE_NAME=""
DESTROY=false

usage() {
    echo "Usage: $0 -b <bundle_path> [-t target] [-p profile] [-r] [--pipeline-name name]"
    echo ""
    echo "  -b, --bundle         Pipeline bundle directory (required)"
    echo "  -t, --target         DABs target (default: dev)"
    echo "  -p, --profile        Databricks CLI profile (default: DEFAULT)"
    echo "  -r, --run            Run pipeline after deploy"
    echo "  --pipeline-name      Pipeline to run (auto-detected if single)"
    echo "  --destroy            Destroy bundle instead of deploy"
    echo "  -h, --help           Show help"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -b|--bundle) BUNDLE_PATH="$2"; shift 2 ;;
        -t|--target) TARGET="$2"; shift 2 ;;
        -p|--profile) PROFILE="$2"; shift 2 ;;
        -r|--run) RUN=true; shift ;;
        --pipeline-name) PIPELINE_NAME="$2"; shift 2 ;;
        --destroy) DESTROY=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [ -z "$BUNDLE_PATH" ]; then
    echo "Error: --bundle is required"
    usage
fi

if [ ! -d "$BUNDLE_PATH" ]; then
    echo "Error: Bundle directory not found: $BUNDLE_PATH"
    exit 1
fi

if [ ! -f "$BUNDLE_PATH/databricks.yml" ]; then
    echo "Error: No databricks.yml found in $BUNDLE_PATH"
    exit 1
fi

cd "$BUNDLE_PATH"

echo "=== Lakeflow Pipeline Bundle ==="
echo "  Bundle: $(basename "$BUNDLE_PATH")"
echo "  Target: $TARGET"
echo "  Profile: $PROFILE"
echo ""

if $DESTROY; then
    echo "Destroying bundle..."
    databricks bundle destroy -t "$TARGET" -p "$PROFILE" --auto-approve
    echo "Bundle destroyed."
    exit 0
fi

echo "Validating bundle..."
if ! databricks bundle validate -t "$TARGET" -p "$PROFILE"; then
    echo ""
    echo "Validation failed. Fix the errors above and retry."
    exit 1
fi

echo ""
echo "Deploying bundle..."
databricks bundle deploy -t "$TARGET" -p "$PROFILE"

echo ""
echo "=== Bundle deployed successfully ==="

if $RUN; then
    if [ -z "$PIPELINE_NAME" ]; then
        RESOURCE_FILES=$(ls resources/*.yml 2>/dev/null | head -1)
        if [ -n "$RESOURCE_FILES" ]; then
            PIPELINE_NAME=$(grep -m1 'name:' "$RESOURCE_FILES" | head -1 | sed 's/.*name: *//' | tr -d '"' | tr -d "'")
        fi
    fi

    if [ -n "$PIPELINE_NAME" ]; then
        echo ""
        echo "Running pipeline: $PIPELINE_NAME"
        databricks bundle run -t "$TARGET" -p "$PROFILE" "$PIPELINE_NAME"
    else
        echo ""
        echo "Could not auto-detect pipeline name. Run manually:"
        echo "  databricks bundle run -t $TARGET <pipeline_name>"
    fi
fi
