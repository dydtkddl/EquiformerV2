#!/bin/bash
# ============================================================
# Example 02: SMILES로 분자 생성
# ============================================================
# 테스트: surfscreen molecule from-smiles
# 설명: SMILES 문자열로부터 3D 분자 구조 생성
# ============================================================

set -e

echo "========================================"
echo "Example 02: SMILES to 3D Molecule"
echo "========================================"

mkdir -p output/02_smiles
cd output/02_smiles

# 1. 간단한 분자 (메탄)
echo ""
echo "[1/4] Creating methane from SMILES..."
surfscreen molecule from-smiles "C" -o methane.xyz --name Methane
echo "✓ methane.xyz created"

# 2. 에탄올
echo ""
echo "[2/4] Creating ethanol from SMILES..."
surfscreen molecule from-smiles "CCO" -o ethanol_smiles.xyz --name Ethanol
echo "✓ ethanol_smiles.xyz created"

# 3. 벤젠
echo ""
echo "[3/4] Creating benzene from SMILES..."
surfscreen molecule from-smiles "c1ccccc1" -o benzene.xyz --name Benzene
echo "✓ benzene.xyz created"

# 4. 최적화 포함
echo ""
echo "[4/4] Creating acetone with optimization..."
surfscreen molecule from-smiles "CC(=O)C" -o acetone_opt.xyz --name Acetone --optimize
echo "✓ acetone_opt.xyz created (optimized)"

echo ""
echo "========================================"
echo "✅ Example 02 completed!"
echo "Output files:"
ls -la *.xyz
echo "========================================"
