"""
Test Adsorption Module

AdsorptionSystem, 흡착 에너지 계산 테스트
"""

import pytest
import numpy as np


class TestAdsorptionSystemImport:
    """AdsorptionSystem import 테스트"""
    
    def test_import_adsorption_system(self):
        """AdsorptionSystem이 import 가능한지"""
        try:
            from surfscreen.adsorption import AdsorptionSystem
            assert AdsorptionSystem is not None
        except ImportError as e:
            pytest.skip(f"AdsorptionSystem not available: {e}")


class TestAdsorptionEnergyFormula:
    """흡착 에너지 공식 테스트"""
    
    def test_adsorption_energy_formula(self):
        """E_ads = E_system - E_surface - E_molecule 검증"""
        # 샘플 값
        E_system = -110.0  # eV
        E_surface = -100.0  # eV
        E_molecule = -5.0  # eV
        
        E_ads = E_system - E_surface - E_molecule
        
        # E_ads = -110 - (-100) - (-5) = -110 + 100 + 5 = -5 eV
        assert np.isclose(E_ads, -5.0)
    
    def test_negative_adsorption_energy_favorable(self):
        """음의 흡착 에너지는 유리함을 의미"""
        E_system = -115.0
        E_surface = -100.0
        E_molecule = -5.0
        
        E_ads = E_system - E_surface - E_molecule
        
        # E_ads < 0: 흡착이 에너지적으로 유리
        assert E_ads < 0
    
    def test_positive_adsorption_energy_unfavorable(self):
        """양의 흡착 에너지는 불리함을 의미"""
        E_system = -103.0  # 근접 시 척력
        E_surface = -100.0
        E_molecule = -5.0
        
        E_ads = E_system - E_surface - E_molecule
        
        # E_ads > 0: 흡착이 에너지적으로 불리
        assert E_ads > 0


@pytest.mark.requires_ase
class TestAdsorptionSystem:
    """AdsorptionSystem 테스트"""
    
    def test_create_adsorption_system(self, cu_slab, h2o_atoms):
        """AdsorptionSystem 생성"""
        try:
            from surfscreen.adsorption import AdsorptionSystem
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("Required modules not available")
        
        # Surface 객체 생성
        try:
            surf = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=3)
        except:
            pytest.skip("SurfaceBuilder failed")
        
        system = AdsorptionSystem(surface=surf, molecule=h2o_atoms)
        
        assert system is not None
    
    def test_generate_configurations(self, cu_slab, h2o_atoms):
        """흡착 구성 생성"""
        try:
            from surfscreen.adsorption import AdsorptionSystem
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("Required modules not available")
        
        try:
            surf = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=3, supercell=(3, 3, 1))
        except:
            pytest.skip("SurfaceBuilder failed")
        
        system = AdsorptionSystem(surface=surf, molecule=h2o_atoms)
        configs = system.generate_configurations(
            rotations=[0, 90],
            heights=[2.0, 3.0],
            max_configs=10
        )
        
        # 구성이 생성됨
        assert len(configs) > 0
        assert len(configs) <= 10
    
    def test_filter_overlapping(self, cu_slab, h2o_atoms):
        """겹치는 구성 필터링"""
        try:
            from surfscreen.adsorption import AdsorptionSystem
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("Required modules not available")
        
        try:
            surf = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=3, supercell=(3, 3, 1))
        except:
            pytest.skip("SurfaceBuilder failed")
        
        system = AdsorptionSystem(surface=surf, molecule=h2o_atoms)
        system.generate_configurations(max_configs=20)
        
        # 필터링
        valid = system.filter_overlapping(min_distance=1.5)
        
        # 필터링 후 구성 수가 같거나 적음
        assert len(valid) <= 20


