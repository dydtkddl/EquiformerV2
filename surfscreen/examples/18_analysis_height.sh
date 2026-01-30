#!/bin/bash
# ============================================================
# Example 18: 흡착 높이 분석
# ============================================================
# 테스트: surfscreen analysis height
# 설명: 흡착 구조에서 분자-표면 거리 분석
# ============================================================

set -e

echo "========================================"
echo "Example 18: Adsorption Height Analysis"
echo "========================================"

mkdir -p output/18_height
cd output/18_height

# 스크리닝으로 흡착 구조 생성
echo ""
echo "[1/3] Generating adsorption structures..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 3x3x1 -o Cu111.xyz
surfscreen molecule from-pubchem water -o water.xyz
surfscreen adsorb generate -s Cu111.xyz -m water.xyz -H 2.0,2.5,3.0 -o configs/
echo "✓ Configs generated"

# 각 구조의 흡착 높이 분석
echo ""
echo "[2/3] Analyzing adsorption heights..."
for xyz in configs/*.xyz; do
    echo ""
    echo "--- $(basename $xyz) ---"
    surfscreen analysis height "$xyz" --n-surface 27
done

echo ""
echo "[3/3] Done!"

echo ""
echo "========================================"
echo "✅ Example 18 completed!"
echo "========================================"
