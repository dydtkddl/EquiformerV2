#!/bin/bash
# ============================================
# DockOnSurf + MACE 통합 테스트
# Isolated 단계 테스트
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/dockonsurf_test"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"
MACE_MODEL="$HOME/.cache/mace/20231203mace128L1_epoch199model"

echo "=========================================="
echo "DockOnSurf + MACE Integration Test"
echo "Date: $(date)"
echo "=========================================="

# 작업 디렉토리 준비
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 분자 파일 복사
cp "$MOLECULE" ./molecule.xyz

# MACE 입력 파일 생성
cat > mace_input.yaml << 'EOF'
optimizer: BFGS
fmax: 0.05
max_steps: 60
EOF

# DockOnSurf 입력 파일 생성 (Isolated)
cat > dockonsurf_isolated.inp << EOF
[Global]
project_name = mace_test
run_type = isolated
code = mace
model_mace = ${MACE_MODEL}

[Isolated]
isol_inp_file = mace_input.yaml
molec_file = molecule.xyz
num_conformers = 5
pre_opt = MMFF
EOF

echo ""
echo "Working directory: $WORK_DIR"
echo "Input files created:"
ls -la

# DockOnSurf 실행
echo ""
echo "Running DockOnSurf (Isolated)..."
echo "Command: dockonsurf.py dockonsurf_isolated.inp"
echo ""

dockonsurf.py dockonsurf_isolated.inp

echo ""
echo "=========================================="
echo "Test completed!"
echo "Results:"
ls -la
echo "=========================================="
