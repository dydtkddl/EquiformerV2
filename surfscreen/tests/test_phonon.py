"""
Test Phonon Analysis Module
"""

import pytest
import numpy as np
from ase import Atoms
from ase.build import molecule

from surfscreen.analysis.phonon import (
    PhononAnalyzer, 
    PhononResult, 
    ThermoResult,
    calculate_zpe,
    calculate_gibbs
)


@pytest.fixture
def water_molecule():
    """물 분자"""
    return molecule('H2O')


@pytest.fixture
def co_molecule():
    """CO 분자"""
    return molecule('CO')


class MockCalculator:
    """테스트용 모의 계산기"""
    def __init__(self, energy=-10.0):
        self.energy = energy
        
    def get_potential_energy(self, atoms=None):
        return self.energy
    
    def get_forces(self, atoms=None):
        n = len(atoms) if atoms else 3
        return np.zeros((n, 3))


def test_phonon_result_creation():
    """PhononResult 생성 테스트"""
    result = PhononResult(
        frequencies_cm1=np.array([1000, 2000, 3000]),
        frequencies_meV=np.array([124, 248, 372]),
        zpe=0.25,
        n_imaginary=0
    )
    
    assert len(result.frequencies_cm1) == 3
    assert result.zpe == 0.25
    assert result.has_imaginary == False


def test_phonon_result_imaginary():
    """허수 주파수 감지 테스트"""
    result = PhononResult(
        frequencies_cm1=np.array([1000, 2000]),
        frequencies_meV=np.array([124, 248]),
        zpe=0.15,
        n_imaginary=2
    )
    
    assert result.has_imaginary == True
    assert result.n_imaginary == 2


def test_thermo_result_creation():
    """ThermoResult 생성 테스트"""
    result = ThermoResult(
        temperature=300.0,
        pressure=1.0,
        E_pot=-10.0,
        ZPE=0.3,
        U_vib=0.5,
        S_vib=0.001,
        H=-9.5,
        G=-9.8
    )
    
    assert result.temperature == 300.0
    assert result.G == -9.8


def test_phonon_analyzer_creation(water_molecule):
    """PhononAnalyzer 생성 테스트"""
    calc = MockCalculator()
    analyzer = PhononAnalyzer(water_molecule, calc, delta=0.01)
    
    assert analyzer.delta == 0.01
    assert analyzer.atoms is not None


def test_phonon_thermodynamics_calculation():
    """열역학 계산 테스트 (모의 결과 사용)"""
    # 미리 계산된 PhononResult 사용
    phonon_result = PhononResult(
        frequencies_cm1=np.array([1500, 3000, 3500]),  # cm^-1
        frequencies_meV=np.array([186, 372, 434]),
        zpe=0.5,
        n_imaginary=0
    )
    
    water = molecule('H2O')
    water.calc = MockCalculator(energy=-10.0)
    
    analyzer = PhononAnalyzer(water)
    thermo = analyzer.calculate_thermodynamics(
        temperature=300.0,
        pressure=1.0,
        phonon_result=phonon_result
    )
    
    assert isinstance(thermo, ThermoResult)
    assert thermo.temperature == 300.0
    assert thermo.ZPE == 0.5
    # G < H (엔트로피 기여)
    assert thermo.G <= thermo.H


def test_thermo_temperature_dependence():
    """온도 의존성 테스트"""
    phonon_result = PhononResult(
        frequencies_cm1=np.array([1000, 2000]),
        frequencies_meV=np.array([124, 248]),
        zpe=0.2,
        n_imaginary=0
    )
    
    water = molecule('H2O')
    water.calc = MockCalculator()
    analyzer = PhononAnalyzer(water)
    
    thermo_low = analyzer.calculate_thermodynamics(100, phonon_result=phonon_result)
    thermo_high = analyzer.calculate_thermodynamics(500, phonon_result=phonon_result)
    
    # 높은 온도에서 엔트로피 기여가 더 큼 -> G가 더 낮음
    assert thermo_high.G < thermo_low.G


def test_convenience_functions_signature():
    """편의 함수 시그니처 테스트"""
    # 함수가 올바른 인자를 받는지 확인
    import inspect
    
    zpe_sig = inspect.signature(calculate_zpe)
    assert 'atoms' in zpe_sig.parameters
    assert 'calculator' in zpe_sig.parameters
    
    gibbs_sig = inspect.signature(calculate_gibbs)
    assert 'atoms' in gibbs_sig.parameters
    assert 'temperature' in gibbs_sig.parameters
