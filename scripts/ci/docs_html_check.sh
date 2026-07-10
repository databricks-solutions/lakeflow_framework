#!/usr/bin/env bash
# Build Sphinx HTML docs and fail if warnings reach the configured limit.
#
# Usage:
#   scripts/ci/docs_html_check.sh [max_warnings]
#
# Default max_warnings is 19 (i.e. fewer than 20 warnings required).
set -euo pipefail

MAX_WARNINGS="${1:-19}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/docs"

mkdir -p build
LOG="$ROOT/docs/build/sphinx-html.log"

set +o pipefail
make html 2>&1 | tee "$LOG"
BUILD_STATUS=${PIPESTATUS[0]}
set -o pipefail

if [ "$BUILD_STATUS" -ne 0 ]; then
  echo "Sphinx HTML build failed (exit $BUILD_STATUS)"
  exit "$BUILD_STATUS"
fi

WARNING_COUNT="$(grep -cE ': WARNING:' "$LOG" || true)"
echo "Sphinx HTML warning count: $WARNING_COUNT (max allowed: $MAX_WARNINGS)"

if [ "$WARNING_COUNT" -gt "$MAX_WARNINGS" ]; then
  echo "Too many Sphinx warnings — limit is $MAX_WARNINGS (need fewer than 20)."
  grep -E ': WARNING:' "$LOG" | tail -30 || true
  exit 1
fi
