#!/usr/bin/env bash
# Deploy the Lakeflow Framework bundle to a Databricks workspace.
#
# Prerequisites:
#   - Databricks CLI installed and configured
#   - Git installed
#
# Usage:
#   ./deploy_framework.sh [options]
#
# Options:
#   -t, --target       DABs target environment (default: dev)
#   -v, --version      Framework version tag (default: current)
#   -p, --profile      Databricks CLI profile (default: DEFAULT)
#   -d, --dir          Directory to clone into (default: /tmp/lakeflow_framework)
#   -h, --help         Show this help message

set -euo pipefail

TARGET="dev"
VERSION="current"
PROFILE="DEFAULT"
CLONE_DIR="/tmp/lakeflow_framework"

usage() {
    echo "Usage: $0 [-t target] [-v version] [-p profile] [-d dir]"
    echo ""
    echo "  -t, --target    DABs target (default: dev)"
    echo "  -v, --version   Framework version (default: current)"
    echo "  -p, --profile   Databricks CLI profile (default: DEFAULT)"
    echo "  -d, --dir       Clone directory (default: /tmp/lakeflow_framework)"
    echo "  -h, --help      Show help"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target) TARGET="$2"; shift 2 ;;
        -v|--version) VERSION="$2"; shift 2 ;;
        -p|--profile) PROFILE="$2"; shift 2 ;;
        -d|--dir) CLONE_DIR="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

echo "=== Lakeflow Framework Deployment ==="
echo "  Target:  $TARGET"
echo "  Version: $VERSION"
echo "  Profile: $PROFILE"
echo ""

if [ -d "$CLONE_DIR" ]; then
    echo "Updating existing clone at $CLONE_DIR..."
    cd "$CLONE_DIR"
    git pull --ff-only
else
    echo "Cloning Lakeflow Framework..."
    git clone https://github.com/databricks-solutions/lakeflow_framework.git "$CLONE_DIR"
    cd "$CLONE_DIR"
fi

if [ "$VERSION" != "current" ]; then
    echo "Checking out version: $VERSION"
    git checkout "v$VERSION" 2>/dev/null || git checkout "$VERSION"
fi

echo ""
echo "Validating bundle..."
databricks bundle validate -t "$TARGET" -p "$PROFILE"

echo ""
echo "Deploying framework bundle..."
databricks bundle deploy -t "$TARGET" -p "$PROFILE" --var="version=$VERSION"

echo ""
echo "=== Framework deployed successfully ==="
echo ""
echo "Framework source path:"
CURRENT_USER=$(databricks current-user me -p "$PROFILE" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['userName'])" 2>/dev/null || echo '<your_username>')
echo "  /Workspace/Users/$CURRENT_USER/.bundle/lakeflow_framework/$TARGET/$VERSION/files/src"
echo ""
echo "Use this path as framework_source_path in your pipeline bundles."
