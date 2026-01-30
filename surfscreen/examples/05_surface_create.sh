#!/bin/bash
# ============================================================
# Example 05: 다양한 금속 표면 생성
# ============================================================
# 테스트: surfscreen surface create
# 설명: 다양한 금속과 밀러 지수로 표면 슬랩 생성
# ============================================================

set -e

echo "========================================"
echo "Example 05: Surface Creation"
echo "========================================"

mkdir -p output/05_surfaces
cd output/05_surfaces

# 1. Cu(111) 표면
echo ""
echo "[1/5] Creating Cu(111) surface..."
surfscreen surface create Cu --miller 111 --layers 4 --supercell 3x3x1 --vacuum 15.0 -o Cu111.xyz
echo "✓ Cu111.xyz created"

# 2. Au(100) 표면
echo ""
echo "[2/5] Creating Au(100) surface..."
surfscreen surface create Au --miller 100 --layers 3 --supercell 2x2x1 --vacuum 12.0 -o Au100.xyz
echo "✓ Au100.xyz created"

# 3. Pt(111) 표면
echo ""
echo "[3/5] Creating Pt(111) surface..."
surfscreen surface create Pt --miller 111 --layers 4 --supercell 3x3x1 -o Pt111.xyz
echo "✓ Pt111.xyz created"

# 4. Ag(110) 표면
echo ""
echo "[4/5] Creating Ag(110) surface..."
surfscreen surface create Ag --miller 110 --layers 4 --supercell 2x3x1 -o Ag110.xyz
echo "✓ Ag110.xyz created"

# 5. 하층 고정 표면
echo ""
echo "[5/5] Creating Cu(111) with fixed bottom layers..."
surfscreen surface create Cu --miller 111 --layers 5 --supercell 3x3x1 --fix 2 -o Cu111_fixed.xyz
echo "✓ Cu111_fixed.xyz created (2 bottom layers fixed)"

echo ""
echo "========================================"
echo "✅ Example 05 completed!"
echo "Output files:"
ls -la *.xyz
echo "========================================"
