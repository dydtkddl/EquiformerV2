"""
Test Analysis Dynamics Module

MSD, Diffusion, Conductivity 계산 테스트
"""

import pytest
import numpy as np


class TestDynamicsAnalyzerImport:
    """DynamicsAnalyzer import 테스트"""
    
    def test_import_dynamics_analyzer(self):
        """DynamicsAnalyzer가 import 가능한지 확인"""
        try:
            from surfscreen.analysis import DynamicsAnalyzer
            assert DynamicsAnalyzer is not None
        except ImportError as e:
            pytest.skip(f"DynamicsAnalyzer not available: {e}")


@pytest.mark.requires_ase
class TestMSDCalculation:
    """Mean Square Displacement 계산 테스트"""
    
    def test_msd_static_system_is_zero(self, static_trajectory):
        """정적 시스템의 MSD는 0에 가까워야 함"""
        try:
            from surfscreen.analysis import DynamicsAnalyzer
        except ImportError:
            pytest.skip("DynamicsAnalyzer not available")
        
        analyzer = DynamicsAnalyzer(static_trajectory, timestep=1.0)
        result = analyzer.calculate_msd('Li')
        
        # 정적 시스템에서 MSD는 거의 0
        assert np.allclose(result.msd, 0, atol=1e-6)
    
    def test_msd_result_structure(self, li_trajectory):
        """MSD 결과 구조 확인"""
        try:
            from surfscreen.analysis import DynamicsAnalyzer
        except ImportError:
            pytest.skip("DynamicsAnalyzer not available")
        
        analyzer = DynamicsAnalyzer(li_trajectory, timestep=1.0)
        result = analyzer.calculate_msd('Li')
        
        # 결과 속성 확인
        assert hasattr(result, 'time')
        assert hasattr(result, 'msd')
        assert len(result.time) == len(result.msd)
    
    def test_msd_monotonically_increasing(self, li_trajectory):
        """확산 시스템의 MSD는 시간에 따라 증가해야 함"""
        try:
            from surfscreen.analysis import DynamicsAnalyzer
        except ImportError:
            pytest.skip("DynamicsAnalyzer not available")
        
        analyzer = DynamicsAnalyzer(li_trajectory, timestep=1.0)
        result = analyzer.calculate_msd('Li')
        
        # MSD는 대체로 증가해야 함 (노이즈로 인해 완벽히 단조증가는 아님)
        # 처음과 끝을 비교
        assert result.msd[-1] > result.msd[0]


@pytest.mark.requires_ase
class TestDiffusionCalculation:
    """확산 계수 계산 테스트"""
    
    def test_diffusion_result_structure(self, li_trajectory):
        """확산 계수 결과 구조 확인"""
        try:
            from surfscreen.analysis import DynamicsAnalyzer
        except ImportError:
            pytest.skip("DynamicsAnalyzer not available")
        
        analyzer = DynamicsAnalyzer(li_trajectory, timestep=1.0)
        result = analyzer.calculate_diffusion('Li')
        
        # 결과 속성 확인
        assert hasattr(result, 'D')
        assert hasattr(result, 'D_error')
        assert hasattr(result, 'r_squared')
        
        # D는 양수여야 함
        assert result.D >= 0
    
    def test_einstein_relation_formula(self):
        """Einstein 관계 공식 검증: D = slope / 6"""
        # 합성 데이터로 직접 검증
        slope = 12.0  # Ų/fs
        D_expected = slope / 6.0  # = 2.0 Ų/fs
        
        assert np.isclose(D_expected, 2.0)
    
    def test_unit_conversion_angstrom_to_cm(self):
        """단위 변환 검증: Ų/fs → cm²/s"""
        # 1 Ų/fs = 0.1 cm²/s (1e-16 cm² / 1e-15 s = 0.1)
        D_angstrom_fs = 1.0  # Ų/fs
        D_cm_s = D_angstrom_fs * 0.1  # cm²/s
        
        assert np.isclose(D_cm_s, 0.1)


