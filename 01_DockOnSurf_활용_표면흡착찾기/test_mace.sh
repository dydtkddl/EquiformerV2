#!/bin/bash
# ============================================
# MACE 테스트 (equiformer_v2 환경에서 직접 실행)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/mace_test"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"

mkdir -p "$WORK_DIR"

echo "=========================================="
echo "MACE Standalone Test"
echo "Date: $(date)"
echo "=========================================="

# 환경 변수 설정
export SCRIPT_DIR WORK_DIR MOLECULE

echo ""
echo "Input: $MOLECULE"
echo "Output: $WORK_DIR/methanol_opt.xyz"
echo ""

python << 'EOF'
import os
import torch
from ase.io import read, write
from ase.optimize import BFGS

# 경로
work_dir = os.environ['WORK_DIR']
mol_path = os.environ['MOLECULE']

print(f"Loading molecule from: {mol_path}")

# Device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# MACE-MP-0 Foundation Model
print("Loading MACE-MP-0 model...")
from mace.calculators import mace_mp
calc = mace_mp(model="medium", device=device, default_dtype="float32")
print("Model loaded successfully!")

# 분자 읽기
atoms = read(mol_path)
atoms.calc = calc

print(f"Molecule: {atoms.get_chemical_formula()}")
print(f"Initial energy: {atoms.get_potential_energy():.4f} eV")

# 최적화
print("\nOptimizing structure...")
opt = BFGS(atoms, trajectory=f"{work_dir}/opt.traj", logfile=f"{work_dir}/opt.log")
opt.run(fmax=0.05, steps=100)

print(f"Final energy: {atoms.get_potential_energy():.4f} eV")
print(f"Optimization steps: {opt.nsteps}")

# 저장
output_path = f"{work_dir}/methanol_opt.xyz"
write(output_path, atoms)
print(f"\nSaved optimized structure to: {output_path}")

print("\n✅ MACE test completed successfully!")
EOF

echo ""
echo "=========================================="
echo "Results saved to: $WORK_DIR"
ls -la "$WORK_DIR"
echo "=========================================="
