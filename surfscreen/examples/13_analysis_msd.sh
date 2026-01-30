#!/bin/bash
# ============================================================
# Example 13: MSD 및 확산 계수 분석
# ============================================================
# 테스트: surfscreen analysis msd, diffusion
# 설명: 궤적에서 MSD 계산 및 확산 계수 추출
# ============================================================

set -e

echo "========================================"
echo "Example 13: MSD & Diffusion Analysis"
echo "========================================"

mkdir -p output/13_msd
cd output/13_msd

# 먼저 MD 실행하여 궤적 생성
echo ""
echo "[1/4] Running MD to generate trajectory..."
surfscreen surface create Cu --miller 111 --layers 2 --supercell 2x2x1 -o Cu111.xyz
surfscreen md run Cu111.xyz \
    --ensemble nvt \
    --temperature 500 \
    --steps 200 \
    --engine mace \
    --device cpu \
    -o md_output/
echo "✓ MD completed"

# MSD 계산
echo ""
echo "[2/4] Calculating MSD for Cu atoms..."
surfscreen analysis msd md_output/trajectory.traj -s Cu --timestep 1.0 -o msd_plot.html
echo "✓ MSD calculated"

# 확산 계수 계산
echo ""
echo "[3/4] Calculating diffusion coefficient..."
surfscreen analysis diffusion md_output/trajectory.traj -s Cu --timestep 1.0

# 결과 확인
echo ""
echo "[4/4] Results summary..."
echo "MSD Plot: msd_plot.html"

echo ""
echo "========================================"
echo "✅ Example 13 completed!"
echo "========================================"
