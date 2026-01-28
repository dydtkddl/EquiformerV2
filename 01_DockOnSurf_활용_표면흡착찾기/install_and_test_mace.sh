#!/bin/bash
# ============================================
# MACE 전체 의존성 설치 + 테스트
# equiformer_v2 환경에서 실행
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/mace_test"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"

echo "=========================================="
echo "MACE Full Installation & Test"
echo "Date: $(date)"
echo "=========================================="

# 1. 의존성 설치
echo ""
echo "[1] Installing MACE dependencies"
echo "---------------------------------"
pip install torch-ema torchmetrics configargparse matscipy orjson prettytable python-hostlist

# 2. MACE 재설치 (의존성 포함)
echo ""
echo "[2] Installing/Upgrading MACE"
echo "-----------------------------"
pip install --upgrade mace-torch

# 3. 설치 확인
echo ""
echo "[3] Verifying Installation"
echo "--------------------------"
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')

from mace.calculators import mace_mp
print('MACE import: OK')
"

# 4. 테스트 실행
echo ""
echo "[4] Running MACE Optimization Test"
echo "-----------------------------------"

mkdir -p "$WORK_DIR"

export SCRIPT_DIR WORK_DIR MOLECULE

python << 'EOF'
import os
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import mace_mp

work_dir = os.environ['WORK_DIR']
mol_path = os.environ['MOLECULE']

print(f"Input: {mol_path}")

# Device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

# MACE-MP-0 Foundation Model
print("Loading MACE-MP-0 model...")
calc = mace_mp(model="medium", device=device, default_dtype="float32")
print("Model loaded!")

# 분자 읽기
atoms = read(mol_path)
atoms.calc = calc

print(f"Molecule: {atoms.get_chemical_formula()}")
print(f"Initial energy: {atoms.get_potential_energy():.4f} eV")

# 최적화
print("\nOptimizing...")
opt = BFGS(atoms, trajectory=f"{work_dir}/opt.traj", logfile=f"{work_dir}/opt.log")
opt.run(fmax=0.05, steps=100)

print(f"Final energy: {atoms.get_potential_energy():.4f} eV")
print(f"Steps: {opt.nsteps}")

# 저장
output_path = f"{work_dir}/methanol_opt.xyz"
write(output_path, atoms)
print(f"Saved: {output_path}")

print("\n✅ MACE test completed successfully!")
EOF

echo ""
echo "=========================================="
echo "Results:"
ls -la "$WORK_DIR"
echo "=========================================="
