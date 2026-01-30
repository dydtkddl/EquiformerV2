"""
Test Coverage Analysis Module
"""

import pytest
import numpy as np
from ase import Atoms
from ase.build import fcc111

from surfscreen.analysis.coverage import CoverageAnalyzer, CoverageResult, calculate_coverage


@pytest.fixture
def surface_with_adsorbate():
    """표면 + 흡착 분자 테스트 구조"""
    # Cu(111) 3x3 표면
    surface = fcc111('Cu', size=(3, 3, 4), vacuum=15.0)
    n_surface = len(surface)
    
    # 물 분자 추가
    water_pos = surface.get_positions().mean(axis=0) + [0, 0, 5]
    water = Atoms('OH2', positions=[
        water_pos,
        water_pos + [0.96, 0, 0],
        water_pos + [-0.24, 0.93, 0]
    ])
    
    combined = surface + water
    return combined, n_surface


def test_coverage_analyzer_creation(surface_with_adsorbate):
    """CoverageAnalyzer 생성 테스트"""
    atoms, n_surface = surface_with_adsorbate
    analyzer = CoverageAnalyzer(atoms, n_surface)
    
    assert analyzer.n_surface == n_surface


def test_surface_area_calculation(surface_with_adsorbate):
    """표면적 계산 테스트"""
    atoms, n_surface = surface_with_adsorbate
    analyzer = CoverageAnalyzer(atoms, n_surface)
    
    area = analyzer.calculate_surface_area()
    
    assert area > 0
    # Cu(111) 3x3 표면적 ~ 50-60 Å²
    assert 40 < area < 80


def test_coverage_calculation(surface_with_adsorbate):
    """피복도 계산 테스트"""
    atoms, n_surface = surface_with_adsorbate
    analyzer = CoverageAnalyzer(atoms, n_surface)
    
    result = analyzer.calculate_coverage(molecular_area=10.0)
    
    assert isinstance(result, CoverageResult)
    assert result.n_adsorbates == 3  # O + H + H
    assert result.surface_area > 0
    assert 0 <= result.coverage_ml <= 10  # 합리적인 범위


def test_coverage_result_fields():
    """CoverageResult 필드 테스트"""
    result = CoverageResult(
        surface_area=100.0,
        n_adsorbates=5,
        molecular_area=10.0,
        coverage_abs=0.05,
        coverage_ml=0.5
    )
    
    assert result.surface_area == 100.0
    assert result.n_adsorbates == 5
    assert result.coverage_ml == 0.5


def test_calculate_coverage_convenience():
    """편의 함수 테스트"""
    surface = fcc111('Cu', size=(2, 2, 3), vacuum=10.0)
    n_surface = len(surface)
    
    # 분자 추가
    mol = Atoms('CO', positions=[[5, 5, 15], [5, 5, 16.1]])
    atoms = surface + mol
    
    result = calculate_coverage(atoms, n_surface, molecular_area=5.0)
    
    assert "surface_area_A2" in result
    assert "coverage_ML" in result
    assert result["n_adsorbates"] == 2


def test_auto_detect_surface():
    """표면 원자 자동 감지 테스트"""
    surface = fcc111('Cu', size=(2, 2, 3), vacuum=10.0)
    mol = Atoms('O', positions=[[5, 5, 20]])
    atoms = surface + mol
    
    analyzer = CoverageAnalyzer(atoms, n_surface_atoms=0)  # 자동 감지
    
    # 자동 감지된 표면 원자 수가 합리적인지
    assert analyzer.n_surface > 0
