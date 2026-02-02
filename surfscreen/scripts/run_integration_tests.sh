#!/bin/bash
###############################################################################
# Integration Tests Runner
# 
# Runs API integration tests with mocked services.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/tests/integration"

WORKERS=${PARALLEL_WORKERS:-$(nproc 2>/dev/null || echo 4)}

echo "=================================================="
echo "INTEGRATION TESTS"
echo "=================================================="
echo "Test Directory: $TEST_DIR"
echo "Workers: $WORKERS"
echo ""

cd "$PROJECT_ROOT"

# Run integration tests
python -m pytest "$TEST_DIR" \
    -v \
    --tb=short \
    -n "$WORKERS" \
    --timeout=300 \
    --cov=surfscreen.api \
    --cov-append \
    --cov-report=term-missing \
    --junitxml="$PROJECT_ROOT/test_outputs/junit_integration.xml" \
    2>&1

echo ""
echo "Integration tests completed."
