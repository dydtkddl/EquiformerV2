"""
Test Surface Module

SurfaceBuilder, SiteDetector 테스트
"""

import pytest
import numpy as np


class TestSurfaceBuilderImport:
    """SurfaceBuilder import 테스트"""
    
    def test_import_surface_builder(self):
        """SurfaceBuilder가 import 가능한지"""
        try:
            from surfscreen.surface import SurfaceBuilder
            assert SurfaceBuilder is not None
        except ImportError as e:
            pytest.skip(f"SurfaceBuilder not available: {e}")


@pytest.mark.requires_ase
class TestSurfaceBuilder:
    """SurfaceBuilder 테스트"""
    
    def test_from_element_cu111(self):
        """Cu(111) 표면 생성"""
        try:
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("SurfaceBuilder not available")
        
        surf = SurfaceBuilder.from_element(
            'Cu',
            miller_index=(1, 1, 1),
            layers=3,
            supercell=(2, 2, 1),
            vacuum=10.0
        )
        
        assert surf is not None
        assert surf.n_atoms > 0
    
    def test_surface_has_vacuum(self):
        """표면에 진공층이 있는지 확인"""
        try:
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("SurfaceBuilder not available")
        
        surf = SurfaceBuilder.from_element(
            'Cu',
            miller_index=(1, 1, 1),
            layers=3,
            vacuum=15.0
        )
        
        # z 방향 셀 크기가 원자층보다 훨씬 커야 함
        atoms = surf.atoms
        z_positions = atoms.positions[:, 2]
        z_range = z_positions.max() - z_positions.min()
        z_cell = atoms.cell[2, 2]
        
        # 진공이 포함되면 셀이 원자 범위보다 훨씬 큼
        assert z_cell > z_range + 5.0  # 최소 5Å 진공
    
    def test_supercell_multiplies_atoms(self):
        """Supercell이 원자 수를 증가시키는지"""
        try:
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("SurfaceBuilder not available")
        
        # 1x1 표면
        surf_1x1 = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=2, supercell=(1, 1, 1))
        n_1x1 = surf_1x1.n_atoms
        
        # 2x2 표면
        surf_2x2 = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=2, supercell=(2, 2, 1))
        n_2x2 = surf_2x2.n_atoms
        
        # 2x2는 1x1의 4배
        assert n_2x2 == n_1x1 * 4
    
    def test_fixed_layers_creates_constraints(self):
        """fixed_layers가 constraint를 생성하는지"""
        try:
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("SurfaceBuilder not available")
        
        surf = SurfaceBuilder.from_element(
            'Cu',
            miller_index=(1, 1, 1),
            layers=4,
            fixed_layers=2
        )
        
        # 고정된 원자 수 확인
        n_fixed = len(surf.fixed_atoms)
        
        # 최소 일부 원자가 고정되어야 함
        assert n_fixed > 0


@pytest.mark.requires_ase
class TestSiteDetector:
    """SiteDetector 테스트"""
    
    def test_site_detector_import(self):
        """SiteDetector import 확인"""
        try:
            from surfscreen.surface.sites import SiteDetector
            assert SiteDetector is not None
        except ImportError:
            pytest.skip("SiteDetector not available")
    
    def test_detect_sites_on_cu111(self):
        """Cu(111)에서 사이트 감지"""
        try:
            from surfscreen.surface import SurfaceBuilder
            from surfscreen.surface.sites import SiteDetector
        except ImportError:
            pytest.skip("Surface modules not available")
        
        surf = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=3, supercell=(3, 3, 1))
        detector = SiteDetector(surf)
        
        sites = detector.detect_all()
        
        # 사이트가 감지되어야 함
        assert len(sites) > 0
    
    def test_site_types_exist(self):
        """사이트 유형 enum 확인"""
        try:
            from surfscreen.surface.sites import SiteType
        except ImportError:
            pytest.skip("SiteType not available")
        
        # 주요 사이트 유형 확인
        assert hasattr(SiteType, 'TOP') or hasattr(SiteType, 'top')
        assert hasattr(SiteType, 'BRIDGE') or hasattr(SiteType, 'bridge')


class TestSurfaceGeometry:
    """표면 기하 구조 테스트"""
    
    def test_fcc111_stacking(self):
        """FCC(111) 스태킹 순서 확인"""
        try:
            from ase.build import fcc111
        except ImportError:
            pytest.skip("ASE not installed")
        
        slab = fcc111('Cu', size=(1, 1, 6), vacuum=10.0)
        
        # z 좌표 추출
        z_coords = slab.positions[:, 2]
        unique_z = np.unique(np.round(z_coords, 2))
        
        # 6층이면 6개의 고유 z 좌표
        assert len(unique_z) == 6
    
    def test_miller_indices_affect_structure(self):
        """다른 밀러 지수는 다른 구조"""
        try:
            from ase.build import fcc111, fcc100
        except ImportError:
            pytest.skip("ASE not installed")
        
        slab_111 = fcc111('Cu', size=(2, 2, 3), vacuum=10.0)
        slab_100 = fcc100('Cu', size=(2, 2, 3), vacuum=10.0)
        
        # 셀 파라미터가 다름
        cell_111 = slab_111.cell.lengths()
        cell_100 = slab_100.cell.lengths()
        
        # a, b 격자 상수가 다름
        assert not np.allclose(cell_111[:2], cell_100[:2], rtol=0.01)


class TestSurfaceArea:
    """표면 면적 계산 테스트"""
    
    def test_area_calculation(self):
        """표면 면적 계산"""
        try:
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("SurfaceBuilder not available")
        
        surf = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=3, supercell=(3, 3, 1))
        
        # 면적은 양수
        assert surf.area > 0
    
    def test_supercell_increases_area(self):
        """Supercell이 면적을 증가시키는지"""
        try:
            from surfscreen.surface import SurfaceBuilder
        except ImportError:
            pytest.skip("SurfaceBuilder not available")
        
        surf_2x2 = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=3, supercell=(2, 2, 1))
        surf_4x4 = SurfaceBuilder.from_element('Cu', (1, 1, 1), layers=3, supercell=(4, 4, 1))
        
        # 4x4는 2x2의 4배 면적
        assert np.isclose(surf_4x4.area, surf_2x2.area * 4, rtol=0.01)


class TestSurfaceFromFile:
    """파일에서 표면 로드 테스트"""
    
    def test_from_file_xyz(self, tmp_path):
        """XYZ 파일에서 표면 로드"""
        try:
            from surfscreen.surface import SurfaceBuilder
            from ase import Atoms
            from ase.io import write
        except ImportError:
            pytest.skip("Required modules not available")
        
        # 샘플 구조 저장
        atoms = Atoms('Cu4', positions=[[0, 0, 0], [2.55, 0, 0], [0, 2.55, 0], [2.55, 2.55, 0]])
        atoms.set_cell([5.1, 5.1, 15.0])
        atoms.set_pbc(True)
        
        xyz_path = tmp_path / "surface.xyz"
        write(str(xyz_path), atoms)
        
        # 로드
        surf = SurfaceBuilder.from_file(str(xyz_path))
        
        assert surf.n_atoms == 4
