#!/bin/bash
# ============================================
# DockOnSurf 상세 디버그
# Python traceback 포함
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/dockonsurf_debug"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "DockOnSurf Debug Mode"
echo "Date: $(date)"
echo "=========================================="

# 가짜 sbatch를 PATH에 추가
export PATH="${SCRIPT_DIR}/bin:$PATH"
chmod +x "${SCRIPT_DIR}/bin/sbatch"

# 작업 디렉토리 준비
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 파일 복사
cp "$MOLECULE" ./molecule.xyz
cp "${SCRIPT_DIR}/sub_mace.sh" ./

# MACE 입력 파일
cat > mace_input.yaml << 'EOF'
optimizer: BFGS
fmax: 0.05
max_steps: 100
EOF

# DockOnSurf 입력 파일
cat > dockonsurf.inp << EOF
[Global]
project_name = mace_test
run_type = isolated
code = mace
model_mace = ${MACE_MODEL}
batch_q_sys = slurm
subm_script = sub_mace.sh

[Isolated]
isol_inp_file = mace_input.yaml
molec_file = molecule.xyz
num_conformers = 10
pre_opt = MMFF
EOF

echo ""
echo "Running DockOnSurf with full Python traceback..."
echo ""

# Python 디버그 모드로 실행 (traceback 포함)
python -u << 'PYEOF'
import sys
import os
import traceback

# DockOnSurf 경로 추가
dos_path = os.path.expanduser("~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf")
sys.path.insert(0, dos_path)
sys.path.insert(0, os.path.join(dos_path, "src"))

try:
    print("Importing DockOnSurf modules...")
    from dockonsurf import dos_input, isolated
    print("Imports successful!")
    
    print("\nReading input file...")
    inp_vars = dos_input.read_input("dockonsurf.inp")
    print(f"Input variables: {list(inp_vars.keys())}")
    print(f"run_type: {inp_vars.get('run_type')}")
    print(f"code: {inp_vars.get('code')}")
    print(f"batch_q_sys: {inp_vars.get('batch_q_sys')}")
    print(f"molec_file: {inp_vars.get('molec_file')}")
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
PYEOF

echo ""
echo "=========================================="
echo "Results:"
ls -la
echo "=========================================="
