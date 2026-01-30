#!/bin/bash
# ============================================================
# SurfScreen Example Test Suite - README
# ============================================================
# 
# 이 폴더는 SurfScreen의 모든 기능을 테스트하기 위한 예제 스크립트를 포함합니다.
#
# 사용법:
#   1. 전체 테스트: bash run_all_tests.sh
#   2. 개별 테스트: bash 01_molecule_from_pubchem.sh
#
# 카테고리:
#   01-05: Molecule 관련 (PubChem, SMILES, Conformer, 분석)
#   06-08: Surface 관련 (생성, 사이트 감지)
#   09-11: Adsorption 관련 (구성 생성, 시각화)
#   12-14: MD 관련 (실행, 리포트, 계속)
#   15-17: Analysis 관련 (MSD, RDF, Boltzmann)
#   18-20: Screen 관련 (스크리닝, 리포트)
#
# 필수 환경:
#   - surfscreen 설치: pip install -e .
#   - MACE: pip install mace-torch
#   - xTB (선택): pip install xtb (분자 계산용)
#
# ============================================================

echo "SurfScreen Example Test Suite"
echo "============================="
echo ""
echo "Available tests:"
ls -1 *.sh | grep -v run_all | grep -v README

