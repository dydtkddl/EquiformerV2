# SurfScreen

엔터프라이즈급 표면 흡착 스크리닝 플랫폼

## 설치

```bash
# 기본 설치
pip install -e .

# MACE 포함
pip install -e ".[mace]"

# 전체 설치
pip install -e ".[all]"
```

## 빠른 시작

### CLI 사용

```bash
# 분자 가져오기
surfscreen molecule from-smiles "CCO" --output ethanol.xyz
surfscreen molecule from-pubchem 2244 --output aspirin.xyz

# 표면 생성
surfscreen surface create Cu --miller 111 --layers 4 --supercell 3x3x1

# 스크리닝
surfscreen screen run --surface cu111.xyz --molecules "*.xyz" --engine mace
```

### Python API

```python
from surfscreen import MoleculeBuilder, SurfaceBuilder, Calculator

# 분자 생성
mol = MoleculeBuilder.from_smiles("CCO")

# 표면 생성
surface = SurfaceBuilder.from_element("Cu", miller_index=(1,1,1))

# 계산
calc = Calculator(engine="mace", device="cuda")
result = calc.optimize(mol)
```

## 문서

- [설계 문서](../SurfScreen_DESIGN.md)
