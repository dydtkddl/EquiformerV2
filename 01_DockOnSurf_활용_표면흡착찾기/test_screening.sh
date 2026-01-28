#!/bin/bash
# ============================================
# DockOnSurf Screening 테스트 (3단계 워크플로우)
# Step 1: Isolated → conformers 생성
# Step 2: MACE 최적화 (수동)
# Step 3: Screening → 표면에 배치
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/screening_test"
SURFACE="${SCRIPT_DIR}/structures/surfaces/cu111_small.xyz"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "DockOnSurf Screening Test (3-Step)"
echo "Surface: Cu(111)"
echo "Molecule: Methanol"
echo "Date: $(date)"
echo "=========================================="

# 가짜 SLURM PATH 추가
export PATH="${SCRIPT_DIR}/bin:$PATH"
chmod +x "${SCRIPT_DIR}/bin/"*

# 작업 디렉토리 준비
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 파일 복사
cp "$SURFACE" ./surface.xyz
cp "$MOLECULE" ./molecule.xyz
cp "${SCRIPT_DIR}/sub_mace.sh" ./

# MACE 설정
cat > mace_input.yaml << 'EOF'
optimizer: BFGS
fmax: 0.05
max_steps: 100
EOF

# ============================================
# Step 1: Isolated (Conformer 생성 전처리)
# ============================================
echo ""
echo "============================================"
echo "Step 1: Generating Conformers with RDKit"
echo "============================================"

python -u << 'PYEOF'
import os
import sys
from rdkit import Chem
from rdkit.Chem import AllChem

# 메탄올 SMILES로부터 conformers 생성
mol = Chem.MolFromSmiles("CO")
mol = Chem.AddHs(mol)

# 여러 conformers 생성
AllChem.EmbedMultipleConfs(mol, numConfs=10, randomSeed=42)
AllChem.MMFFOptimizeMoleculeConfs(mol)

# isolated 디렉토리 생성
os.makedirs("isolated", exist_ok=True)

for i, conf in enumerate(mol.GetConformers()):
    conf_dir = f"isolated/conf_{i}"
    os.makedirs(conf_dir, exist_ok=True)
    
    # XYZ 파일로 저장
    xyz_file = f"{conf_dir}/struct_{i}.xyz"
    with open(xyz_file, 'w') as f:
        f.write(f"{mol.GetNumAtoms()}\n")
        f.write(f"Conformer {i}\n")
        for atom in mol.GetAtoms():
            pos = conf.GetAtomPosition(atom.GetIdx())
            f.write(f"{atom.GetSymbol()} {pos.x:.6f} {pos.y:.6f} {pos.z:.6f}\n")
    
    print(f"Created: {xyz_file}")

print(f"\nTotal conformers: {mol.GetNumConformers()}")
PYEOF

echo ""
echo "Conformers generated:"
ls -la isolated/

# ============================================
# Step 2: MACE 최적화 (수동)
# ============================================
echo ""
echo "============================================"
echo "Step 2: MACE Optimization on Conformers"
echo "============================================"

python -u << 'PYEOF'
import os
import sys
from pathlib import Path
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import mace_mp

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

calc = mace_mp(model="medium", device=device, default_dtype="float32")

results = []
isolated_dir = Path("isolated")

for conf_dir in sorted(isolated_dir.glob("conf_*")):
    xyz_files = list(conf_dir.glob("*.xyz"))
    if not xyz_files:
        continue
    
    input_file = xyz_files[0]
    print(f"\n=== {conf_dir.name} ===")
    
    try:
        atoms = read(str(input_file))
        atoms.calc = calc
        
        initial_e = atoms.get_potential_energy()
        
        # 최적화
        opt_log = conf_dir / "opt_log.out"
        opt = BFGS(atoms, logfile=str(opt_log))
        opt.run(fmax=0.05, steps=50)
        
        final_e = atoms.get_potential_energy()
        print(f"  {initial_e:.4f} → {final_e:.4f} eV ({opt.nsteps} steps)")
        
        # 최적화된 구조 저장
        output_file = conf_dir / "optimized.xyz"
        write(str(output_file), atoms)
        
        # 에너지 정보 저장 (.info에 저장)
        atoms.info['energy'] = final_e
        write(str(conf_dir / f"struct_0.gen"), atoms, format='gen')
        
        results.append({'name': conf_dir.name, 'energy': final_e, 'steps': opt.nsteps})
        
    except Exception as e:
        print(f"  Error: {e}")

# 결과 정렬 및 출력
if results:
    results.sort(key=lambda x: x['energy'])
    print("\n" + "="*50)
    print("Results (sorted by energy):")
    for i, r in enumerate(results):
        rel_e = (r['energy'] - results[0]['energy']) * 1000
        print(f"  {i+1}. {r['name']}: {r['energy']:.4f} eV (Δ = {rel_e:.1f} meV)")
    print(f"\n✅ Most stable: {results[0]['name']}")
PYEOF

# ============================================
# Step 3: Screening (표면 흡착)
# ============================================
echo ""
echo "============================================"
echo "Step 3: Running Screening Mode (Adsorption)"
echo "============================================"

cat > dockonsurf_screening.inp << EOF
[Global]
project_name = cu111_methanol
run_type = screening
code = mace
model_mace = ${MACE_MODEL}
batch_q_sys = slurm
subm_script = sub_mace.sh
pbc_cell = (10.0 0.0 0.0) (0.0 10.0 0.0) (0.0 0.0 25.0)

[Screening]
screen_inp_file = mace_input.yaml
molec_file = molecule.xyz
surf_file = surface.xyz
set_angles = euler
sites = 1 2 3
max_structures = 20
distance = 2.0
molec_ctrs = 2
EOF

echo "=== dockonsurf_screening.inp ==="
cat dockonsurf_screening.inp
echo ""

python -u << 'PYEOF'
import sys
import os
import traceback

dos_path = os.path.expanduser("~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf")
sys.path.insert(0, dos_path)
sys.path.insert(0, os.path.join(dos_path, "src"))

try:
    from dockonsurf import dos_input, screening
    
    print("Reading screening input file...")
    inp_vars = dos_input.read_input("dockonsurf_screening.inp")
    print(f"run_type: {inp_vars.get('run_type')}")
    print(f"sites: {inp_vars.get('sites')}")
    
    print("\nRunning screening stage...")
    screening.run_screening(inp_vars)
    print("Screening completed!")
    
except Exception as e:
    print(f"\n=== ERROR ===")
    print(f"Type: {type(e).__name__}")
    print(f"Message: {e}")
    print("\n=== TRACEBACK ===")
    traceback.print_exc()
PYEOF

echo ""
echo "=========================================="
echo "Final Results:"
ls -la
if [ -d "screening" ]; then
    echo ""
    echo "=== Screening Results ==="
    find screening -type f \( -name "*.xyz" -o -name "*.gen" \) | head -20
fi
if [ -d "isolated" ]; then
    echo ""
    echo "=== Isolated Conformers ==="
    find isolated -type f -name "optimized.xyz" | head -10
fi
echo "=========================================="
