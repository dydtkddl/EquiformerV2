#!/bin/bash
# ============================================================
# Example 06: 표면 흡착 사이트 감지
# ============================================================
# 테스트: surfscreen surface sites
# 설명: 표면의 흡착 사이트 (ontop, bridge, hollow) 감지
# ============================================================

set -e

echo "========================================"
echo "Example 06: Adsorption Site Detection"
echo "========================================"

mkdir -p output/06_sites
cd output/06_sites

# 표면 생성
echo ""
echo "[1/3] Creating Cu(111) surface..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 3x3x1 -o Cu111.xyz
echo "✓ Cu111.xyz created"

# 사이트 감지
echo ""
echo "[2/3] Detecting adsorption sites..."
surfscreen surface sites Cu111.xyz
echo ""

# 특정 사이트만 감지
echo ""
echo "[3/3] Detecting only hollow sites..."
surfscreen surface sites Cu111.xyz --types hollow

echo ""
echo "========================================"
echo "✅ Example 06 completed!"
echo "========================================"
