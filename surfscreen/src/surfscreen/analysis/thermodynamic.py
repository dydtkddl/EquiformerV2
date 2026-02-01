"""
Thermodynamic Analysis Module

열역학 분석 도구
- Boltzmann 분포
- 자유 에너지 추정
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from ase import Atoms
from ase.io import read

from surfscreen.logging_utils import analysis_logger as logger, physics_logger


# 물리 상수
kB_eV = 8.617333262e-5  # eV/K
kB_J = 1.380649e-23  # J/K


@dataclass
class BoltzmannResult:
    """Boltzmann 분포 결과"""
    names: List[str]
    energies: List[float]  # eV
    probabilities: List[float]  # normalized
    temperature: float  # K
    partition_function: float
    
    def to_dict(self) -> dict:
        return {
            "temperature_K": self.temperature,
            "partition_function": self.partition_function,
            "configurations": [
                {"name": n, "energy_eV": e, "probability": p}
                for n, e, p in zip(self.names, self.energies, self.probabilities)
            ]
        }


@dataclass
class FreeEnergyResult:
    """자유 에너지 결과"""
    name: str
    E_electronic: float  # eV
    E_zpe: float  # eV (Zero Point Energy)
    E_thermal: float  # eV
    S_vib: float  # eV/K (진동 엔트로피)
    H: float  # eV (엔탈피)
    G: float  # eV (깁스 자유 에너지)
    temperature: float  # K
    frequencies: List[float]  # cm⁻¹
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "temperature_K": self.temperature,
            "E_electronic_eV": self.E_electronic,
            "E_zpe_eV": self.E_zpe,
            "E_thermal_eV": self.E_thermal,
            "S_vib_eV_K": self.S_vib,
            "H_eV": self.H,
            "G_eV": self.G,
            "frequencies_cm-1": self.frequencies
        }


class ThermodynamicAnalyzer:
    """열역학 분석기"""
    
    def __init__(self, results: List[Dict] = None):
        """
        Args:
            results: 스크리닝 결과 리스트 [{"name": str, "energy": float}, ...]
        """
        self.results = results or []
        logger.debug(f"ThermodynamicAnalyzer initialized with {len(self.results)} results")
        
    def add_result(self, name: str, energy: float, atoms: Optional[Atoms] = None):
        """결과 추가"""
        self.results.append({
            "name": name,
            "energy": energy,
            "atoms": atoms
        })
        logger.detail(f"Added result: {name}, E={energy:.6f} eV")
        
    def load_from_directory(self, results_dir: str):
        """결과 디렉토리에서 로드"""
        import json
        
        results_path = Path(results_dir)
        logger.step(f"Loading results from: {results_path}")
        
        # results.json 찾기
        json_file = results_path / "results.json"
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)
                
            for entry in data.get("results", []):
                self.add_result(
                    name=entry.get("name", ""),
                    energy=entry.get("adsorption_energy", entry.get("energy", 0))
                )
            logger.success(f"Loaded {len(self.results)} results from {json_file.name}")
        else:
            logger.warning(f"results.json not found in {results_path}")
    
    def calculate_boltzmann(self, temperature: float = 300.0) -> BoltzmannResult:
        """Boltzmann 분포 계산
        
        P_i = exp(-E_i / kT) / Z
        Z = Σ exp(-E_i / kT)
        
        Args:
            temperature: 온도 (K)
            
        Returns:
            BoltzmannResult
        """
        with logger.section("Boltzmann Distribution"):
            if not self.results:
                logger.error("No results to analyze")
                raise ValueError("No results to analyze")
            
            logger.info(f"Temperature: {temperature} K")
            logger.info(f"Configurations: {len(self.results)}")
            
            names = [r["name"] for r in self.results]
            energies = np.array([r["energy"] for r in self.results])
            
            # 최저 에너지를 기준으로
            E_ref = energies.min()
            E_rel = energies - E_ref
            
            logger.detail(f"Reference energy: {E_ref:.6f} eV")
            
            # Boltzmann 인자
            beta = 1.0 / (kB_eV * temperature)
            physics_logger.log_formula(
                "Boltzmann factor",
                "β = 1/(kB*T)",
                {"kB": kB_eV, "T": temperature},
                beta
            )
            
            boltzmann_factors = np.exp(-E_rel * beta)
            
            # 분배 함수
            Z = np.sum(boltzmann_factors)
            logger.calc(f"Partition function Z = {Z:.6f}")
            
            # 확률
            probabilities = boltzmann_factors / Z
            
            # 상위 3개 출력
            top_indices = np.argsort(probabilities)[::-1][:3]
            for idx in top_indices:
                logger.data(
                    f"Top config: {names[idx]}",
                    E_rel_eV=E_rel[idx],
                    probability=probabilities[idx]
                )
            
            logger.success(f"Calculated Boltzmann distribution for {len(names)} configurations")
            
            return BoltzmannResult(
                names=names,
                energies=energies.tolist(),
                probabilities=probabilities.tolist(),
                temperature=temperature,
                partition_function=Z
            )
    
    def calculate_free_energy(self,
                               atoms: Atoms,
                               name: str,
                               temperature: float = 300.0,
                               pressure: float = 1.0) -> FreeEnergyResult:
        """자유 에너지 계산 (진동 분석 기반, Harmonic Approximation)
        
        G = E_elec + ZPE + U_vib - T*S_vib
        
        where:
            ZPE = (1/2) Σ ℏω
            U_vib = Σ ℏω * n(ω,T)  [Bose-Einstein]
            S_vib from vibrational partition function
        
        Args:
            atoms: Atoms 객체 (calculator 포함)
            name: 구성 이름
            temperature: 온도 (K)
            pressure: 압력 (bar)
            
        Returns:
            FreeEnergyResult
        """
        from ase.vibrations import Vibrations
        from ase.thermochemistry import HarmonicThermo
        
        with logger.section(f"Free Energy ({name})"):
            logger.info(f"Temperature: {temperature} K, Pressure: {pressure} bar")
            
            # 전자 에너지
            E_elec = atoms.get_potential_energy()
            logger.energy(f"Electronic energy: E_elec = {E_elec:.6f} eV")
            
            # 진동 계산
            logger.step("Computing vibrational frequencies...")
            vib = Vibrations(atoms)
            
            try:
                vib.run()
                # ASE Vibrations.get_frequencies() returns cm⁻¹
                frequencies_cm = vib.get_frequencies()
                vib.clean()
                logger.detail(f"Found {len(frequencies_cm)} vibrational modes")
            except Exception as e:
                # Vibration 계산 실패 시
                logger.warning(f"Vibration calculation failed: {e}")
                frequencies_cm = []
                
            # 유효 진동 모드만 (허수 제거)
            # ASE returns complex numbers for imaginary frequencies
            real_freqs_cm = []
            n_imaginary = 0
            for f in frequencies_cm:
                if np.isreal(f) and f.real > 0:
                    real_freqs_cm.append(f.real)
                elif hasattr(f, 'real') and f.real > 0:
                    real_freqs_cm.append(f.real)
                else:
                    n_imaginary += 1
            
            if n_imaginary > 0:
                logger.warning(f"Removed {n_imaginary} imaginary modes (transition state?)")
            
            real_freqs_cm = np.array(real_freqs_cm)
            logger.detail(f"Valid modes: {len(real_freqs_cm)}, range: {real_freqs_cm.min():.1f} - {real_freqs_cm.max():.1f} cm⁻¹" 
                         if len(real_freqs_cm) > 0 else "No valid vibrational modes")
            
            # cm⁻¹ → eV: 1 cm⁻¹ = 1.23984×10⁻⁴ eV
            freqs_eV = real_freqs_cm * 1.23984e-4
            
            physics_logger.log_formula(
                "Unit Conversion",
                "E(eV) = ν(cm⁻¹) × 1.23984e-4",
                {"cm_to_eV_factor": 1.23984e-4},
                freqs_eV.sum() if len(freqs_eV) > 0 else 0
            )
            
            if len(freqs_eV) > 0:
                # 열역학 계산 (ASE HarmonicThermo expects eV)
                thermo = HarmonicThermo(
                    vib_energies=freqs_eV,
                    potentialenergy=E_elec
                )
                
                # ZPE
                E_zpe = thermo.get_ZPE_correction()
                physics_logger.log_formula(
                    "Zero Point Energy",
                    "ZPE = (1/2) × Σ ℏω",
                    {"n_modes": len(freqs_eV), "sum_hbar_omega": freqs_eV.sum()},
                    E_zpe
                )
                logger.calc(f"ZPE = {E_zpe:.6f} eV")
                
                # 엔트로피 (Bose-Einstein statistics)
                S = thermo.get_entropy(temperature)
                logger.calc(f"Vibrational entropy: S = {S:.6e} eV/K = {S*1e3:.4f} meV/K")
                
                # 내부 에너지
                U = thermo.get_internal_energy(temperature)
                E_thermal = U - E_elec - E_zpe
                
                physics_logger.log_formula(
                    "Thermal Energy",
                    "E_thermal = U - E_elec - ZPE",
                    {"U": U, "E_elec": E_elec, "ZPE": E_zpe},
                    E_thermal
                )
                logger.calc(f"Thermal energy: E_thermal = {E_thermal:.6f} eV")
                
                # 엔탈피 (고체의 경우 PV ≈ 0, 기체의 경우 PV ≈ kT)
                H = U
                logger.calc(f"Enthalpy: H = {H:.6f} eV")
                
                # Helmholtz 자유 에너지 (고체/흡착 시스템에 적합)
                G = thermo.get_helmholtz_energy(temperature)
                
                physics_logger.log_formula(
                    "Gibbs Free Energy",
                    "G = H - T×S = E_elec + ZPE + E_thermal - T×S",
                    {"H": H, "T": temperature, "S": S, "T_S": temperature * S},
                    G
                )
                
            else:
                # 진동 계산 없이 근사
                logger.warning("No vibrational modes - using electronic energy only")
                E_zpe = 0.0
                E_thermal = 0.0
                S = 0.0
                H = E_elec
                G = E_elec
            
            logger.energy(f"Gibbs free energy: G = {G:.6f} eV")
            logger.success(f"Free energy calculation complete: G = {G:.6f} eV at T = {temperature} K")
            
            return FreeEnergyResult(
                name=name,
                E_electronic=E_elec,
                E_zpe=E_zpe,
                E_thermal=E_thermal,
                S_vib=S,
                H=H,
                G=G,
                temperature=temperature,
                frequencies=real_freqs_cm.tolist() if len(real_freqs_cm) > 0 else []
            )
    
    def get_ranking(self, by: str = "energy") -> List[Dict]:
        """에너지/확률 순위"""
        if by == "energy":
            sorted_results = sorted(self.results, key=lambda x: x["energy"])
        elif by == "probability":
            boltz = self.calculate_boltzmann()
            indices = np.argsort(boltz.probabilities)[::-1]  # 내림차순
            sorted_results = [self.results[i] for i in indices]
        else:
            sorted_results = self.results
            
        return [
            {"rank": i+1, "name": r["name"], "energy": r["energy"]}
            for i, r in enumerate(sorted_results)
        ]
    
    def get_summary(self, temperature: float = 300.0) -> Dict:
        """요약 통계"""
        if not self.results:
            return {}
            
        energies = [r["energy"] for r in self.results]
        boltz = self.calculate_boltzmann(temperature)
        
        return {
            "n_configurations": len(self.results),
            "temperature_K": temperature,
            "energy_min_eV": min(energies),
            "energy_max_eV": max(energies),
            "energy_range_eV": max(energies) - min(energies),
            "energy_mean_eV": np.mean(energies),
            "energy_std_eV": np.std(energies),
            "most_probable": boltz.names[np.argmax(boltz.probabilities)],
            "max_probability": max(boltz.probabilities)
        }


def calculate_coverage_energy(results: List[Dict],
                               surface_area: float,
                               n_sites: int) -> Dict:
    """Coverage 의존 흡착 에너지
    
    Args:
        results: 흡착 결과 리스트
        surface_area: 표면 면적 (Å²)
        n_sites: 총 흡착 사이트 수
        
    Returns:
        Coverage-에너지 관계
    """
    coverages = []
    energies = []
    
    for i in range(1, len(results) + 1):
        coverage = i / n_sites
        
        # 가장 안정한 i개 구성의 평균 에너지
        sorted_results = sorted(results, key=lambda x: x["energy"])[:i]
        avg_energy = np.mean([r["energy"] for r in sorted_results])
        
        coverages.append(coverage)
        energies.append(avg_energy)
        
    return {
        "coverage": coverages,
        "average_energy_eV": energies,
        "surface_area_A2": surface_area,
        "n_sites": n_sites
    }
