#!/bin/bash
# ============================================================
# Run All SurfScreen Examples
# ============================================================
# 전체 예제 테스트 실행 스크립트
# 
# 사용법:
#   bash run_all_tests.sh           # 전체 실행
#   bash run_all_tests.sh quick     # 빠른 테스트만 (01-08)
#   bash run_all_tests.sh full      # 전체 테스트 (01-20)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE=${1:-full}

echo "========================================================"
echo "🧪 SurfScreen Example Test Suite"
echo "========================================================"
echo "Mode: $MODE"
echo "Start time: $(date)"
echo ""

# 출력 디렉토리 정리
rm -rf output/
mkdir -p output

# 테스트 목록
if [ "$MODE" = "quick" ]; then
    TESTS="01 02 03 04 05 06 07 08"
else
    TESTS="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23"
fi

PASSED=0
FAILED=0
FAILED_LIST=""

for num in $TESTS; do
    script=$(ls ${num}_*.sh 2>/dev/null | head -1)
    
    if [ -z "$script" ]; then
        echo "⚠️ Test $num not found"
        continue
    fi
    
    echo ""
    echo "========================================================"
    echo "Running: $script"
    echo "========================================================"
    
    if timeout 300 bash "$script"; then
        echo ""
        echo "✅ $script PASSED"
        PASSED=$((PASSED + 1))
    else
        echo ""
        echo "❌ $script FAILED"
        FAILED=$((FAILED + 1))
        FAILED_LIST="$FAILED_LIST $script"
    fi
done

echo ""
echo "========================================================"
echo "📊 Test Summary"
echo "========================================================"
echo "Total: $((PASSED + FAILED))"
echo "Passed: $PASSED ✅"
echo "Failed: $FAILED ❌"
if [ -n "$FAILED_LIST" ]; then
    echo "Failed tests:$FAILED_LIST"
fi
echo "End time: $(date)"
echo "========================================================"

exit $FAILED
