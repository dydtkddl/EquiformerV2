#!/bin/bash
# ============================================
# DockOnSurf Screening 테스트
# 표면 + 분자 흡착 사이트 탐색
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/screening_test"
SURFACE="${SCRIPT_DIR}/structures/surfaces/cu111_small.xyz"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "DockOnSurf Screening Test"
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

# DockOnSurf Screening 입력
cat > dockonsurf.inp << EOF
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
set_angles = auto
sites = top, bridge, hollow
max_structures = 20
distance = 2.0
num_conformers = 10
pre_opt = MMFF
EOF

echo ""
echo "=== dockonsurf.inp ==="
cat dockonsurf.inp
echo ""

# DockOnSurf 실행
echo ""
echo "Running DockOnSurf Screening..."
python -u << 'PYEOF'
import sys
import os
import traceback

dos_path = os.path.expanduser("~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf")
sys.path.insert(0, dos_path)
sys.path.insert(0, os.path.join(dos_path, "src"))

try:
    from dockonsurf import dos_input, screening
    
    print("Reading input file...")
    inp_vars = dos_input.read_input("dockonsurf.inp")
    print(f"run_type: {inp_vars.get('run_type')}")
    print(f"sites: {inp_vars.get('sites')}")
    print(f"max_structures: {inp_vars.get('max_structures')}")
    
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
echo "Results:"
ls -la
if [ -d "screening" ]; then
    echo ""
    echo "=== Screening Results ==="
    find screening -type f -name "*.xyz" -o -name "*.gen" | head -20
fi
echo "=========================================="
