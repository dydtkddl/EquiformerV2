#!/bin/bash
# ============================================
# CP2K Podman 통합 테스트
# DockOnSurf + CP2K (Podman 컨테이너)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work/cp2k_test"
MOLECULE="${SCRIPT_DIR}/structures/molecules/methanol.xyz"

echo "=========================================="
echo "CP2K Podman Integration Test"
echo "Date: $(date)"
echo "=========================================="

# CP2K Podman 컨테이너 확인
echo ""
echo "[1] Checking CP2K container..."
if command -v podman &> /dev/null; then
    echo "Podman: Found"
    podman images | grep -i cp2k || echo "No CP2K image found"
else
    echo "Podman: NOT FOUND"
fi

# 기존 run_cp2k.sh 확인
echo ""
echo "[2] Checking existing CP2K runner..."
if [ -f ~/run_cp2k.sh ]; then
    echo "Found: ~/run_cp2k.sh"
    echo "=== run_cp2k.sh content ==="
    head -30 ~/run_cp2k.sh
else
    echo "~/run_cp2k.sh not found"
fi

# CP2K 데이터 디렉토리 확인
echo ""
echo "[3] Checking CP2K data..."
if [ -d ~/cp2k/data ]; then
    echo "Found: ~/cp2k/data"
    ls ~/cp2k/data | head -10
else
    echo "~/cp2k/data not found"
fi

# 작업 디렉토리 준비
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 분자 파일 복사
cp "$MOLECULE" ./coord.xyz

# CP2K 입력 파일 생성
cat > cp2k.inp << 'EOF'
&GLOBAL
  PROJECT methanol_opt
  RUN_TYPE GEO_OPT
  PRINT_LEVEL MEDIUM
&END GLOBAL

&MOTION
  &GEO_OPT
    OPTIMIZER BFGS
    MAX_ITER 50
    MAX_DR 0.003
    MAX_FORCE 0.00045
  &END GEO_OPT
&END MOTION

&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    CHARGE 0
    &QS
      EPS_DEFAULT 1.0E-12
    &END QS
    &MGRID
      CUTOFF 300
      NGRIDS 4
    &END MGRID
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
      &VDW_POTENTIAL
        DISPERSION_FUNCTIONAL PAIR_POTENTIAL
        &PAIR_POTENTIAL
          TYPE DFTD3
          PARAMETER_FILE_NAME dftd3.dat
          REFERENCE_FUNCTIONAL PBE
        &END PAIR_POTENTIAL
      &END VDW_POTENTIAL
    &END XC
    &SCF
      EPS_SCF 1.0E-6
      MAX_SCF 50
      SCF_GUESS ATOMIC
      &OT
        MINIMIZER DIIS
        PRECONDITIONER FULL_SINGLE_INVERSE
      &END OT
    &END SCF
  &END DFT
  &SUBSYS
    &CELL
      ABC 15.0 15.0 15.0
      PERIODIC NONE
    &END CELL
    &TOPOLOGY
      COORD_FILE_FORMAT XYZ
      COORD_FILE_NAME coord.xyz
    &END TOPOLOGY
    &KIND C
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q4
    &END KIND
    &KIND H
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q1
    &END KIND
    &KIND O
      BASIS_SET DZVP-MOLOPT-SR-GTH
      POTENTIAL GTH-PBE-q6
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
EOF

echo ""
echo "[4] CP2K input file created:"
ls -la

echo ""
echo "[5] Testing CP2K execution..."
if [ -f ~/run_cp2k.sh ]; then
    echo "Running: ~/run_cp2k.sh cp2k.inp"
    # CP2K 실행 (타임아웃 5분)
    timeout 300 ~/run_cp2k.sh cp2k.inp 2>&1 || {
        echo "CP2K execution failed or timed out"
    }
else
    echo "Skipping CP2K execution (no runner script)"
fi

echo ""
echo "=========================================="
echo "Results:"
ls -la
if [ -f "methanol_opt.out" ]; then
    echo ""
    echo "=== CP2K Output (last 30 lines) ==="
    tail -30 methanol_opt.out
fi
echo "=========================================="
