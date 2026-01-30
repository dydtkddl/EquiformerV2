#!/bin/bash
# ============================================================
# Example 15: Boltzmann 분포 분석
# ============================================================
# 테스트: surfscreen analysis boltzmann
# 설명: 스크리닝 결과에서 Boltzmann 분포 계산
# ============================================================

set -e

echo "========================================"
echo "Example 15: Boltzmann Distribution"
echo "========================================"

mkdir -p output/15_boltzmann
cd output/15_boltzmann

# 스크리닝 실행 (또는 이전 결과 사용)
echo ""
echo "[1/3] Running screening for test data..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 3x3x1 -o Cu111.xyz
surfscreen molecule from-pubchem water -o water.xyz

surfscreen screen run \
    -s Cu111.xyz \
    -m water.xyz \
    --engine mace \
    --device cpu \
    --max-configs 8 \
    -o screening/
echo "✓ Screening completed"

# Boltzmann 분포 계산
echo ""
echo "[2/3] Calculating Boltzmann distribution at different temperatures..."
for temp in 300 500 1000; do
    echo "  Temperature: ${temp}K"
    surfscreen analysis boltzmann screening/ -T $temp -o boltzmann_${temp}K.html
done
echo "✓ Boltzmann distributions calculated"

# 결과
echo ""
echo "[3/3] Results..."
ls -la boltzmann_*.html

echo ""
echo "========================================"
echo "✅ Example 15 completed!"
echo "Generated Boltzmann plots for 300K, 500K, 1000K"
echo "========================================"
