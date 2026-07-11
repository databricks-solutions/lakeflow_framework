#!/usr/bin/env bash
# Run Sphinx spelling builder and fail if any misspelled words are found.
#
# Usage:
#   scripts/ci/docs_spelling_check.sh
#
# sphinxcontrib-spelling reports misspellings but exits 0 unless the build
# itself fails. This script fails when the log contains
# "Found N misspelled words" with N > 0.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/docs"

mkdir -p build
LOG="$ROOT/docs/build/sphinx-spelling.log"

SPHINXBUILD="${SPHINXBUILD:-sphinx-build}"

set +o pipefail
"$SPHINXBUILD" -M spelling source build -c . 2>&1 | tee "$LOG"
BUILD_STATUS=${PIPESTATUS[0]}
set -o pipefail

if [ "$BUILD_STATUS" -ne 0 ]; then
  echo "Sphinx spelling build failed (exit $BUILD_STATUS)"
  exit "$BUILD_STATUS"
fi

if grep -qE 'Found [1-9][0-9]* misspelled words' "$LOG"; then
  echo "Spelling check failed — misspelled words found."
  grep -E 'Spell check:|Found [0-9]+ misspelled words' "$LOG" || true
  exit 1
fi

echo "Spelling check passed."
