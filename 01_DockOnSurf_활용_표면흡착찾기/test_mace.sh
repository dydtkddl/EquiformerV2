#!/bin/bash
# ============================================
# MACE 단독 테스트 스크립트
# DockOnSurf 없이 MACE만 테스트
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

# MACE Foundation Model로 최적화 테스트
echo ""
echo "Testing MACE-MP-0 optimization..."
echo ""

conda run -n mace python << 'EOF'
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import mace_mp
import os

# 경로 설정
script_dir = os.environ.get('SCRIPT_DIR', '.')
work_dir = os.environ.get('WORK_DIR', './work/mace_test')
mol_path = os.environ.get('MOLECULE', 'structures/molecules/methanol.xyz')

print(f"Input: {mol_path}")
print(f"Output: {work_dir}/methanol_opt.xyz")

# Device 선택
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

# MACE-MP-0 Foundation Model 로드
print("Loading MACE-MP-0 model...")
calc = mace_mp(model="medium", device=device, default_dtype="float32")

# 분자 읽기
atoms = read(mol_path)
atoms.calc = calc

print(f"Initial energy: {atoms.get_potential_energy():.4f} eV")

# 최적화
opt = BFGS(atoms, trajectory=f"{work_dir}/opt.traj")
opt.run(fmax=0.05, steps=100)

print(f"Final energy: {atoms.get_potential_energy():.4f} eV")

# 저장
write(f"{work_dir}/methanol_opt.xyz", atoms)
print(f"Saved optimized structure")

print("\n✅ MACE test completed successfully!")
EOF

echo ""
echo "Results saved to: $WORK_DIR"
echo "=========================================="
