#!/bin/bash
# ============================================
# DockOnSurf + MACE (가짜 SLURM 사용)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/dockonsurf_slurm"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "DockOnSurf + MACE (Fake SLURM)"
echo "Date: $(date)"
echo "=========================================="

# 가짜 sbatch를 PATH에 추가
export PATH="${SCRIPT_DIR}/bin:$PATH"
chmod +x "${SCRIPT_DIR}/bin/sbatch"

echo "Using fake sbatch: $(which sbatch)"

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
num_conformers = 3
pre_opt = MMFF
EOF

echo ""
echo "Input files:"
ls -la
echo ""
echo "=== dockonsurf.inp ==="
cat dockonsurf.inp
echo ""

# DockOnSurf 실행
echo ""
echo "Running DockOnSurf..."
python "$HOME/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/dockonsurf.py" -i dockonsurf.inp 2>&1

echo ""
echo "=========================================="
echo "Results:"
ls -la
echo ""
if [ -f dockonsurf.log ]; then
    echo "=== dockonsurf.log ==="
    cat dockonsurf.log
fi
echo "=========================================="
