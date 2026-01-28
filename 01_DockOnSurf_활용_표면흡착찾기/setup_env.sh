#!/bin/bash
# ============================================
# DockOnSurf + MACE 환경 설치 스크립트
# HPC 클러스터에서 실행
# ============================================

set -e

echo "=========================================="
echo "DockOnSurf + MACE Environment Setup"
echo "Date: $(date)"
echo "=========================================="

# 1. DockOnSurf 환경 생성
echo ""
echo "[1] Creating DockOnSurf Environment"
echo "-----------------------------------"
if conda env list | grep -q "^dockonsurf "; then
    echo "dockonsurf env already exists, skipping..."
else
    conda create -n dockonsurf python=3.10 -y
    conda activate dockonsurf
    pip install dockonsurf ase rdkit-pypi pymatgen networkx hdbscan
    conda deactivate
    echo "dockonsurf env created successfully"
fi

# 2. MACE 환경 생성
echo ""
echo "[2] Creating MACE Environment"
echo "-----------------------------"
if conda env list | grep -q "^mace "; then
    echo "mace env already exists, skipping..."
else
    conda create -n mace python=3.10 -y
    conda activate mace
    pip install torch --index-url https://download.pytorch.org/whl/cu121
    pip install mace-torch ase
    conda deactivate
    echo "mace env created successfully"
fi

# 3. CP2K 데이터 경로 설정
echo ""
echo "[3] Setting up CP2K Data Path"
echo "-----------------------------"
if grep -q "CP2K_DATA_DIR" ~/.bashrc; then
    echo "CP2K_DATA_DIR already in .bashrc"
else
    echo 'export CP2K_DATA_DIR="$HOME/cp2k/data"' >> ~/.bashrc
    echo "Added CP2K_DATA_DIR to .bashrc"
fi

# 4. 검증
echo ""
echo "[4] Verifying Installation"
echo "--------------------------"
echo "DockOnSurf:"
conda run -n dockonsurf python -c "import ase; print(f'  ASE: {ase.__version__}')" 2>/dev/null || echo "  ERROR: ASE not found"

echo "MACE:"
conda run -n mace python -c "
import torch
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA: {torch.cuda.is_available()}')
from mace.calculators import mace_mp
print('  MACE: OK')
" 2>/dev/null || echo "  ERROR: MACE not working"

echo ""
echo "=========================================="
echo "Setup completed!"
echo "Run 'source ~/.bashrc' to apply changes"
echo "=========================================="
