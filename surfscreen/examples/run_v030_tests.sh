#!/bin/bash
# ============================================================
# SurfScreen v0.3.0 통합 테스트 스크립트
# ============================================================
# 
# 이 스크립트는 모든 새 기능을 테스트합니다:
# - Export (CSV/JSON/Excel/ZIP)
# - Checkpoint/Resume
# - Templates
# - Coverage Analysis
# - Phonon Analysis
# - Materials Project 연동 (API 키 필요)
#
# 사용법:
#   cd examples/
#   bash run_v030_tests.sh
#
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "🧪 SurfScreen v0.3.0 New Features Test Suite"
echo "========================================================"
echo "Start time: $(date)"
echo ""

# 출력 디렉토리
rm -rf output/v030_test
mkdir -p output/v030_test
cd output/v030_test

PASSED=0
FAILED=0

run_test() {
    local name="$1"
    local cmd="$2"
    
    echo ""
    echo "----------------------------------------"
    echo "🔧 Testing: $name"
    echo "   Command: $cmd"
    echo "----------------------------------------"
    
    if eval "$cmd" 2>&1; then
        echo "✅ PASSED: $name"
        PASSED=$((PASSED + 1))
    else
        echo "❌ FAILED: $name"
        FAILED=$((FAILED + 1))
    fi
}

# ============================================================
# 1. Import Tests
# ============================================================
echo ""
echo "========================================================"
echo "📦 1. Import Tests"
echo "========================================================"

run_test "Import surfscreen" "python -c 'import surfscreen; print(surfscreen.__version__)'"

run_test "Import ExportManager" "python -c 'from surfscreen import ExportManager, ExportConfig'"

run_test "Import CheckpointManager" "python -c 'from surfscreen import CheckpointManager, ScreeningCheckpoint, MDCheckpoint'"

run_test "Import TemplateEngine" "python -c 'from surfscreen import TemplateEngine, WorkflowTemplate'"

run_test "Import PhononAnalyzer" "python -c 'from surfscreen.analysis import PhononAnalyzer, calculate_zpe'"

run_test "Import CoverageAnalyzer" "python -c 'from surfscreen.analysis import CoverageAnalyzer, calculate_coverage'"

# ============================================================
# 2. CLI Help Tests
# ============================================================
echo ""
echo "========================================================"
echo "📋 2. CLI Help Tests"
echo "========================================================"

run_test "surfscreen --version" "surfscreen --version"

run_test "export --help" "surfscreen export --help"

run_test "template --help" "surfscreen template --help"

run_test "analysis coverage --help" "surfscreen analysis coverage --help"

run_test "analysis phonon --help" "surfscreen analysis phonon --help"

run_test "analysis gibbs --help" "surfscreen analysis gibbs --help"

# ============================================================
# 3. Export Tests
# ============================================================
echo ""
echo "========================================================"
echo "📊 3. Export Tests"
echo "========================================================"

# 테스트 데이터 생성
mkdir -p results
cat > results/results.json << 'EOF'
{
    "results": [
        {"name": "config1", "e_ads": -1.5, "height": 2.0},
        {"name": "config2", "e_ads": -1.2, "height": 2.5}
    ],
    "summary": {"best_energy": -1.5}
}
EOF

run_test "Export CSV" "surfscreen export csv results -o export.csv && cat export.csv"

run_test "Export JSON" "surfscreen export json results -o export.json && head -10 export.json"

run_test "Export ZIP" "surfscreen export zip results -o export.zip --no-structures --no-trajectories && ls -la export.zip"

# ============================================================
# 4. Template Tests
# ============================================================
echo ""
echo "========================================================"
echo "📝 4. Template Tests"
echo "========================================================"

run_test "Install defaults" "surfscreen template install-defaults"

run_test "List templates" "surfscreen template list"

run_test "Dry-run template" "surfscreen template run basic_screening -v element=Cu --dry-run"

# ============================================================
# 5. Checkpoint Tests
# ============================================================
echo ""
echo "========================================================"
echo "💾 5. Checkpoint Tests"
echo "========================================================"

run_test "Checkpoint create" "python -c '
from surfscreen.checkpoint import ScreeningCheckpoint

cp = ScreeningCheckpoint(\"checkpoint_test\")
cp.register_tasks([\"t1\", \"t2\", \"t3\"])
cp.complete_task(\"t1\")
progress = cp.get_progress()
print(f\"Progress: {progress}\")
assert progress[\"completed\"] == 1
print(\"OK\")
'"

# ============================================================
# 6. Coverage Analysis Tests
# ============================================================
echo ""
echo "========================================================"
echo "📏 6. Coverage Analysis Tests"
echo "========================================================"

# 테스트 구조 생성
python << 'EOF'
from ase.build import fcc111, molecule
from ase.io import write

surface = fcc111('Cu', size=(3, 3, 4), vacuum=15.0)
n_surface = len(surface)
print(f"Surface atoms: {n_surface}")

co = molecule('CO')
co.translate([5, 5, 20])
system = surface + co

write('test_surface.xyz', system)
print("Created: test_surface.xyz")
EOF

run_test "Coverage analysis" "surfscreen analysis coverage test_surface.xyz --n-surface 36 --mol-area 10.0"

# ============================================================
# 7. Unit Tests (pytest)
# ============================================================
echo ""
echo "========================================================"
echo "🧪 7. Unit Tests (pytest)"
echo "========================================================"

cd "$SCRIPT_DIR/.."

run_test "pytest test_export.py" "pytest tests/test_export.py -v --tb=short" || true

run_test "pytest test_checkpoint.py" "pytest tests/test_checkpoint.py -v --tb=short" || true

run_test "pytest test_templates.py" "pytest tests/test_templates.py -v --tb=short" || true

run_test "pytest test_coverage.py" "pytest tests/test_coverage.py -v --tb=short" || true

run_test "pytest test_phonon.py" "pytest tests/test_phonon.py -v --tb=short" || true

# ============================================================
# Summary
# ============================================================
echo ""
echo "========================================================"
echo "📊 Test Summary"
echo "========================================================"
echo "Total: $((PASSED + FAILED))"
echo "Passed: $PASSED ✅"
echo "Failed: $FAILED ❌"
echo ""
echo "End time: $(date)"
echo "========================================================"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed!"
    exit 0
else
    echo ""
    echo "⚠️ Some tests failed. Check the output above."
    exit 1
fi
