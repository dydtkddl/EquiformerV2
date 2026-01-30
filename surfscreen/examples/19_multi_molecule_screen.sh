#!/bin/bash
# ============================================================
# Example 19: 다분자 스크리닝
# ============================================================
# 테스트: surfscreen screen run -m mol1.xyz -m mol2.xyz
# 설명: 여러 분자를 동시에 한 표면에 스크리닝
# ============================================================

set -e

echo "========================================"
echo "Example 19: Multi-Molecule Screening"
echo "========================================"

mkdir -p output/19_multi
cd output/19_multi

# 표면 준비
echo ""
echo "[1/4] Preparing surface..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 3x3x1 -o Cu111.xyz

# 여러 분자 준비
echo ""
echo "[2/4] Preparing multiple molecules..."
surfscreen molecule from-pubchem water -o water.xyz
surfscreen molecule from-pubchem methanol -o methanol.xyz
surfscreen molecule from-pubchem ethanol -o ethanol.xyz
echo "✓ 3 molecules ready"

# 각 분자별 스크리닝
echo ""
echo "[3/4] Screening each molecule..."
for mol in water methanol ethanol; do
    echo ""
    echo "--- Screening $mol ---"
    surfscreen screen run \
        -s Cu111.xyz \
        -m ${mol}.xyz \
        --engine mace \
        --device cpu \
        --max-configs 5 \
        -o results_${mol}/
done

# 결과 비교
echo ""
echo "[4/4] Comparing results..."
for mol in water methanol ethanol; do
    echo ""
    echo "=== $mol on Cu(111) ==="
    surfscreen screen results results_${mol}/results.json --top 3
done

echo ""
echo "========================================"
echo "✅ Example 19 completed!"
echo "========================================"
