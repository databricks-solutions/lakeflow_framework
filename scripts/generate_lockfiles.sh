#!/bin/bash
# Generate hashed lockfiles for CI.
# Run this from the repo root on a machine with PyPI (or JFrog) access.
# The generated lockfiles should be committed to the repo.
#
# Usage:
#   ./scripts/generate_lockfiles.sh
#
# Prerequisites:
#   pip install uv   (or: pip install pip-tools)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Generating hashed lockfile for requirements-docs.txt..."
uv pip compile \
    "$REPO_ROOT/requirements-docs.txt" \
    --generate-hashes \
    --output-file "$REPO_ROOT/requirements-docs.lock"

echo "Done. Commit requirements-docs.lock to the repository."
echo ""
echo "To verify: pip install --require-hashes -r requirements-docs.lock"
