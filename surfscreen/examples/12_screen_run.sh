#!/bin/bash
# ============================================================
# Example 12: 흡착 스크리닝 (전체 워크플로우)
# ============================================================
# 테스트: surfscreen screen run
# 설명: 표면 + 분자 → 흡착 에너지 스크리닝
# ⚠️ GPU 권장, 시간 소요됨
# ============================================================

set -e

echo "========================================"
echo "Example 12: Adsorption Screening"
echo "========================================"

mkdir -p output/12_screening
cd output/12_screening

# 표면과 분자 준비
echo ""
echo "[1/4] Preparing surface and molecule..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 3x3x1 --fix 2 -o Cu111.xyz
surfscreen molecule from-pubchem water -o water.xyz
echo "✓ Surface and molecule ready"

# 스크리닝 실행 (작은 설정)
echo ""
echo "[2/4] Running adsorption screening..."
surfscreen screen run \
    -s Cu111.xyz \
    -m water.xyz \
    --engine mace \
    --device cpu \
    --rotations 4 \
    --max-configs 10 \
    -o screening_results/
echo "✓ Screening completed"

# 결과 확인
echo ""
echo "[3/4] Viewing results..."
surfscreen screen results screening_results/results.json --top 5

# 리포트 생성
echo ""
echo "[4/4] Generating HTML report..."
surfscreen screen report screening_results/ -o screening_report.html

echo ""
echo "========================================"
echo "✅ Example 12 completed!"
echo "Results: screening_results/"
echo "Report: screening_report.html"
echo "========================================"
