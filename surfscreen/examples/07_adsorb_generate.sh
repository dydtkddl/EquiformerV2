#!/bin/bash
# ============================================================
# Example 07: 흡착 구성 생성
# ============================================================
# 테스트: surfscreen adsorb generate
# 설명: 다양한 회전 각도와 높이로 흡착 구성 사전 생성
# ============================================================

set -e

echo "========================================"
echo "Example 07: Adsorption Config Generation"
echo "========================================"

mkdir -p output/07_adsorb
cd output/07_adsorb

# 표면과 분자 준비
echo ""
echo "[1/4] Preparing surface and molecule..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 3x3x1 -o Cu111.xyz
surfscreen molecule from-pubchem water -o water.xyz
echo "✓ Surface and molecule ready"

# 기본 구성 생성
echo ""
echo "[2/4] Generating default configs..."
surfscreen adsorb generate -s Cu111.xyz -m water.xyz -o configs_default/
echo "✓ configs_default/ created"

# 세밀한 회전과 높이
echo ""
echo "[3/4] Generating configs with custom rotations and heights..."
surfscreen adsorb generate -s Cu111.xyz -m water.xyz \
    -r 0,30,60,90,120,150 \
    -H 1.5,2.0,2.5,3.0 \
    --max-configs 50 \
    -o configs_fine/
echo "✓ configs_fine/ created"

# 결과 확인
echo ""
echo "[4/4] Checking results..."
echo "Default configs: $(ls configs_default/*.xyz 2>/dev/null | wc -l) files"
echo "Fine configs: $(ls configs_fine/*.xyz 2>/dev/null | wc -l) files"

echo ""
echo "========================================"
echo "✅ Example 07 completed!"
echo "========================================"
