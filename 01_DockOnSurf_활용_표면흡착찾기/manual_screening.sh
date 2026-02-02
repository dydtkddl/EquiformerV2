#!/bin/bash
# ============================================
# 수동 Screening 파이프라인
# DockOnSurf의 로그 형식 이슈를 우회
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/manual_screening"
SURFACE="${SCRIPT_DIR}/structures/surfaces/cu111_small.xyz"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"

echo "=========================================="
echo "Manual Screening Pipeline"
echo "Surface: Cu(111)"
echo "Molecule: Methanol"
echo "Date: $(date)"
echo "=========================================="

# 작업 디렉토리 준비
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 파일 복사
cp "$SURFACE" ./surface.xyz
cp "$MOLECULE" ./molecule.xyz

# ============================================
# Step 1: 표면에 분자 배치 및 MACE 최적화
# ============================================
echo ""
echo "============================================"
echo "Surface Adsorption Screening with MACE"
echo "============================================"

python -u << 'PYEOF'
import os
import numpy as np
import torch
from ase.io import read, write
from ase.optimize import BFGS
from ase.build import add_adsorbate
from ase.constraints import FixAtoms
from mace.calculators import mace_mp

# Device 설정
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

# MACE 모델 로드
calc = mace_mp(model="medium", device=device, default_dtype="float32")

# 표면 및 분자 읽기
surface = read("surface.xyz")
molecule = read("molecule.xyz")

print(f"Surface: {len(surface)} atoms ({surface.get_chemical_formula()})")
print(f"Molecule: {len(molecule)} atoms ({molecule.get_chemical_formula()})")

# 표면의 최상층 Cu 원자 위치 (z 좌표 기준)
z_coords = surface.positions[:, 2]
top_z = z_coords.max()
top_atoms = [i for i, z in enumerate(z_coords) if abs(z - top_z) < 0.1]
print(f"Top layer atoms: {top_atoms}")

# Cell 설정 (10x10x25 Å)
cell = [[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 25.0]]
surface.set_cell(cell)
surface.set_pbc([True, True, False])

# 분자 중심 @ O 원자 (인덱스 1)
mol_center = molecule.positions[1]  # O atom
molecule.positions -= mol_center  # 원점으로 이동

# 여러 흡착 사이트 테스트
results = []
os.makedirs("structures", exist_ok=True)

# 흡착 높이 설정
ads_height = 2.0  # Å

for site_idx, atom_idx in enumerate(top_atoms[:3]):  # 상위 3개 사이트
    site_pos = surface.positions[atom_idx][:2]  # x, y 좌표
    
    # 여러 회전 각도 테스트
    for angle_idx, angle in enumerate([0, 45, 90, 135]):
        config_name = f"site{site_idx}_rot{angle}"
        print(f"\n=== {config_name} ===")
        print(f"  Site: ({site_pos[0]:.2f}, {site_pos[1]:.2f})")
        print(f"  Rotation: {angle}°")
        
        # 시스템 복사
        system = surface.copy()
        mol_copy = molecule.copy()
        
        # 분자 회전 (z축 기준)
        angle_rad = np.radians(angle)
        rot_matrix = np.array([
            [np.cos(angle_rad), -np.sin(angle_rad), 0],
            [np.sin(angle_rad),  np.cos(angle_rad), 0],
            [0, 0, 1]
        ])
        mol_copy.positions = mol_copy.positions @ rot_matrix.T
        
        # 분자 위치 설정 (표면 위)
        mol_copy.positions[:, 0] += site_pos[0]
        mol_copy.positions[:, 1] += site_pos[1]
        mol_copy.positions[:, 2] += top_z + ads_height
        
        # 시스템에 분자 추가
        system += mol_copy
        system.set_cell(cell)
        system.set_pbc([True, True, False])
        
        # 표면 원자 고정
        constraint = FixAtoms(indices=list(range(len(surface))))
        system.set_constraint(constraint)
        
        # MACE 계산기 설정
        system.calc = calc
        
        try:
            # 초기 에너지
            initial_e = system.get_potential_energy()
            print(f"  Initial E: {initial_e:.4f} eV")
            
            # 최적화
            opt = BFGS(system, logfile=f"structures/{config_name}_opt.log")
            opt.run(fmax=0.05, steps=100)
            
            final_e = system.get_potential_energy()
            print(f"  Final E: {final_e:.4f} eV ({opt.nsteps} steps)")
            
            # 흡착 에너지 계산
            # E_ads = E_system - E_surface - E_molecule
            surface.calc = calc
            mol_copy_isolated = molecule.copy()
            mol_copy_isolated.calc = calc
            
            e_surface = surface.get_potential_energy()
            e_molecule = mol_copy_isolated.get_potential_energy()
            e_ads = final_e - e_surface - e_molecule
            
            print(f"  E_ads: {e_ads:.4f} eV")
            
            # 결과 저장 (먼저)
            results.append({
                'name': config_name,
                'site_idx': site_idx,
                'angle': angle,
                'energy': final_e,
                'e_ads': e_ads,
                'steps': opt.nsteps
            })
            
            # 구조 저장 (constraint 제거)
            try:
                system.set_constraint()  # constraint 제거
                output_file = f"structures/{config_name}.xyz"
                write(output_file, system)
            except Exception as write_err:
                print(f"  Write warning: {write_err}")
            
        except Exception as e:
            print(f"  Error: {e}")

# 결과 정렬 및 출력
if results:
    results.sort(key=lambda x: x['e_ads'])
    
    print("\n" + "="*60)
    print("RESULTS: Sorted by Adsorption Energy")
    print("="*60)
    for i, r in enumerate(results):
        print(f"{i+1:2d}. {r['name']:15s} E_ads = {r['e_ads']:8.4f} eV")
    
    print(f"\n✅ Most stable: {results[0]['name']} (E_ads = {results[0]['e_ads']:.4f} eV)")
    
    # 결과 CSV 저장
    with open("results.csv", "w") as f:
        f.write("name,site_idx,angle,energy,e_ads,steps\n")
        for r in results:
            f.write(f"{r['name']},{r['site_idx']},{r['angle']},{r['energy']:.6f},{r['e_ads']:.6f},{r['steps']}\n")
    print("\n📊 Results saved to: results.csv")
else:
    print("\n❌ No configurations were successfully optimized")
PYEOF

echo ""
echo "=========================================="
echo "Results:"
ls -la
if [ -d "structures" ]; then
    echo ""
    echo "=== Generated Structures ==="
    ls -la structures/
fi
if [ -f "results.csv" ]; then
    echo ""
    echo "=== Results CSV ==="
    cat results.csv
fi
echo "=========================================="
