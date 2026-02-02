"""
Test Analysis Thermodynamic Module

ZPE, Gibbs Free Energy, Boltzmann 분포 테스트
"""

import pytest
import numpy as np


class TestThermodynamicConstants:
    """열역학 상수 테스트"""
    
    def test_boltzmann_constant_ev(self):
        """Boltzmann 상수 eV/K 값 확인"""
        # kB = 8.617333262e-5 eV/K (CODATA 2018)
        kB_eV = 8.617333262e-5
        
        # kB * 300K ≈ 0.0259 eV (실온 열에너지)
        thermal_energy = kB_eV * 300
        
        assert np.isclose(thermal_energy, 0.0259, atol=0.001)
    
    def test_planck_constant(self):
        """Planck 상수 값 확인"""
        # h = 6.62607015e-34 J·s (정확값)
        h = 6.62607015e-34
        
        # ℏ = h / (2π)
        hbar = h / (2 * np.pi)
        
        assert np.isclose(hbar, 1.054571817e-34, rtol=1e-6)
    
    def test_wavenumber_to_ev_conversion(self):
        """파수(cm⁻¹) → eV 변환 확인"""
        # 1 cm⁻¹ = 1.239841984e-4 eV
        cm_to_eV = 1.23984e-4
        
        # 1000 cm⁻¹ 진동
        freq_cm = 1000
        freq_eV = freq_cm * cm_to_eV
        
        assert np.isclose(freq_eV, 0.123984, rtol=1e-4)


class TestZPECalculation:
    """Zero Point Energy 계산 테스트"""
    
    def test_zpe_formula(self):
        """ZPE = (1/2) × Σ ℏω 검증"""
        # 샘플 진동수 (eV 단위)
        frequencies_eV = np.array([0.1, 0.2, 0.3])  # eV
        
        # ZPE = 0.5 * sum(frequencies)
        zpe = 0.5 * np.sum(frequencies_eV)
        
        assert np.isclose(zpe, 0.3)
    
    def test_zpe_from_wavenumbers(self):
        """파수에서 ZPE 계산"""
        # 샘플 진동수 (cm⁻¹)
        frequencies_cm = np.array([1000, 2000, 3000])
        
        # cm⁻¹ → eV 변환
        cm_to_eV = 1.23984e-4
        frequencies_eV = frequencies_cm * cm_to_eV
        
        # ZPE
        zpe = 0.5 * np.sum(frequencies_eV)
        
        # 예상값: 0.5 * 6000 * 1.23984e-4 = 0.372 eV
        assert np.isclose(zpe, 0.372, atol=0.01)
    
    def test_imaginary_frequencies_excluded(self):
        """허수 진동수는 ZPE 계산에서 제외"""
        # 진동수 (일부 음수 = 허수)
        frequencies = np.array([-100, 1000, 2000])  # cm⁻¹
        
        # 양수만 필터링
        real_frequencies = frequencies[frequencies > 0]
        
        assert len(real_frequencies) == 2
        assert -100 not in real_frequencies


class TestThermalEnergy:
    """열 에너지 계산 테스트"""
    
    def test_thermal_energy_formula(self):
        """열 에너지 공식: E = kT × Σ [x/(exp(x)-1)]"""
        kB_eV = 8.617333262e-5  # eV/K
        T = 300  # K
        kT = kB_eV * T
        
        # 샘플 진동수
        freq_eV = 0.1  # eV
        x = freq_eV / kT
        
        # 단일 모드 기여
        if x > 0:
            n_avg = 1.0 / (np.exp(x) - 1)  # Bose-Einstein 분포
            E_thermal = freq_eV * n_avg
        else:
            E_thermal = 0
        
        assert E_thermal >= 0
    
    def test_high_frequency_limit(self):
        """고주파수 극한: E → 0 (hν >> kT)"""
        kB_eV = 8.617333262e-5
        T = 300
        kT = kB_eV * T  # ≈ 0.026 eV
        
        # 고주파수 (kT보다 훨씬 큼)
        freq_eV = 1.0  # eV (>> 0.026 eV)
        x = freq_eV / kT
        
        # exp(x) - 1 ≈ exp(x) for large x
        n_avg = 1.0 / (np.exp(x) - 1)
        
        # n_avg → 0 for large x
        assert n_avg < 0.01
    
    def test_low_frequency_limit(self):
        """저주파수 극한: E → kT (hν << kT, 고전 극한)"""
        kB_eV = 8.617333262e-5
        T = 300
        kT = kB_eV * T
        
        # 저주파수 (kT보다 작음)
        freq_eV = 0.001  # eV (<< 0.026 eV)
        x = freq_eV / kT
        
        # 저주파수 극한에서 n_avg ≈ kT/hν
        n_avg = 1.0 / (np.exp(x) - 1)
        E_thermal = freq_eV * n_avg
        
        # E → kT (고전 극한)
        assert np.isclose(E_thermal, kT, rtol=0.2)


