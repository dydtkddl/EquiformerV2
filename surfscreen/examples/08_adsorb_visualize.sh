#!/bin/bash
# ============================================================
# Example 08: 흡착 구성 시각화
# ============================================================
# 테스트: surfscreen adsorb visualize
# 설명: 생성된 흡착 구성을 HTML로 시각화
# ============================================================

set -e

echo "========================================"
echo "Example 08: Adsorption Config Visualization"
echo "========================================"

mkdir -p output/08_visualize
cd output/08_visualize

# 표면과 분자 준비
echo ""
echo "[1/3] Preparing surface and molecule..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 3x3x1 -o Cu111.xyz
surfscreen molecule from-pubchem ethanol -o ethanol.xyz

# 구성 생성
echo ""
echo "[2/3] Generating configurations..."
surfscreen adsorb generate -s Cu111.xyz -m ethanol.xyz -r 0,45,90 -H 2.0,2.5 -o configs/

# HTML 시각화
echo ""
echo "[3/3] Generating HTML visualization..."
surfscreen adsorb visualize configs/ -o configs_preview.html

echo ""
echo "========================================"
echo "✅ Example 08 completed!"
echo "Generated: configs_preview.html"
echo "Open in browser: firefox configs_preview.html"
echo "========================================"
