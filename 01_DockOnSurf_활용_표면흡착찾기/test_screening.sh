#!/bin/bash
# ============================================
# DockOnSurf Screening 테스트 (2단계 워크플로우)
# Step 1: Isolated → conformers 생성
# Step 2: Screening → 표면에 배치
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/screening_test"
SURFACE="${SCRIPT_DIR}/structures/surfaces/cu111_small.xyz"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "DockOnSurf Screening Test (2-Step)"
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
# Step 1: Isolated (Conformer 생성)
# ============================================
echo ""
echo "============================================"
echo "Step 1: Running Isolated Mode (Conformers)"
echo "============================================"

cat > dockonsurf_isolated.inp << EOF
[Global]
project_name = cu111_methanol
run_type = isolated
code = mace
model_mace = ${MACE_MODEL}
batch_q_sys = slurm
subm_script = sub_mace.sh
pbc_cell = False

[Isolated]
isol_inp_file = mace_input.yaml
molec_file = molecule.xyz
num_conformers = 10
pre_opt = MMFF
EOF

echo "=== dockonsurf_isolated.inp ==="
cat dockonsurf_isolated.inp
echo ""

python -u << 'PYEOF'
import sys
import os
import traceback

dos_path = os.path.expanduser("~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf")
sys.path.insert(0, dos_path)
sys.path.insert(0, os.path.join(dos_path, "src"))

try:
    from dockonsurf import dos_input, isolated
    
    print("Reading isolated input file...")
    inp_vars = dos_input.read_input("dockonsurf_isolated.inp")
    print(f"run_type: {inp_vars.get('run_type')}")
    print(f"num_conformers: {inp_vars.get('num_conformers')}")
    
    print("\nRunning isolated stage...")
    isolated.run_isolated(inp_vars)
    print("Isolated stage completed!")
    
except Exception as e:
    print(f"\n=== ERROR ===")
    print(f"Type: {type(e).__name__}")
    print(f"Message: {e}")
    print("\n=== TRACEBACK ===")
    traceback.print_exc()
    sys.exit(1)
PYEOF

echo ""
echo "Isolated results:"
ls -la
if [ -d "isolated" ]; then
    echo "Conformers generated: $(find isolated -name "*.gen" -o -name "*.xyz" | wc -l)"
fi

# ============================================
# Step 2: Screening (표면 흡착)
# ============================================
echo ""
echo "============================================"
echo "Step 2: Running Screening Mode (Adsorption)"
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
echo "Final Results:"
ls -la
if [ -d "screening" ]; then
    echo ""
    echo "=== Screening Results ==="
    find screening -type f -name "*.xyz" -o -name "*.gen" | head -20
fi
echo "=========================================="
