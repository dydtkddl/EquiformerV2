#!/bin/bash
# ============================================
# MACE용 SLURM submission script 템플릿
# DockOnSurf가 이 스크립트를 호출합니다
# ============================================
#SBATCH --job-name=mace_opt
#SBATCH --output=mace_%j.out
#SBATCH --error=mace_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00

# Conda 환경 활성화
source ~/anaconda3/etc/profile.d/conda.sh
conda activate equiformer_v2

# 작업 디렉토리로 이동
cd $SLURM_SUBMIT_DIR 2>/dev/null || cd $(dirname $0)

echo "Starting MACE optimization..."
echo "Working directory: $(pwd)"
echo "Date: $(date)"

# MACE 최적화 실행
python << 'PYEOF'
import os
import sys
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import mace_mp

# 입력/출력 파일 찾기
input_file = os.environ.get('INPUT_FILE', 'input.xyz')
output_file = os.environ.get('OUTPUT_FILE', 'optimized.xyz')

print(f"Input: {input_file}")
print(f"Output: {output_file}")

# MACE 로드
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

calc = mace_mp(model="medium", device=device, default_dtype="float32")

# 구조 읽기
atoms = read(input_file)
atoms.calc = calc

print(f"Initial energy: {atoms.get_potential_energy():.4f} eV")

# 최적화
opt = BFGS(atoms, logfile="opt.log")
opt.run(fmax=0.05, steps=100)

print(f"Final energy: {atoms.get_potential_energy():.4f} eV")
print(f"Steps: {opt.nsteps}")

# 저장
write(output_file, atoms)
print(f"Saved: {output_file}")
PYEOF

echo "MACE optimization completed"
