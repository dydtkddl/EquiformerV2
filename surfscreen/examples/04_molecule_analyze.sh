#!/bin/bash
# ============================================================
# Example 04: 분자 분석
# ============================================================
# 테스트: surfscreen molecule analyze
# 설명: 분자의 구조, 원자 구성, 분자량 등 분석
# ============================================================

set -e

echo "========================================"
echo "Example 04: Molecule Analysis"
echo "========================================"

mkdir -p output/04_analyze
cd output/04_analyze

# 여러 분자 생성 및 분석
molecules=("water" "ethanol" "benzene")

for mol in "${molecules[@]}"; do
    echo ""
    echo "--- Analyzing $mol ---"
    surfscreen molecule from-pubchem "$mol" -o "${mol}.xyz"
    echo ""
    surfscreen molecule analyze "${mol}.xyz"
    echo ""
done

echo ""
echo "========================================"
echo "✅ Example 04 completed!"
echo "========================================"
