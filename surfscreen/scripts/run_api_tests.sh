#!/bin/bash
###############################################################################
# API Tests Runner
# 
# Runs API endpoint tests with a live test server.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/tests"

WORKERS=${PARALLEL_WORKERS:-4}

echo "=================================================="
echo "API TESTS"
echo "=================================================="
echo "Testing API endpoints..."
echo ""

cd "$PROJECT_ROOT"

# Start API server in background for testing (if not already running)
API_PORT=8765
API_PID=""

start_test_server() {
    echo "Starting test API server on port $API_PORT..."
    python -m surfscreen.api.main --host 127.0.0.1 --port $API_PORT &
    API_PID=$!
    sleep 5  # Wait for server to start
    
    # Check if server is running
    if ! kill -0 $API_PID 2>/dev/null; then
        echo "ERROR: Failed to start test server"
        return 1
    fi
    
    echo "Test server started (PID: $API_PID)"
}

stop_test_server() {
    if [[ -n "$API_PID" ]]; then
        echo "Stopping test server (PID: $API_PID)..."
        kill $API_PID 2>/dev/null || true
        wait $API_PID 2>/dev/null || true
    fi
}

# Cleanup on exit
trap stop_test_server EXIT

# Start server
# start_test_server  # Uncomment if you need a live server

# Run API tests
export SURFSCREEN_API_URL="http://127.0.0.1:$API_PORT"

python -m pytest "$TEST_DIR/integration" \
    -v \
    --tb=short \
    -n "$WORKERS" \
    --timeout=180 \
    -k "api" \
    --junitxml="$PROJECT_ROOT/test_outputs/junit_api.xml" \
    2>&1

# Test API health endpoints
echo ""
echo "Testing API Health Check Endpoints..."
echo ""

# These tests run even without pytest
python << 'EOF'
import sys
try:
    from surfscreen.api.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    print("✓ /health endpoint OK")
    
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200, f"Root endpoint failed: {response.status_code}"
    print("✓ / (root) endpoint OK")
    
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200, f"OpenAPI failed: {response.status_code}"
    print("✓ /openapi.json endpoint OK")
    
    print("\nAll API health checks passed!")
    sys.exit(0)
except Exception as e:
    print(f"✗ API test failed: {e}")
    sys.exit(1)
EOF

echo ""
echo "API tests completed."
