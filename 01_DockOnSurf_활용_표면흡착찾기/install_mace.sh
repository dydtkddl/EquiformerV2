#!/bin/bash
# ============================================
# MACE 설치 (기존 equiformer_v2 환경 사용)
# equiformer_v2 환경에 이미 PyTorch, ASE 등 설치됨
# ============================================

set -e

echo "=========================================="
echo "Installing MACE in equiformer_v2 environment"
echo "Date: $(date)"
echo "=========================================="

# 현재 환경 확인
echo ""
echo "[1] Current Environment Check"
echo "-----------------------------"
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
python -c "import ase; print(f'ASE: {ase.__version__}')"

# MACE 설치
echo ""
echo "[2] Installing MACE"
echo "-------------------"
pip install mace-torch --no-deps 2>/dev/null || pip install mace-torch

# 설치 확인
echo ""
echo "[3] Verifying MACE Installation"
echo "-------------------------------"
python -c "
from mace.calculators import mace_mp
print('MACE import: OK')
print('Foundation models available: mace-mp-0 (small, medium, large)')
"

echo ""
echo "=========================================="
echo "MACE installation completed!"
echo "=========================================="
