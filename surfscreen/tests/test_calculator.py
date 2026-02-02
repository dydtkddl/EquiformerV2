"""
Test Calculator Module

CalculatorFactory와 개별 계산기 테스트
"""

import pytest
import numpy as np


class TestCalculatorFactoryImport:
    """CalculatorFactory import 테스트"""
    
    def test_import_calculator_factory(self):
        """CalculatorFactory가 import 가능한지"""
        try:
            from surfscreen.calculator import CalculatorFactory
            assert CalculatorFactory is not None
        except ImportError as e:
            pytest.skip(f"CalculatorFactory not available: {e}")


class TestCalculatorFactory:
    """CalculatorFactory 테스트"""
    
    def test_available_engines_list(self):
        """사용 가능한 엔진 목록 확인"""
        try:
            from surfscreen.calculator import CalculatorFactory
        except ImportError:
            pytest.skip("CalculatorFactory not available")
        
        available = CalculatorFactory.available()
        
        # 최소한 EMT는 항상 사용 가능
        assert 'emt' in [e.lower() for e in available] or len(available) > 0
    
    def test_create_emt_calculator(self):
        """EMT 계산기 생성"""
        try:
            from surfscreen.calculator import CalculatorFactory
        except ImportError:
            pytest.skip("CalculatorFactory not available")
        
        try:
            calc = CalculatorFactory.create('emt')
            assert calc is not None
        except ValueError:
            pytest.skip("EMT not available")
    
    def test_create_invalid_engine_raises(self):
        """존재하지 않는 엔진은 에러 발생"""
        try:
            from surfscreen.calculator import CalculatorFactory
        except ImportError:
            pytest.skip("CalculatorFactory not available")
        
        with pytest.raises((ValueError, KeyError)):
            CalculatorFactory.create('nonexistent_engine')


@pytest.mark.requires_ase
class TestEMTCalculator:
    """EMT 계산기 테스트"""
    
    def test_emt_energy_calculation(self, cu_cluster):
        """EMT 에너지 계산"""
        try:
            from ase.calculators.emt import EMT
        except ImportError:
            pytest.skip("ASE not available")
        
        cu_cluster.calc = EMT()
        energy = cu_cluster.get_potential_energy()
        
        # 에너지는 실수
        assert isinstance(energy, float)
        # Cu 클러스터 에너지는 음수
        assert energy < 0
    
    def test_emt_force_calculation(self, cu_cluster):
        """EMT 힘 계산"""
        try:
            from ase.calculators.emt import EMT
        except ImportError:
            pytest.skip("ASE not available")
        
        cu_cluster.calc = EMT()
        forces = cu_cluster.get_forces()
        
        # 힘 배열 크기 확인
        assert forces.shape == (len(cu_cluster), 3)
    
    def test_emt_optimization(self, cu_cluster):
        """EMT 최적화"""
        try:
            from ase.calculators.emt import EMT
            from ase.optimize import BFGS
        except ImportError:
            pytest.skip("ASE not available")
        
        cu_cluster.calc = EMT()
        initial_energy = cu_cluster.get_potential_energy()
        
        # 최적화
        opt = BFGS(cu_cluster, logfile=None)
        opt.run(fmax=0.1, steps=50)
        
        final_energy = cu_cluster.get_potential_energy()
        
        # 최적화 후 에너지가 감소하거나 같음
        assert final_energy <= initial_energy + 0.01  # 허용 오차


class TestCalculatorResult:
    """계산 결과 구조 테스트"""
    
    def test_optimization_result_structure(self, mock_calculator, h2o_atoms):
        """최적화 결과 구조 확인"""
        result = mock_calculator.optimize(h2o_atoms)
        
        # 필수 속성 확인
        assert hasattr(result, 'atoms')
        assert hasattr(result, 'final_energy')
        assert hasattr(result, 'steps')
        assert hasattr(result, 'converged')
    
    def test_energy_result_is_float(self, mock_calculator, h2o_atoms):
        """에너지는 float 타입"""
        energy = mock_calculator.get_energy(h2o_atoms)
        
        assert isinstance(energy, (int, float))


@pytest.mark.slow
@pytest.mark.requires_mace
class TestMACECalculator:
    """MACE 계산기 테스트 (느림)"""
    
    def test_mace_import(self):
        """MACE import 확인"""
        try:
            from mace.calculators import mace_mp
            assert mace_mp is not None
        except ImportError:
            pytest.skip("MACE not installed")
    
    def test_mace_energy_on_small_system(self, h2o_atoms):
        """MACE로 작은 시스템 에너지 계산"""
        try:
            from mace.calculators import mace_mp
        except ImportError:
            pytest.skip("MACE not installed")
        
        calc = mace_mp(model="small", device="cpu", default_dtype="float64")
        h2o_atoms.calc = calc
        
        energy = h2o_atoms.get_potential_energy()
        
        assert isinstance(energy, float)


@pytest.mark.slow
@pytest.mark.requires_xtb
class TestXTBCalculator:
    """xTB 계산기 테스트 (느림)"""
    
    def test_xtb_import(self):
        """xTB import 확인"""
        try:
            from xtb.ase.calculator import XTB
            assert XTB is not None
        except ImportError:
            pytest.skip("xTB not installed")
    
    def test_xtb_energy_on_molecule(self, h2o_atoms):
        """xTB로 분자 에너지 계산"""
        try:
            from xtb.ase.calculator import XTB
        except ImportError:
            pytest.skip("xTB not installed")
        
        # xTB는 PBC 없는 분자에 적합
        h2o_atoms.set_pbc(False)
        h2o_atoms.calc = XTB(method="GFN2-xTB")
        
        energy = h2o_atoms.get_potential_energy()
        
        assert isinstance(energy, float)


class TestCalculatorCaching:
    """계산기 결과 캐싱 테스트"""
    
    def test_repeated_calculation_same_result(self, mock_calculator, h2o_atoms):
        """동일한 구조에 대한 반복 계산은 동일한 결과"""
        energy1 = mock_calculator.get_energy(h2o_atoms)
        energy2 = mock_calculator.get_energy(h2o_atoms)
        
        assert energy1 == energy2
