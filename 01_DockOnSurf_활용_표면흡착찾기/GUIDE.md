# DockOnSurf + MACE 통합 가이드

> SLURM 없는 환경에서 DockOnSurf를 MACE와 함께 사용하는 완전한 가이드

## 📋 목차

1. [환경 요구사항](#환경-요구사항)
2. [발견한 이슈 및 해결](#발견한-이슈-및-해결)
3. [완전한 설치 및 설정](#완전한-설치-및-설정)
4. [워크플로우 실행](#워크플로우-실행)
5. [트러블슈팅](#트러블슈팅)

---

## 환경 요구사항

### 필수 패키지

- Python 3.8+
- PyTorch (CUDA 지원)
- ASE (Atomic Simulation Environment)
- RDKit
- MACE-torch
- DockOnSurf

### 권장 버전

```
torch==1.13.1+cu117
ase>=3.22.0
rdkit>=2022.03
mace-torch>=0.3.14
```

---

## 발견한 이슈 및 해결

### 이슈 1: `batch_q_sys = local` 미구현

**증상**: DockOnSurf 실행 시 아무 출력 없이 종료

**원인**: `calculation.py`에서 `local` 모드가 구현되지 않음

```python
elif inp_vars['batch_q_sys'] == 'local':
    pass  # TODO: Implement local execution
```

**해결**: 가짜 SLURM 환경 구현

```bash
# bin/sbatch - 가짜 sbatch
#!/bin/bash
SCRIPT="$1"
echo "Submitted batch job $$"
bash "$SCRIPT"
```

```bash
# bin/squeue - 가짜 squeue
#!/bin/bash
echo "             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)"
# 빈 출력 = 대기 중인 작업 없음
```

---

### 이슈 2: HDBSCAN 클러스터링 오류

**증상**: `ValueError: Min cluster size must be greater than one`

**원인**: `num_conformers`가 너무 적음 (3개 미만)

**해결**: `num_conformers = 10` 이상 설정

```ini
[Isolated]
num_conformers = 10  # 최소 10개 권장
```

---

### 이슈 3: pbc_cell 형식 오류

**증상**: `ValueError: 'pbc_cell' must be either 3 vectors of size 3 or False`

**원인**: 잘못된 pbc_cell 형식 (`15.0, 15.0, 15.0`)

**해결**:

- Isolated 계산: `pbc_cell = False`
- Screening/표면 계산: 3x3 행렬 형식 사용

```ini
# Isolated (분자만)
pbc_cell = False

# Screening (표면 + 분자) - 괄호로 각 벡터 감싸기
pbc_cell = (10.0 0.0 0.0) (0.0 10.0 0.0) (0.0 0.0 25.0)
```

---

### 이슈 4: 분자 파일 형식 (.gen)

**증상**: XYZ 파일을 찾지 못함

**원인**: DockOnSurf가 `.gen` (DFTB+) 형식으로 저장

**해결**: ASE가 `.gen` 형식 지원

```python
from ase.io import read
atoms = read("struct_0.gen")  # .gen 형식 읽기 가능
```

---

## 완전한 설치 및 설정

### Step 1: MACE 설치

```bash
# 기존 환경에서 MACE 설치
conda activate equiformer_v2

# MACE 및 의존성 설치
pip install torch-ema torchmetrics configargparse matscipy orjson prettytable
pip install mace-torch --upgrade
```

### Step 2: 가짜 SLURM 환경 설정

```bash
# 디렉토리 생성
mkdir -p bin

# bin/sbatch 생성
cat > bin/sbatch << 'EOF'
#!/bin/bash
SCRIPT="$1"
JOB_ID=$$
echo "Submitted batch job $JOB_ID"
if [ -f "$SCRIPT" ]; then
    bash "$SCRIPT"
fi
EOF

# bin/squeue 생성
cat > bin/squeue << 'EOF'
#!/bin/bash
echo "             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)"
EOF

# 실행 권한
chmod +x bin/sbatch bin/squeue

# PATH에 추가
export PATH="$PWD/bin:$PATH"
```

### Step 3: DockOnSurf 입력 파일 작성

```ini
# dockonsurf.inp
[Global]
project_name = my_project
run_type = isolated
code = mace
model_mace = ~/.cache/mace/20231203mace128L1_epoch199model
batch_q_sys = slurm
subm_script = sub_mace.sh
pbc_cell = False

[Isolated]
isol_inp_file = mace_input.yaml
molec_file = molecule.xyz
num_conformers = 10
pre_opt = MMFF
```

### Step 4: MACE 설정 파일

```yaml
# mace_input.yaml
optimizer: BFGS
fmax: 0.05
max_steps: 100
```

---

## 워크플로우 실행

### 방법 1: 2단계 워크플로우 (권장)

```bash
# 1. DockOnSurf로 conformer 생성
python ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/dockonsurf.py -i dockonsurf.inp

# 2. MACE로 수동 최적화 (run_mace_on_conformers.sh 사용)
./run_mace_on_conformers.sh
```

### 방법 2: 통합 스크립트

```bash
./run_full_workflow.sh molecule.xyz
```

---

## 트러블슈팅

### Q: dockonsurf.log가 비어있음

**A**: Python traceback 확인

```bash
python -c "from dockonsurf import isolated; ..."
```

### Q: MACE 모델 로드 실패

**A**: 모델 경로 확인

```bash
ls -la ~/.cache/mace/
```

### Q: GPU 메모리 부족

**A**: float32 사용 (기본값)

```python
calc = mace_mp(model="medium", default_dtype="float32")
```

---

## 참고 자료

- [DockOnSurf 문서](https://dockonsurf.readthedocs.io/)
- [MACE GitHub](https://github.com/ACEsuit/mace)
- [ASE 문서](https://wiki.fysik.dtu.dk/ase/)
