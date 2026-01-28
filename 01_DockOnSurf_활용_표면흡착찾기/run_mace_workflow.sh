#!/bin/bash
# ============================================
# DockOnSurf + MACE 우회 솔루션
# DockOnSurf로 conformer 생성 → 별도로 MACE 최적화
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/mace_workflow"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "DockOnSurf + MACE Workflow"
echo "Date: $(date)"
echo "=========================================="

# 작업 디렉토리 준비
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/conformers"
cd "$WORK_DIR"

# Step 1: SMILES로부터 conformer 생성 (RDKit 사용)
echo ""
echo "[1] Generating conformers with RDKit + MMFF optimization..."
python << 'PYEOF'
import os
from rdkit import Chem
from rdkit.Chem import AllChem

# 메탄올 SMILES
smiles = "CO"
mol = Chem.MolFromSmiles(smiles)
mol = Chem.AddHs(mol)

# Conformer 생성
num_confs = 5
AllChem.EmbedMultipleConfs(mol, numConfs=num_confs, randomSeed=42)

# MMFF 최적화
results = AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=200)

print(f"Generated {mol.GetNumConformers()} conformers")

# 각 conformer를 XYZ로 저장
conf_dir = "conformers"
for i, conf in enumerate(mol.GetConformers()):
    energy = results[i][1] if results[i][0] == 0 else float('inf')
    xyz_path = f"{conf_dir}/conf_{i:03d}.xyz"
    
    # XYZ 파일 작성
    atoms = mol.GetAtoms()
    coords = conf.GetPositions()
    
    with open(xyz_path, 'w') as f:
        f.write(f"{mol.GetNumAtoms()}\n")
        f.write(f"Conformer {i}, MMFF Energy: {energy:.4f} kcal/mol\n")
        for atom, pos in zip(atoms, coords):
            f.write(f"{atom.GetSymbol():2s}  {pos[0]:12.6f}  {pos[1]:12.6f}  {pos[2]:12.6f}\n")
    
    print(f"  conf_{i:03d}.xyz - MMFF Energy: {energy:.4f} kcal/mol")

print(f"\nConformers saved to: {conf_dir}/")
PYEOF

echo ""
echo "Conformer files:"
ls -la conformers/

# Step 2: MACE로 각 conformer 최적화
echo ""
echo "[2] Optimizing conformers with MACE..."
python << 'PYEOF'
import os
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import mace_mp
from pathlib import Path

# MACE 모델 로드
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
calc = mace_mp(model="medium", device=device, default_dtype="float32")

# 결과 저장
results = []

conf_dir = Path("conformers")
out_dir = Path("optimized")
out_dir.mkdir(exist_ok=True)

for xyz_file in sorted(conf_dir.glob("conf_*.xyz")):
    print(f"\nOptimizing: {xyz_file.name}")
    
    atoms = read(xyz_file)
    atoms.calc = calc
    
    initial_e = atoms.get_potential_energy()
    
    opt = BFGS(atoms, logfile=None)
    opt.run(fmax=0.05, steps=100)
    
    final_e = atoms.get_potential_energy()
    
    # 저장
    out_path = out_dir / f"{xyz_file.stem}_opt.xyz"
    write(out_path, atoms)
    
    results.append({
        'name': xyz_file.stem,
        'initial_e': initial_e,
        'final_e': final_e,
        'steps': opt.nsteps
    })
    
    print(f"  Initial: {initial_e:.4f} eV → Final: {final_e:.4f} eV ({opt.nsteps} steps)")

# 에너지 순으로 정렬
print("\n" + "="*50)
print("Results sorted by energy:")
print("="*50)
results.sort(key=lambda x: x['final_e'])
for i, r in enumerate(results):
    rel_e = (r['final_e'] - results[0]['final_e']) * 1000  # meV
    print(f"{i+1}. {r['name']}: {r['final_e']:.4f} eV (Δ = {rel_e:.1f} meV)")

print(f"\nLowest energy conformer: {results[0]['name']}")
PYEOF

echo ""
echo "=========================================="
echo "[3] Results:"
echo "Optimized conformers:"
ls -la optimized/
echo "=========================================="
