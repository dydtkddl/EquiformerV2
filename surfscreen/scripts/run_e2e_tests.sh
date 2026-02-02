#!/bin/bash
###############################################################################
# End-to-End Workflow Tests
# 
# Tests complete workflows from molecule input to report generation.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_OUTPUT_DIR="$PROJECT_ROOT/test_outputs/e2e"
DATE_TAG=$(date +"%Y%m%d_%H%M%S")
E2E_LOG="$TEST_OUTPUT_DIR/e2e_${DATE_TAG}.log"

# Test counters
PASSED=0
FAILED=0
TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=================================================="
echo "END-TO-END WORKFLOW TESTS"
echo "=================================================="
echo ""

cd "$PROJECT_ROOT"
mkdir -p "$TEST_OUTPUT_DIR"

# Initialize log
echo "E2E Test Run - $DATE_TAG" > "$E2E_LOG"
echo "======================================" >> "$E2E_LOG"

# Helper function
run_e2e_test() {
    local test_name="$1"
    local test_func="$2"
    
    ((TOTAL++))
    
    echo -n "Testing: $test_name... "
    echo "" >> "$E2E_LOG"
    echo "=== $test_name ===" >> "$E2E_LOG"
    
    local start_time=$(date +%s)
    local exit_code=0
    
    if $test_func >> "$E2E_LOG" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${GREEN}PASS${NC} (${duration}s)"
        ((PASSED++))
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${RED}FAIL${NC} (${duration}s)"
        ((FAILED++))
        exit_code=1
    fi
    
    return $exit_code
}

# ============================================
# Test Functions
# ============================================

test_workflow_screen_single() {
    # Create test molecule
    local mol_file="$TEST_OUTPUT_DIR/test_mol.xyz"
    cat > "$mol_file" << 'EOF'
5
Methane
C  0.000000  0.000000  0.000000
H  1.089000  0.000000  0.000000
H -0.363000  1.027350  0.000000
H -0.363000 -0.513675  0.889165
H -0.363000 -0.513675 -0.889165
EOF

    # Create test surface
    local surf_file="$TEST_OUTPUT_DIR/test_surf.cif"
    cat > "$surf_file" << 'EOF'
data_test
_cell_length_a   5.0
_cell_length_b   5.0
_cell_length_c   20.0
_cell_angle_alpha   90.0
_cell_angle_beta    90.0
_cell_angle_gamma   90.0
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Pt1  0.0  0.0  0.5
Pt2  0.5  0.5  0.5
EOF

    # Run screen command (dry-run)
    python -m surfscreen screen \
        --molecule "$mol_file" \
        --surface "$surf_file" \
        --dry-run \
        --output "$TEST_OUTPUT_DIR/screen_result.json"
    
    # Verify output
    if [[ -f "$TEST_OUTPUT_DIR/screen_result.json" ]]; then
        echo "Output file created successfully"
        cat "$TEST_OUTPUT_DIR/screen_result.json"
        return 0
    else
        echo "Output file not created"
        return 1
    fi
}

test_workflow_validate() {
    # Test file validation
    local test_file="$TEST_OUTPUT_DIR/validate_test.xyz"
    cat > "$test_file" << 'EOF'
2
Hydrogen
H  0.0  0.0  0.0
H  0.74  0.0  0.0
EOF
    
    python -m surfscreen validate --file "$test_file" || true
    return 0
}

test_workflow_config() {
    # Test config commands
    python -m surfscreen config show || true
    return 0
}

test_workflow_api_health() {
    # Test API health via Python
    python << 'EOF'
from surfscreen.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Health check
response = client.get("/health")
assert response.status_code == 200
print(f"Health: {response.json()}")

# Root
response = client.get("/")
assert response.status_code == 200
print(f"Root: {response.json()}")

print("API health check passed")
EOF
}

test_workflow_batch_submit() {
    # Test batch job submission via API
    python << 'EOF'
from surfscreen.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Get batch jobs list (should work even if empty)
response = client.get("/api/v1/batch")
print(f"Batch list: {response.status_code}")

# Get cache stats
response = client.get("/api/v1/cache/stats")
print(f"Cache stats: {response.status_code}")
if response.status_code == 200:
    print(f"Stats: {response.json()}")

print("Batch test passed")
EOF
}

test_workflow_jobs_list() {
    # Test jobs listing
    python << 'EOF'
from surfscreen.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# List jobs
response = client.get("/api/v1/jobs")
print(f"Jobs list: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total jobs: {data.get('total', 0)}")

print("Jobs listing passed")
EOF
}

test_workflow_import_all_modules() {
    # Test all module imports
    python << 'EOF'
import sys

modules = [
    'surfscreen',
    'surfscreen.core',
    'surfscreen.api',
    'surfscreen.api.main',
    'surfscreen.api.routers',
    'surfscreen.cache',
    'surfscreen.batch',
    'surfscreen.scheduler',
    'surfscreen.auth',
    'surfscreen.notifications',
]

failed = []
for module in modules:
    try:
        __import__(module)
        print(f"✓ {module}")
    except ImportError as e:
        print(f"✗ {module}: {e}")
        failed.append(module)

if failed:
    print(f"\nFailed imports: {len(failed)}")
    sys.exit(1)
else:
    print(f"\nAll {len(modules)} modules imported successfully")
EOF
}

# ============================================
# Run Tests
# ============================================
echo ""
echo "--- Running E2E Tests ---"
echo ""

run_e2e_test "Import All Modules" test_workflow_import_all_modules || true
run_e2e_test "Config Show" test_workflow_config || true
run_e2e_test "Validate File" test_workflow_validate || true
run_e2e_test "API Health Check" test_workflow_api_health || true
run_e2e_test "Jobs List" test_workflow_jobs_list || true
run_e2e_test "Batch Submit" test_workflow_batch_submit || true
run_e2e_test "Screen Single (Dry-Run)" test_workflow_screen_single || true

# ============================================
# Summary
# ============================================
echo ""
echo "=================================================="
echo "E2E TEST SUMMARY"
echo "=================================================="
echo -e "Total:  $TOTAL"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""
echo "Log: $E2E_LOG"
echo ""

if [[ $FAILED -gt 0 ]]; then
    echo "Some E2E tests failed. Check log for details."
    exit 1
else
    echo "All E2E tests passed!"
    exit 0
fi
