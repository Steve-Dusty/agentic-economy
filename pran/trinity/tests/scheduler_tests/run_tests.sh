#!/bin/bash
# Run scheduler tests independently
# Usage: ./tests/scheduler/run_tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================"
echo "Trinity Scheduler Service - Test Suite"
echo "========================================"
echo ""

# Check if we have a virtual environment
if [ -d "$PROJECT_ROOT/tests/.venv" ]; then
    echo "Using existing tests/.venv..."
    source "$PROJECT_ROOT/tests/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "Using project .venv..."
    source "$PROJECT_ROOT/.venv/bin/activate"
else
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Install dependencies
echo "Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov pytest-mock httpx aiohttp redis apscheduler croniter pytz

# Add src to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Run tests
echo ""
echo "Running tests..."
echo "----------------------------------------"

cd "$SCRIPT_DIR"
python -m pytest \
    --tb=short \
    -v \
    --cov="$PROJECT_ROOT/src/scheduler" \
    --cov-report=term-missing \
    "$@"

echo ""
echo "========================================"
echo "Test run complete!"
echo "========================================"
