#!/bin/bash
# Generate hashed lockfiles for CI.
# Run this from the repo root on a machine with PyPI (or JFrog) access.
# The generated lockfiles should be committed to the repo.
#
# Usage:
#   ./scripts/generate_lockfiles.sh
#
# Prerequisites:
#   pip install pip-tools

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REQUIREMENTS_FILES=(
    "requirements.txt"
    "requirements-dev.txt"
    "requirements-docs.txt"
)

for req_file in "${REQUIREMENTS_FILES[@]}"; do
    lock_file="${req_file%.txt}.lock"
    echo "Generating hashed lockfile for ${req_file}..."
    compile_args=(
        "$REPO_ROOT/$req_file"
        --generate-hashes
    )
    if [ "$req_file" = "requirements-dev.txt" ]; then
        # Pin setuptools (distutils shim on Python 3.12+) for --no-deps CI installs.
        compile_args+=(--allow-unsafe)
    fi
    pip-compile \
        "${compile_args[@]}" \
        --output-file "$REPO_ROOT/$lock_file" \
        --no-emit-index-url

done

echo ""
echo "Done. Commit the following lockfiles to the repository:"
for req_file in "${REQUIREMENTS_FILES[@]}"; do
    echo "  - ${req_file%.txt}.lock"
done
echo ""
echo "To verify, run (for each lockfile):"
echo "  pip install --require-hashes --no-deps -r <lockfile>"
