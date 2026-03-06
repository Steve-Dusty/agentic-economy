#!/bin/bash
# Trinity Full Test Suite (~5-8 minutes)
# Complete validation including slow chat tests
# Use for: Release validation, comprehensive testing

set -e

cd "$(dirname "$0")"
source .venv/bin/activate

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================="
echo "  TRINITY FULL TEST SUITE (Tier 3)"
echo "  Expected time: 5-8 minutes"
echo "========================================="
echo ""

# Run with HTML report
time python -m pytest -v --tb=short \
  --html=reports/test-report-${TIMESTAMP}.html \
  --self-contained-html \
  "$@"

echo ""
echo "HTML report saved to: reports/test-report-${TIMESTAMP}.html"