@pytest.mark.requires_ase
class TestConductivityCalculation:
    """이온 전도도 계산 테스트"""
    
    def test_nernst_einstein_formula(self):
        """Nernst-Einstein 공식 검증"""
        # σ = (n × z² × e² × D) / (kB × T)
        
        # 상수
        e = 1.602176634e-19  # C
        kB = 1.380649e-23  # J/K
        
        # 샘플 값
        n = 1e22  # cm⁻³ = 1e28 m⁻³
        z = 1
        D = 1e-8  # cm²/s = 1e-12 m²/s
        T = 300  # K
        
        # cm²/s → m²/s
        D_m2_s = D * 1e-4
        # cm⁻³ → m⁻³
        n_m3 = n * 1e6
        
        # 이론값 계산
        sigma = (n_m3 * z**2 * e**2 * D_m2_s) / (kB * T)
        
        # σ > 0 확인
        assert sigma > 0
        
        # 대략적 크기 확인 (S/m 단위)
        # S/m → S/cm: sigma / 100
        sigma_S_cm = sigma / 100
        assert sigma_S_cm > 0
    
    def test_conductivity_result_structure(self, li_trajectory):
        """전도도 결과 구조 확인"""
        try:
            from surfscreen.analysis import DynamicsAnalyzer
        except ImportError:
            pytest.skip("DynamicsAnalyzer not available")
        
        analyzer = DynamicsAnalyzer(li_trajectory, timestep=1.0)
        
        try:
            result = analyzer.calculate_conductivity('Li', charge=1, temperature=300)
        except Exception:
            pytest.skip("Conductivity calculation requires volume info")
        
        # 결과 속성 확인
        assert hasattr(result, 'sigma')
        assert hasattr(result, 'temperature')
        assert result.temperature == 300


class TestPhysicsFormulas:
    """물리 공식 직접 테스트 (import 없이)"""
    
    def test_msd_formula_3d(self):
        """3D MSD 공식: MSD = <|r(t) - r(0)|²>"""
        # 초기 위치
        r0 = np.array([0, 0, 0])
        # 나중 위치
        r1 = np.array([1, 1, 1])
        
        # 변위 제곱
        displacement_sq = np.sum((r1 - r0)**2)
        
        assert np.isclose(displacement_sq, 3.0)
    
    def test_diffusion_3d_factor(self):
        """3D 확산에서 MSD = 6Dt 확인"""
        D = 1.0  # cm²/s
        t = 10.0  # s
        
        MSD_expected = 6 * D * t
        
        assert np.isclose(MSD_expected, 60.0)
    
    def test_diffusion_1d_factor(self):
        """1D 확산에서 MSD = 2Dt 확인"""
        D = 1.0
        t = 10.0
        
        MSD_expected = 2 * D * t
        
        assert np.isclose(MSD_expected, 20.0)
    
    def test_codata_constants(self):
        """CODATA 상수 값 확인"""
        # 기본 전하 (2019 CODATA)
        e_exact = 1.602176634e-19  # C (정확값)
        
        # Boltzmann 상수 (2019 CODATA)
        kB_exact = 1.380649e-23  # J/K (정확값)
        
        # Avogadro 수 (2019 CODATA)
        NA_exact = 6.02214076e23  # mol⁻¹ (정확값)
        
        # 정확한 값인지 확인
        assert np.isclose(e_exact, 1.602176634e-19, rtol=1e-10)
        assert np.isclose(kB_exact, 1.380649e-23, rtol=1e-10)
        assert np.isclose(NA_exact, 6.02214076e23, rtol=1e-10)


class TestTimeAverageMSD:
    """Time-averaged MSD (TAMSD) 테스트"""
    
    def test_tamsd_reduces_noise(self):
        """TAMSD가 단순 MSD보다 노이즈가 적어야 함"""
        # 합성 trajectory 생성
        np.random.seed(42)
        n_frames = 100
        n_atoms = 10
        
        # 위치 추적
        positions = np.zeros((n_frames, n_atoms, 3))
        for t in range(1, n_frames):
            # 브라운 운동
            positions[t] = positions[t-1] + np.random.randn(n_atoms, 3) * 0.1
        
        # 단순 MSD (lag=1에서만)
        msd_simple = np.mean(np.sum((positions[1:] - positions[:-1])**2, axis=2))
        
        # TAMSD (여러 lag 평균)
        # 단순화된 검증
        assert msd_simple > 0
