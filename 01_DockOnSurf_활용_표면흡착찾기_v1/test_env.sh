#!/bin/bash
# ============================================
# DockOnSurf Pipeline Environment Test Script
# HPC 클러스터에서 실행하여 로그 확인
# ============================================

echo "=========================================="
echo "DockOnSurf Pipeline Environment Check"
echo "Date: $(date)"
echo "Host: $(hostname)"
echo "=========================================="

# 1. Conda 확인
echo ""
echo "[1] Conda Environment Check"
echo "----------------------------"
conda --version 2>&1 || echo "ERROR: conda not found"

# 2. DockOnSurf 환경
echo ""
echo "[2] DockOnSurf Environment"
echo "--------------------------"
if conda env list | grep -q dockonsurf; then
    echo "dockonsurf env: Found"
    conda run -n dockonsurf python -c "
import sys
print(f'Python: {sys.version}')
try:
    import dockonsurf
    print(f'DockOnSurf: OK')
except ImportError as e:
    print(f'DockOnSurf: FAILED - {e}')
try:
    import ase
    print(f'ASE: {ase.__version__}')
except ImportError as e:
    print(f'ASE: FAILED - {e}')
try:
    import rdkit
    print(f'RDKit: OK')
except ImportError as e:
    print(f'RDKit: FAILED - {e}')
"
else
    echo "dockonsurf env: NOT FOUND"
fi

# 3. MACE 환경
echo ""
echo "[3] MACE Environment"
echo "--------------------"
if conda env list | grep -q mace; then
    echo "mace env: Found"
    conda run -n mace python -c "
import sys
print(f'Python: {sys.version}')
try:
    import torch
    print(f'PyTorch: {torch.__version__}')
    print(f'CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'CUDA device: {torch.cuda.get_device_name(0)}')
except ImportError as e:
    print(f'PyTorch: FAILED - {e}')
try:
    from mace.calculators import MACECalculator
    print(f'MACE: OK')
except ImportError as e:
    print(f'MACE: FAILED - {e}')
"
else
    echo "mace env: NOT FOUND"
fi

# 4. CP2K 확인
echo ""
echo "[4] CP2K Installation"
echo "---------------------"
if command -v cp2k.psmp &> /dev/null; then
    echo "cp2k.psmp: Found at $(which cp2k.psmp)"
    cp2k.psmp --version 2>&1 | head -3
elif command -v cp2k.popt &> /dev/null; then
    echo "cp2k.popt: Found at $(which cp2k.popt)"
    cp2k.popt --version 2>&1 | head -3
else
    echo "CP2K: NOT FOUND in PATH"
fi

# 5. CP2K 데이터 파일
echo ""
echo "[5] CP2K Data Files"
echo "-------------------"
if [ -n "$CP2K_DATA_DIR" ]; then
    echo "CP2K_DATA_DIR: $CP2K_DATA_DIR"
    if [ -f "$CP2K_DATA_DIR/BASIS_MOLOPT" ]; then
        echo "BASIS_MOLOPT: Found"
    else
        echo "BASIS_MOLOPT: NOT FOUND"
    fi
    if [ -f "$CP2K_DATA_DIR/GTH_POTENTIALS" ]; then
        echo "GTH_POTENTIALS: Found"
    else
        echo "GTH_POTENTIALS: NOT FOUND"
    fi
    if [ -f "$CP2K_DATA_DIR/dftd3.dat" ]; then
        echo "dftd3.dat: Found"
    else
        echo "dftd3.dat: NOT FOUND"
    fi
else
    echo "CP2K_DATA_DIR: NOT SET"
    echo "Checking ~/cp2k/data..."
    if [ -d "$HOME/cp2k/data" ]; then
        echo "Found at: $HOME/cp2k/data"
        ls -la "$HOME/cp2k/data" | head -10
    fi
fi

# 6. GPU 확인
echo ""
echo "[6] GPU Status"
echo "--------------"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
else
    echo "nvidia-smi: NOT FOUND"
fi

echo ""
echo "=========================================="
echo "Environment check completed"
echo "=========================================="
