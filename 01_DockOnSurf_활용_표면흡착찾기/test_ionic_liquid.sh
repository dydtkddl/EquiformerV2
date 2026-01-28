#!/bin/bash
# ============================================
# 대규모 분자 테스트 (이온성 액체)
# EMIM+ 양이온 MACE 최적화
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/ionic_liquid_test"
EMIM="${SCRIPT_DIR}/structures/molecules/emim.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "Ionic Liquid (EMIM+) MACE Test"
echo "Date: $(date)"
echo "=========================================="

# 가짜 SLURM PATH 추가
export PATH="${SCRIPT_DIR}/bin:$PATH"

# 작업 디렉토리 준비
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 파일 복사
cp "$EMIM" ./emim.xyz

echo ""
echo "[1] EMIM+ structure:"
cat emim.xyz

# MACE 최적화 실행
echo ""
echo "[2] Running MACE optimization on EMIM+..."
python << 'PYEOF'
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import mace_mp

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

# MACE 모델 로드
calc = mace_mp(model="medium", device=device, default_dtype="float32")

# EMIM+ 읽기
atoms = read("emim.xyz")
atoms.calc = calc

print(f"\nInitial structure: {len(atoms)} atoms")
print(f"Formula: {atoms.get_chemical_formula()}")

initial_e = atoms.get_potential_energy()
print(f"Initial energy: {initial_e:.4f} eV")

# 최적화
print("\nOptimizing...")
opt = BFGS(atoms, logfile="opt.log", trajectory="opt.traj")
opt.run(fmax=0.05, steps=200)

final_e = atoms.get_potential_energy()
print(f"\nFinal energy: {final_e:.4f} eV")
print(f"Steps: {opt.nsteps}")
print(f"Energy change: {(final_e - initial_e)*1000:.2f} meV")

# 저장
write("emim_optimized.xyz", atoms)
print("\nSaved: emim_optimized.xyz")

# Forces 확인
forces = atoms.get_forces()
max_force = ((forces**2).sum(axis=1)**0.5).max()
print(f"Max force: {max_force:.6f} eV/Å")
PYEOF

echo ""
echo "=========================================="
echo "[3] Results:"
ls -la
if [ -f "emim_optimized.xyz" ]; then
    echo ""
    echo "=== Optimized structure ==="
    cat emim_optimized.xyz
fi
echo "=========================================="
