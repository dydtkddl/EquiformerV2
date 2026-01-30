#!/bin/bash
# ============================================================
# Example 03: 분자 Conformer 생성
# ============================================================
# 테스트: surfscreen molecule conformers
# 설명: 분자의 다양한 conformer (배열) 생성
# ============================================================

set -e

echo "========================================"
echo "Example 03: Conformer Generation"
echo "========================================"

mkdir -p output/03_conformers
cd output/03_conformers

# 먼저 테스트용 분자 생성
echo ""
echo "[1/3] Creating test molecule (propanol)..."
surfscreen molecule from-smiles "CCCO" -o propanol.xyz --name Propanol

# RDKit 엔진으로 conformer 생성
echo ""
echo "[2/3] Generating conformers with RDKit..."
surfscreen molecule conformers propanol.xyz --engine rdkit --n-conformers 10 -o conformers_rdkit/
echo "✓ conformers_rdkit/ created"

# 결과 확인
echo ""
echo "[3/3] Checking results..."
echo "Generated conformers:"
ls -la conformers_rdkit/

echo ""
echo "========================================"
echo "✅ Example 03 completed!"
echo "Conformer directory: conformers_rdkit/"
echo "========================================"