class TestGibbsFreeEnergy:
    """Gibbs 자유 에너지 테스트"""
    
    def test_gibbs_formula(self):
        """G = E_elec + ZPE + E_thermal - TS 검증"""
        E_elec = -100.0  # eV
        ZPE = 0.5  # eV
        E_thermal = 0.2  # eV
        T = 300  # K
        S = 0.001  # eV/K (가상 값)
        
        G = E_elec + ZPE + E_thermal - T * S
        
        expected = -100.0 + 0.5 + 0.2 - 0.3  # = -99.6 eV
        assert np.isclose(G, -99.6)
    
    def test_gibbs_temperature_dependence(self):
        """온도에 따른 Gibbs 변화: 높은 T → 낮은 G"""
        E_base = -100.0  # eV
        S = 0.001  # eV/K
        
        G_300K = E_base - 300 * S
        G_600K = E_base - 600 * S
        
        # 엔트로피가 양수이면 높은 온도에서 G 감소
        assert G_600K < G_300K


class TestBoltzmannDistribution:
    """Boltzmann 분포 테스트"""
    
    def test_boltzmann_probability_sum_to_one(self):
        """Boltzmann 확률 합은 1"""
        energies = np.array([-1.5, -1.2, -1.0, -0.8])  # eV
        T = 300  # K
        kB_eV = 8.617333262e-5
        kT = kB_eV * T
        
        # Boltzmann 가중치
        weights = np.exp(-energies / kT)
        
        # 정규화
        probabilities = weights / np.sum(weights)
        
        assert np.isclose(np.sum(probabilities), 1.0)
    
    def test_lowest_energy_highest_probability(self):
        """가장 낮은 에너지가 가장 높은 확률"""
        energies = np.array([-1.5, -1.2, -1.0])  # eV
        T = 300  # K
        kB_eV = 8.617333262e-5
        kT = kB_eV * T
        
        weights = np.exp(-energies / kT)
        probabilities = weights / np.sum(weights)
        
        # 가장 낮은 에너지(-1.5)의 확률이 가장 높음
        assert np.argmax(probabilities) == 0
    
    def test_high_temperature_uniform_distribution(self):
        """고온에서 균등 분포에 가까워짐"""
        energies = np.array([-1.5, -1.2, -1.0])  # eV
        T = 10000  # K (매우 높은 온도)
        kB_eV = 8.617333262e-5
        kT = kB_eV * T
        
        weights = np.exp(-energies / kT)
        probabilities = weights / np.sum(weights)
        
        # 고온에서 확률이 거의 균등
        assert np.std(probabilities) < 0.1
    
    def test_low_temperature_ground_state_dominance(self):
        """저온에서 바닥 상태 지배"""
        energies = np.array([-1.5, -1.2, -1.0])  # eV
        T = 100  # K (낮은 온도)
        kB_eV = 8.617333262e-5
        kT = kB_eV * T
        
        weights = np.exp(-energies / kT)
        probabilities = weights / np.sum(weights)
        
        # 저온에서 바닥 상태 확률이 매우 높음
        assert probabilities[0] > 0.99
    
    def test_relative_population_formula(self):
        """상대 점유율 공식: n2/n1 = exp(-(E2-E1)/kT)"""
        E1 = -1.5  # eV
        E2 = -1.2  # eV
        T = 300  # K
        kB_eV = 8.617333262e-5
        kT = kB_eV * T
        
        # 에너지 차이
        dE = E2 - E1  # 0.3 eV
        
        # 상대 점유율
        ratio = np.exp(-dE / kT)
        
        # dE > 0이면 ratio < 1
        assert ratio < 1


class TestEntropyCalculation:
    """엔트로피 계산 테스트"""
    
    def test_vibrational_entropy_formula(self):
        """진동 엔트로피 공식"""
        kB_eV = 8.617333262e-5
        T = 300
        kT = kB_eV * T
        
        # 샘플 진동수
        freq_eV = 0.05  # eV
        x = freq_eV / kT
        
        # 단일 모드 엔트로피 (eV/K)
        if x > 0:
            S_mode = kB_eV * (x / (np.exp(x) - 1) - np.log(1 - np.exp(-x)))
        else:
            S_mode = 0
        
        assert S_mode >= 0
    
    def test_entropy_increases_with_temperature(self):
        """온도가 높을수록 엔트로피 증가"""
        kB_eV = 8.617333262e-5
        freq_eV = 0.05
        
        def calc_entropy(T):
            kT = kB_eV * T
            x = freq_eV / kT
            if x > 0 and x < 50:  # 오버플로우 방지
                return kB_eV * (x / (np.exp(x) - 1) - np.log(1 - np.exp(-x)))
            return 0
        
        S_300 = calc_entropy(300)
        S_600 = calc_entropy(600)
        
        assert S_600 > S_300
