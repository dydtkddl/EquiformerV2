#!/bin/bash
###############################################################################
# Unit Tests Runner
# 
# Runs all unit tests for SurfScreen modules with coverage reporting.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/tests/unit"

# Number of parallel workers (use all available CPUs)
WORKERS=${PARALLEL_WORKERS:-$(nproc 2>/dev/null || echo 8)}

echo "=================================================="
echo "UNIT TESTS"
echo "=================================================="
echo "Test Directory: $TEST_DIR"
echo "Workers: $WORKERS"
echo ""

cd "$PROJECT_ROOT"

# Run unit tests with coverage
python -m pytest "$TEST_DIR" \
    -v \
    --tb=short \
    -n "$WORKERS" \
    --timeout=120 \
    --cov=surfscreen \
    --cov-report=term-missing \
    --cov-report=html:"$PROJECT_ROOT/test_outputs/coverage_unit" \
    --junitxml="$PROJECT_ROOT/test_outputs/junit_unit.xml" \
    -x \
    2>&1

echo ""
echo "Unit tests completed."
