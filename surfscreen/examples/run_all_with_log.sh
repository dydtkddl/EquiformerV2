#!/bin/bash
# ============================================================
# Run All SurfScreen Examples with Full Logging
# ============================================================
# 모든 예제를 실행하고 하나의 로그 파일에 저장
#
# 사용법:
#   bash run_all_with_log.sh
#
# 출력:
#   - test_results_YYYYMMDD_HHMMSS.log (전체 로그)
#   - output/ (모든 테스트 출력 파일)
# ============================================================

# 스크립트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 타임스탬프
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="test_results_${TIMESTAMP}.log"

# 출력 디렉토리 정리
rm -rf output/
mkdir -p output

# 로그 파일 헤더
{
    echo "========================================================"
    echo "🧪 SurfScreen Complete Test Suite"
    echo "========================================================"
    echo ""
    echo "Start Time: $(date)"
    echo "Hostname: $(hostname)"
    echo "User: $(whoami)"
    echo "Python: $(python --version 2>&1)"
    echo "Working Dir: $(pwd)"
    echo ""
    echo "Testing Environment:"
    echo "-------------------"
    pip show surfscreen 2>/dev/null | grep -E "^(Name|Version|Location)" || echo "surfscreen: not found"
    echo ""
    command -v surfscreen && surfscreen --version 2>/dev/null || echo "surfscreen CLI: not available"
    echo ""
} | tee "$LOG_FILE"

# 테스트 목록
TESTS=(
    "01_molecule_from_pubchem.sh"
    "02_molecule_from_smiles.sh"
    "03_molecule_conformers.sh"
    "04_molecule_analyze.sh"
    "05_surface_create.sh"
    "06_surface_sites.sh"
    "07_adsorb_generate.sh"
    "08_adsorb_visualize.sh"
    "09_md_mace.sh"
    "10_md_xtb_molecule.sh"
    "11_xtb_pbc_warning.sh"
    "12_screen_run.sh"
    "13_analysis_msd.sh"
    "14_analysis_rdf.sh"
    "15_analysis_boltzmann.sh"
    "16_md_ensembles.sh"
    "17_config_show.sh"
    "18_analysis_height.sh"
    "19_multi_molecule_screen.sh"
    "20_full_pipeline.sh"
)

TOTAL=${#TESTS[@]}
PASSED=0
FAILED=0
SKIPPED=0
declare -a FAILED_TESTS
declare -a PASSED_TESTS
declare -a TEST_TIMES

echo "" | tee -a "$LOG_FILE"
echo "========================================================"  | tee -a "$LOG_FILE"
echo "Starting $TOTAL tests..."  | tee -a "$LOG_FILE"
echo "========================================================"  | tee -a "$LOG_FILE"

# 각 테스트 실행
for i in "${!TESTS[@]}"; do
    script="${TESTS[$i]}"
    num=$((i + 1))
    
    echo "" | tee -a "$LOG_FILE"
    echo "========================================================" | tee -a "$LOG_FILE"
    echo "[$num/$TOTAL] Running: $script" | tee -a "$LOG_FILE"
    echo "Start: $(date)" | tee -a "$LOG_FILE"
    echo "========================================================" | tee -a "$LOG_FILE"
    
    if [ ! -f "$script" ]; then
        echo "⚠️ SKIPPED: File not found" | tee -a "$LOG_FILE"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi
    
    # 시간 측정
    START_TIME=$(date +%s)
    
    # 테스트 실행 (타임아웃 5분)
    if timeout 300 bash "$script" 2>&1 | tee -a "$LOG_FILE"; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        TEST_TIMES+=("$script: ${DURATION}s")
        
        echo "" | tee -a "$LOG_FILE"
        echo "✅ PASSED: $script (${DURATION}s)" | tee -a "$LOG_FILE"
        PASSED=$((PASSED + 1))
        PASSED_TESTS+=("$script")
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        TEST_TIMES+=("$script: ${DURATION}s (FAILED)")
        
        echo "" | tee -a "$LOG_FILE"
        echo "❌ FAILED: $script (${DURATION}s)" | tee -a "$LOG_FILE"
        FAILED=$((FAILED + 1))
        FAILED_TESTS+=("$script")
    fi
done

# 최종 요약
{
    echo ""
    echo "========================================================"
    echo "📊 FINAL TEST SUMMARY"
    echo "========================================================"
    echo ""
    echo "End Time: $(date)"
    echo ""
    echo "Results:"
    echo "  Total:   $TOTAL"
    echo "  Passed:  $PASSED ✅"
    echo "  Failed:  $FAILED ❌"
    echo "  Skipped: $SKIPPED ⚠️"
    echo ""
    echo "Success Rate: $(( (PASSED * 100) / TOTAL ))%"
    echo ""
    
    if [ ${#PASSED_TESTS[@]} -gt 0 ]; then
        echo "Passed Tests:"
        for t in "${PASSED_TESTS[@]}"; do
            echo "  ✅ $t"
        done
        echo ""
    fi
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "Failed Tests:"
        for t in "${FAILED_TESTS[@]}"; do
            echo "  ❌ $t"
        done
        echo ""
    fi
    
    echo "Execution Times:"
    for t in "${TEST_TIMES[@]}"; do
        echo "  $t"
    done
    echo ""
    
    echo "Log File: $LOG_FILE"
    echo "Output Directory: output/"
    echo ""
    echo "========================================================"
    echo "🏁 Test Suite Complete"
    echo "========================================================"
} | tee -a "$LOG_FILE"

# 출력 디렉토리 크기
echo "" | tee -a "$LOG_FILE"
echo "Output directory size:" | tee -a "$LOG_FILE"
du -sh output/ 2>/dev/null | tee -a "$LOG_FILE"

echo ""
echo "📄 Full log saved to: $LOG_FILE"
echo ""

# 실패한 테스트 수를 종료 코드로
exit $FAILED
