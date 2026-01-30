#!/bin/bash
# ============================================================
# Example 10: MD 시뮬레이션 (xTB 엔진 - 분자용)
# ============================================================
# 테스트: surfscreen md run --engine xtb
# 설명: xTB 기반 MD 시뮬레이션 (분자/클러스터용)
# ⚠️ 주의: xTB는 PBC 없는 분자에만 사용 가능!
# ============================================================

set -e

echo "========================================"
echo "Example 10: MD Simulation with xTB"
echo "========================================"

mkdir -p output/10_md_xtb
cd output/10_md_xtb

# 분자 생성 (PBC 없음)
echo ""
echo "[1/3] Creating isolated molecule (no PBC)..."
surfscreen molecule from-pubchem ethanol -o ethanol.xyz
echo "✓ ethanol.xyz created"

# xTB MD 실행
echo ""
echo "[2/3] Running NVT MD with xTB (50 steps)..."
surfscreen md run ethanol.xyz \
    --ensemble nvt \
    --temperature 300 \
    --timestep 0.5 \
    --steps 50 \
    --engine xtb \
    -o md_xtb/
echo "✓ xTB MD completed"

# 상태 확인
echo ""
echo "[3/3] Checking MD status..."
surfscreen md status md_xtb/

echo ""
echo "========================================"
echo "✅ Example 10 completed!"
echo "Note: xTB is for molecules without PBC."
echo "For surfaces, use --engine mace instead."
echo "========================================"