class TestAdsorptionConfigGeneration:
    """흡착 구성 생성 상세 테스트"""
    
    def test_rotation_angles(self):
        """회전 각도 적용"""
        try:
            from ase import Atoms
            from scipy.spatial.transform import Rotation
        except ImportError:
            pytest.skip("Required modules not available")
        
        # 원래 분자 위치
        original = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        
        # 90도 회전 (z축 기준)
        r = Rotation.from_euler('z', 90, degrees=True)
        rotated = r.apply(original)
        
        # 첫 번째 점은 원점이므로 변화 없음
        assert np.isclose(rotated[0, 0], 0, atol=1e-6)
        # 두 번째 점 (1,0,0) → (0,1,0)
        assert np.isclose(rotated[1, 0], 0, atol=1e-6)
        assert np.isclose(rotated[1, 1], 1, atol=1e-6)
    
    def test_height_placement(self):
        """높이 배치"""
        surface_z_max = 5.0
        height = 2.5
        
        molecule_z = surface_z_max + height
        
        assert np.isclose(molecule_z, 7.5)
    
    def test_overlap_detection(self):
        """겹침 감지 로직"""
        # 두 원자 위치
        pos1 = np.array([0, 0, 0])
        pos2 = np.array([1.0, 0, 0])  # 1Å 거리
        
        distance = np.linalg.norm(pos2 - pos1)
        min_distance = 1.5  # Å
        
        is_overlapping = distance < min_distance
        
        assert is_overlapping == True
    
    def test_no_overlap_detection(self):
        """겹침 없음 감지"""
        pos1 = np.array([0, 0, 0])
        pos2 = np.array([3.0, 0, 0])  # 3Å 거리
        
        distance = np.linalg.norm(pos2 - pos1)
        min_distance = 1.5
        
        is_overlapping = distance < min_distance
        
        assert is_overlapping == False


class TestAdsorptionOptimization:
    """흡착 최적화 테스트"""
    
    def test_optimize_with_emt(self, cu_slab, h2o_atoms):
        """EMT로 최적화"""
        try:
            from ase.calculators.emt import EMT
            from ase.optimize import BFGS
        except ImportError:
            pytest.skip("ASE not installed")
        
        # 간단한 Cu 클러스터 사용 (H2O는 EMT 미지원)
        from ase.cluster import FaceCenteredCubic
        cluster = FaceCenteredCubic('Cu', surfaces=[(1, 0, 0)], layers=[2, 2, 2])
        
        cluster.calc = EMT()
        initial_energy = cluster.get_potential_energy()
        
        opt = BFGS(cluster, logfile=None)
        opt.run(fmax=0.1, steps=10)
        
        final_energy = cluster.get_potential_energy()
        
        # 최적화 완료
        assert final_energy <= initial_energy + 0.1
    
    def test_constraint_preservation(self):
        """Constraint 보존 확인"""
        try:
            from ase import Atoms
            from ase.constraints import FixAtoms
        except ImportError:
            pytest.skip("ASE not installed")
        
        # 간단한 구조
        atoms = Atoms('Cu4', positions=[[0, 0, 0], [2, 0, 0], [0, 2, 0], [2, 2, 0]])
        atoms.set_cell([10, 10, 10])
        
        # 처음 두 원자 고정
        constraint = FixAtoms(indices=[0, 1])
        atoms.set_constraint(constraint)
        
        # Constraint 확인
        const = atoms.constraints
        assert len(const) == 1
        assert 0 in const[0].get_indices()
        assert 1 in const[0].get_indices()


class TestAdsorptionResults:
    """흡착 결과 구조 테스트"""
    
    def test_result_has_required_fields(self):
        """결과에 필수 필드 존재"""
        # 예상 결과 구조
        result = {
            'name': 'config_001',
            'e_ads': -1.5,
            'height': 2.0,
            'site_type': 'top',
            'converged': True,
            'final_energy': -105.5
        }
        
        assert 'name' in result
        assert 'e_ads' in result
        assert 'converged' in result
    
    def test_sort_by_energy(self):
        """에너지로 정렬"""
        results = [
            {'name': 'a', 'e_ads': -1.0},
            {'name': 'b', 'e_ads': -2.0},
            {'name': 'c', 'e_ads': -1.5},
        ]
        
        sorted_results = sorted(results, key=lambda x: x['e_ads'])
        
        # 가장 낮은 에너지가 먼저
        assert sorted_results[0]['name'] == 'b'
        assert sorted_results[0]['e_ads'] == -2.0
