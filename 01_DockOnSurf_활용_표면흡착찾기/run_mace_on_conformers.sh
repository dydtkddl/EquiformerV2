#!/bin/bash
# ============================================
# DockOnSurf Conformer가 생성되었는지 확인 후
# 수동으로 MACE 최적화 실행
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/dockonsurf_debug/isolated"

echo "=========================================="
echo "Checking DockOnSurf Generated Conformers"
echo "=========================================="

if [ ! -d "$WORK_DIR" ]; then
    echo "Error: $WORK_DIR not found"
    echo "Run debug_dockonsurf.sh first"
    exit 1
fi

echo ""
echo "Conformer directories:"
ls -la "$WORK_DIR"

echo ""
echo "=== Conformer files ==="
for conf_dir in "$WORK_DIR"/conf_*; do
    if [ -d "$conf_dir" ]; then
        echo ""
        echo "--- $(basename $conf_dir) ---"
        ls -la "$conf_dir"
    fi
done

echo ""
echo "=========================================="
echo "Running MACE optimization on all conformers..."
echo "=========================================="

python << 'PYEOF'
import os
import sys
from pathlib import Path
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import mace_mp

# 경로 설정
work_dir = Path(os.environ.get('WORK_DIR', 'work/dockonsurf_debug/isolated'))

# MACE 모델 로드
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
calc = mace_mp(model="medium", device=device, default_dtype="float32")

results = []

# 각 conformer 디렉토리 순회
for conf_dir in sorted(work_dir.glob("conf_*")):
    print(f"\n=== Processing {conf_dir.name} ===")
    
    # XYZ 파일 찾기 (여러 가능한 이름)
    xyz_files = list(conf_dir.glob("*.xyz")) + list(conf_dir.glob("coord.*"))
    
    if not xyz_files:
        print(f"  No structure file found in {conf_dir}")
        continue
    
    input_file = xyz_files[0]
    print(f"  Input: {input_file.name}")
    
    try:
        atoms = read(str(input_file))
        atoms.calc = calc
        
        initial_e = atoms.get_potential_energy()
        print(f"  Initial energy: {initial_e:.4f} eV")
        
        # 최적화
        opt_log = conf_dir / "opt_log.out"
        opt = BFGS(atoms, logfile=str(opt_log))
        opt.run(fmax=0.05, steps=100)
        
        final_e = atoms.get_potential_energy()
        print(f"  Final energy: {final_e:.4f} eV ({opt.nsteps} steps)")
        
        # 저장
        output_file = conf_dir / "optimized_structure.xyz"
        write(str(output_file), atoms)
        
        results.append({
            'name': conf_dir.name,
            'energy': final_e,
            'steps': opt.nsteps
        })
        
    except Exception as e:
        print(f"  Error: {e}")

# 결과 정렬
if results:
    print("\n" + "="*50)
    print("Results sorted by energy:")
    print("="*50)
    results.sort(key=lambda x: x['energy'])
    for i, r in enumerate(results):
        rel_e = (r['energy'] - results[0]['energy']) * 1000  # meV
        print(f"{i+1}. {r['name']}: {r['energy']:.4f} eV (Δ = {rel_e:.1f} meV)")
    
    print(f"\n✅ Most stable: {results[0]['name']} ({results[0]['energy']:.4f} eV)")
else:
    print("\n❌ No conformers were optimized")
PYEOF

echo ""
echo "=========================================="
echo "Optimization completed!"
echo "=========================================="
