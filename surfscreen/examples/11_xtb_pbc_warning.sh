#!/bin/bash
# ============================================================
# Example 11: xTB + PBC 경고 테스트
# ============================================================
# 테스트: surfscreen md run --engine xtb (표면에서)
# 설명: xTB + PBC 경고 메시지 및 --force-xtb 테스트
# ============================================================

set -e

echo "========================================"
echo "Example 11: xTB + PBC Warning Test"
echo "========================================"

mkdir -p output/11_xtb_warning
cd output/11_xtb_warning

# 표면 생성 (PBC 있음)
echo ""
echo "[1/3] Creating surface with PBC..."
surfscreen surface create Cu --miller 111 --layers 2 --supercell 2x2x1 -o Cu111.xyz
echo "✓ Cu111.xyz created (has PBC)"

# xTB + PBC = 오류 (예상됨)
echo ""
echo "[2/3] Testing xTB + PBC (should fail)..."
echo "Running: surfscreen md run Cu111.xyz --engine xtb --steps 10"
if surfscreen md run Cu111.xyz --engine xtb --steps 10 -o md_fail/ 2>&1; then
    echo "⚠️ Unexpected: Command succeeded"
else
    echo "✓ Expected: xTB + PBC correctly rejected!"
fi

# --force-xtb로 강제 실행 시도
echo ""
echo "[3/3] Testing --force-xtb flag..."
echo "Running: surfscreen md run Cu111.xyz --engine xtb --force-xtb --steps 10"
echo "(This may fail at xTB level, but the warning should appear)"
surfscreen md run Cu111.xyz --engine xtb --force-xtb --steps 10 -o md_force/ 2>&1 || true

echo ""
echo "========================================"
echo "✅ Example 11 completed!"
echo "This demonstrates the xTB+PBC safety check."
echo "For surface MD, always use: --engine mace"
echo "========================================"
