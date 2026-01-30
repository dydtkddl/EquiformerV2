#!/bin/bash
# ============================================================
# Example 16: MD 앙상블 비교 (NVT vs NVE)
# ============================================================
# 테스트: surfscreen md run --ensemble nvt/nve
# 설명: 다양한 앙상블에서 MD 실행 및 비교
# ============================================================

set -e

echo "========================================"
echo "Example 16: MD Ensemble Comparison"
echo "========================================"

mkdir -p output/16_ensembles
cd output/16_ensembles

# 표면 생성
echo ""
echo "[1/4] Creating surface..."
surfscreen surface create Cu --miller 111 --layers 2 --supercell 2x2x1 -o Cu111.xyz

# NVT 앙상블
echo ""
echo "[2/4] Running NVT MD..."
surfscreen md run Cu111.xyz \
    --ensemble nvt \
    --temperature 300 \
    --thermostat langevin \
    --steps 100 \
    --engine mace \
    --device cpu \
    -o md_nvt/
echo "✓ NVT completed"

# NVE 앙상블
echo ""
echo "[3/4] Running NVE MD..."
surfscreen md run Cu111.xyz \
    --ensemble nve \
    --steps 100 \
    --engine mace \
    --device cpu \
    -o md_nve/
echo "✓ NVE completed"

# 리포트 생성
echo ""
echo "[4/4] Generating reports..."
surfscreen md report md_nvt/ -o report_nvt.html
surfscreen md report md_nve/ -o report_nve.html

echo ""
echo "========================================"
echo "✅ Example 16 completed!"
echo "Compare: report_nvt.html vs report_nve.html"
echo ""
echo "NVT: Temperature controlled (thermostat)"
echo "NVE: Energy conserved (no thermostat)"
echo "========================================"
