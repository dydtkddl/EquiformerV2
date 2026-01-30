#!/bin/bash
# ============================================================
# Example 01: PubChem에서 분자 다운로드
# ============================================================
# 테스트: surfscreen molecule from-pubchem
# 설명: PubChem 데이터베이스에서 분자를 이름/CID/화학식으로 검색하여 다운로드
# ============================================================

set -e  # 오류 시 중단

echo "========================================"
echo "Example 01: PubChem Molecule Download"
echo "========================================"

mkdir -p output/01_pubchem
cd output/01_pubchem

# 1. 이름으로 검색 (기본)
echo ""
echo "[1/4] Fetching water by name..."
surfscreen molecule from-pubchem water -o water.xyz
echo "✓ water.xyz created"

# 2. 다른 분자들
echo ""
echo "[2/4] Fetching ethanol by name..."
surfscreen molecule from-pubchem ethanol -o ethanol.xyz
echo "✓ ethanol.xyz created"

# 3. 화학식으로 검색
echo ""
echo "[3/4] Fetching CO2 by formula..."
surfscreen molecule from-pubchem CO2 --by formula -o co2.xyz
echo "✓ co2.xyz created"

# 4. CID로 검색
echo ""
echo "[4/4] Fetching aspirin by CID (2244)..."
surfscreen molecule from-pubchem 2244 --by cid -o aspirin.xyz
echo "✓ aspirin.xyz created"

echo ""
echo "========================================"
echo "✅ Example 01 completed!"
echo "Output files:"
ls -la *.xyz
echo "========================================"
