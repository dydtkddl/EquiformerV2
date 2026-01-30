#!/bin/bash
# ============================================================
# Example 09: MD 시뮬레이션 (MACE 엔진)
# ============================================================
# 테스트: surfscreen md run
# 설명: MACE 기반 MD 시뮬레이션 실행
# ⚠️ GPU 권장 (CPU도 가능하지만 느림)
# ============================================================

set -e

echo "========================================"
echo "Example 09: MD Simulation with MACE"
echo "========================================"

mkdir -p output/09_md_mace
cd output/09_md_mace

# 표면 생성
echo ""
echo "[1/4] Creating surface..."
surfscreen surface create Cu --miller 111 --layers 3 --supercell 2x2x1 --vacuum 10.0 -o Cu111.xyz
echo "✓ Cu111.xyz created"

# NVT MD 실행 (짧은 테스트)
echo ""
echo "[2/4] Running NVT MD (100 steps, CPU mode)..."
surfscreen md run Cu111.xyz \
    --ensemble nvt \
    --temperature 300 \
    --timestep 1.0 \
    --steps 100 \
    --engine mace \
    --model medium \
    --device cpu \
    -o md_nvt/
echo "✓ NVT MD completed"

# 상태 확인
echo ""
echo "[3/4] Checking MD status..."
surfscreen md status md_nvt/

# 리포트 생성
echo ""
echo "[4/4] Generating MD report..."
surfscreen md report md_nvt/ -o md_report.html

echo ""
echo "========================================"
echo "✅ Example 09 completed!"
echo "Output directory: md_nvt/"
echo "Report: md_report.html"
echo "Trajectory files:"
ls -la md_nvt/*.xyz md_nvt/*.extxyz md_nvt/*.traj 2>/dev/null || echo "(trajectory files)"
echo "========================================"
