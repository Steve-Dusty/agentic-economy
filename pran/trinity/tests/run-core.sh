#!/bin/bash
# Trinity Core Tests (~3-5 minutes)
# Standard validation with module-scoped agents
# Use for: Pre-commit checks, feature verification

set -e

cd "$(dirname "$0")"
source .venv/bin/activate

echo "========================================="
echo "  TRINITY CORE TESTS (Tier 2)"
echo "  Expected time: 3-5 minutes"
echo "========================================="
echo ""

time python -m pytest -m "not slow" -v --tb=short "$@"
