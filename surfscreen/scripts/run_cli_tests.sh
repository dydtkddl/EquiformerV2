#!/bin/bash
###############################################################################
# CLI Tests Runner
# 
# Comprehensive testing of all SurfScreen CLI commands.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_OUTPUT_DIR="$PROJECT_ROOT/test_outputs/cli"
FIXTURES_DIR="$PROJECT_ROOT/tests/fixtures"

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
echo "CLI TESTS"
echo "=================================================="
echo ""

cd "$PROJECT_ROOT"
mkdir -p "$TEST_OUTPUT_DIR"

# Helper function to run a CLI test
run_cli_test() {
    local test_name="$1"
    local command="$2"
    local expected_exit_code="${3:-0}"
    
    ((TOTAL++))
    
    echo -n "Testing: $test_name... "
    
    local exit_code=0
    local output
    output=$(eval "$command" 2>&1) || exit_code=$?
    
    if [[ $exit_code -eq $expected_exit_code ]]; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC} (expected $expected_exit_code, got $exit_code)"
        echo "  Output: $output" | head -5
        ((FAILED++))
        return 1
    fi
}

# ============================================
# 1. Basic CLI Commands
# ============================================
echo ""
echo "--- 1. Basic CLI Commands ---"

run_cli_test "surfscreen --help" "python -m surfscreen --help"
run_cli_test "surfscreen --version" "python -m surfscreen --version"

# ============================================
# 2. Screen Command Tests
# ============================================
echo ""
echo "--- 2. Screen Command Tests ---"

# Create test molecule file
TEST_MOL="$TEST_OUTPUT_DIR/test_molecule.xyz"
cat > "$TEST_MOL" << 'EOF'
3
Water molecule
O  0.000000  0.000000  0.117489
H  0.756950  0.000000 -0.469957
H -0.756950  0.000000 -0.469957
EOF

# Create test surface file
TEST_SURFACE="$TEST_OUTPUT_DIR/test_surface.cif"
cat > "$TEST_SURFACE" << 'EOF'
data_test_surface
_cell_length_a   3.0
_cell_length_b   3.0
_cell_length_c   20.0
_cell_angle_alpha   90.0
_cell_angle_beta    90.0
_cell_angle_gamma   90.0
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Cu1  0.0  0.0  0.5
Cu2  0.5  0.5  0.5
EOF

run_cli_test "surfscreen screen --help" "python -m surfscreen screen --help"

# Test screen command with test files (may fail if MACE not installed - acceptable)
run_cli_test "surfscreen screen (dry run)" \
    "python -m surfscreen screen --molecule $TEST_MOL --surface $TEST_SURFACE --dry-run --output $TEST_OUTPUT_DIR/screen_result.json" || true

# ============================================
# 3. MD Command Tests
# ============================================
echo ""
echo "--- 3. MD Command Tests ---"

run_cli_test "surfscreen md --help" "python -m surfscreen md --help"

# Test MD command with test files
run_cli_test "surfscreen md (dry run)" \
    "python -m surfscreen md --input $TEST_MOL --dry-run --output $TEST_OUTPUT_DIR/md_result" || true

# ============================================
# 4. Report Command Tests
# ============================================
echo ""
echo "--- 4. Report Command Tests ---"

run_cli_test "surfscreen report --help" "python -m surfscreen report --help" || true

# ============================================
# 5. Validate Command Tests
# ============================================
echo ""
echo "--- 5. Validate Command Tests ---"

run_cli_test "surfscreen validate --help" "python -m surfscreen validate --help" || true
run_cli_test "validate xyz file" "python -m surfscreen validate --file $TEST_MOL" || true
run_cli_test "validate cif file" "python -m surfscreen validate --file $TEST_SURFACE" || true

# ============================================
# 6. Config Command Tests
# ============================================
echo ""
echo "--- 6. Config Command Tests ---"

run_cli_test "surfscreen config --help" "python -m surfscreen config --help" || true
run_cli_test "surfscreen config show" "python -m surfscreen config show" || true

# ============================================
# 7. Server Command Tests
# ============================================
echo ""
echo "--- 7. Server Command Tests ---"

run_cli_test "surfscreen server --help" "python -m surfscreen server --help" || true

# ============================================
# 8. Batch Command Tests
# ============================================
echo ""
echo "--- 8. Batch Command Tests ---"

run_cli_test "surfscreen batch --help" "python -m surfscreen batch --help" || true

# ============================================
# 9. Input Validation Tests
# ============================================
echo ""
echo "--- 9. Input Validation Tests ---"

# Test with invalid inputs (should fail gracefully)
run_cli_test "invalid file path" "python -m surfscreen screen --molecule /nonexistent/file.xyz --surface $TEST_SURFACE" 1 || true
run_cli_test "missing required args" "python -m surfscreen screen" 2 || true

# ============================================
# 10. Module Import Tests
# ============================================
echo ""
echo "--- 10. Module Import Tests ---"

run_cli_test "import surfscreen" "python -c 'import surfscreen; print(surfscreen.__version__)'"
run_cli_test "import surfscreen.core" "python -c 'import surfscreen.core'"
run_cli_test "import surfscreen.api" "python -c 'import surfscreen.api'"
run_cli_test "import surfscreen.analysis" "python -c 'import surfscreen.analysis'" || true

# ============================================
# Summary
# ============================================
echo ""
echo "=================================================="
echo "CLI TEST SUMMARY"
echo "=================================================="
echo -e "Total:  $TOTAL"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

# Cleanup
rm -f "$TEST_MOL" "$TEST_SURFACE"

if [[ $FAILED -gt 0 ]]; then
    echo "Some CLI tests failed!"
    exit 1
else
    echo "All CLI tests passed!"
    exit 0
fi
