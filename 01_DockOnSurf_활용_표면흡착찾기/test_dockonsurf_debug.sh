#!/bin/bash
# ============================================
# DockOnSurf + MACE 통합 테스트 (디버그 버전)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/dockonsurf_test2"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"
DOS_EXAMPLE="$HOME/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/examples/mace/isolated"

echo "=========================================="
echo "DockOnSurf + MACE Integration Test"
echo "Date: $(date)"
echo "=========================================="

# 작업 디렉토리 준비
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# DockOnSurf 예제 파일 확인
echo ""
echo "[1] Checking DockOnSurf MACE example..."
if [ -f "$DOS_EXAMPLE/dockonsurf_isolated_mace.inp" ]; then
    echo "Found example at: $DOS_EXAMPLE"
    echo "=== Example Input File ==="
    cat "$DOS_EXAMPLE/dockonsurf_isolated_mace.inp"
    echo ""
    echo "=== Example mace_input.yaml ==="
    cat "$DOS_EXAMPLE/mace_input.yaml"
    echo ""
else
    echo "Example not found at: $DOS_EXAMPLE"
fi

# 분자 파일 복사
echo ""
echo "[2] Copying molecule file..."
cp "$MOLECULE" ./molecule.xyz

# MACE 입력 파일 생성 (예제 참고)
cat > mace_input.yaml << 'EOF'
optimizer: BFGS
fmax: 0.05
max_steps: 60
EOF

# DockOnSurf 입력 파일 생성
cat > dockonsurf_isolated.inp << EOF
[Global]
project_name = mace_test
run_type = isolated
code = mace
model_mace = ${MACE_MODEL}
batch_q_sys = local
pbc_cell = False

[Isolated]
isol_inp_file = mace_input.yaml
molec_file = molecule.xyz
num_conformers = 3
pre_opt = MMFF
EOF

echo ""
echo "[3] Input files created:"
ls -la
echo ""
echo "=== dockonsurf_isolated.inp ==="
cat dockonsurf_isolated.inp
echo ""

# DockOnSurf 실행 (stderr도 캡처)
echo ""
echo "[4] Running DockOnSurf..."
echo "Command: python $HOME/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/dockonsurf.py -i dockonsurf_isolated.inp"
echo ""

python "$HOME/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/dockonsurf.py" -i dockonsurf_isolated.inp 2>&1 || {
    echo ""
    echo "=== DockOnSurf Error ==="
    echo "Exit code: $?"
    if [ -f dockonsurf.log ]; then
        echo "=== dockonsurf.log ==="
        cat dockonsurf.log
    fi
    exit 1
}

echo ""
echo "=========================================="
echo "[5] Test completed! Results:"
ls -la
if [ -f dockonsurf.log ]; then
    echo ""
    echo "=== dockonsurf.log ==="
    cat dockonsurf.log
fi
echo "=========================================="
