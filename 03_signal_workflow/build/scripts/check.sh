#!/usr/bin/env bash
# Bundled pre-commit verification for the Mento signal-engine build.
#
# Runs ruff (lint), mypy --strict (types), and pytest (tests) in sequence.
# Exit code is non-zero on the first failing step. Output is left as-is so
# you see the actual diagnostics rather than a custom summary.
#
# Usage: ./scripts/check.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> ruff"
uv run ruff check src/ tests/

echo "==> mypy"
uv run mypy src/signal_engine

echo "==> pytest"
uv run pytest

echo
echo "✓ all checks passed"
