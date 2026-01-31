"""
Phonon Analysis Module

진동 분석 및 열역학 보정
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ase import Atoms, units

KB = units.kB


@dataclass
class PhononResult:
    """Phonon 결과"""
    frequencies_cm1: np.ndarray
    frequencies_meV: np.ndarray
    zpe: float
    n_imaginary: int
    
    @property
    def has_imaginary(self) -> bool:
        return self.n_imaginary > 0


@dataclass  
class ThermoResult:
    """열역학 결과"""
    temperature: float
    pressure: float
    E_pot: float
    ZPE: float
    U_vib: float
    S_vib: float
    H: float
    G: float


class PhononAnalyzer:
    """Phonon 분석"""
    
    def __init__(self, atoms: Atoms, calculator=None, delta: float = 0.01):
        self.atoms = atoms.copy()
        self.calculator = calculator
        self.delta = delta
        if calculator:
            self.atoms.calc = calculator
            
    def calculate_vibrations(self, indices: Optional[List[int]] = None, 
                              cleanup: bool = True) -> PhononResult:
        """진동 주파수 계산
        
        Args:
            indices: 진동을 계산할 원자 인덱스 (None=전체)
            cleanup: 임시 파일 정리 여부
            
        Returns:
            PhononResult
        """
        from ase.vibrations import Vibrations
        import os
        import tempfile
        
        # 임시 디렉토리 사용
        work_dir = tempfile.mkdtemp(prefix="phonon_")
        original_dir = os.getcwd()
        
        try:
            os.chdir(work_dir)
            vib = Vibrations(self.atoms, indices=indices, delta=self.delta)
            vib.run()
            freq_cm1 = vib.get_frequencies()
            
            real_freqs = []
            n_imaginary = 0
            for f in freq_cm1:
                if np.isreal(f) and f.real > 0:
                    real_freqs.append(f.real)
                else:
                    n_imaginary += 1
                    
            freq_cm1 = np.array(real_freqs)
            freq_meV = freq_cm1 * 0.12398
            zpe = 0.5 * np.sum(freq_cm1 * 1.23984e-4)
            
            if cleanup:
                vib.clean()
                
            return PhononResult(freq_cm1, freq_meV, zpe, n_imaginary)
        finally:
            os.chdir(original_dir)
            if cleanup:
                import shutil
                try:
                    shutil.rmtree(work_dir)
                except:
                    pass
    
    def calculate_thermodynamics(self, temperature: float = 298.15, 
                                  pressure: float = 1.0,
                                  phonon_result: Optional[PhononResult] = None) -> ThermoResult:
        """열역학량 계산 (Harmonic approximation)
        
        ZPE = (1/2) Σ ℏω
        U_vib = Σ ℏω [1/2 + n(ω,T)]  where n = 1/(exp(ℏω/kT) - 1)
        S_vib = kB Σ [(ℏω/kT)n(ω,T) - ln(1 - exp(-ℏω/kT))]
        G = E_pot + U_vib - T*S_vib
        """
        if phonon_result is None:
            phonon_result = self.calculate_vibrations()
            
        E_pot = self.atoms.get_potential_energy() if self.atoms.calc else 0.0
        
        # Convert cm⁻¹ to eV: 1 cm⁻¹ = 1.23984×10⁻⁴ eV
        freqs_eV = phonon_result.frequencies_cm1 * 1.23984e-4
        
        T = temperature
        U_vib = 0.0
        S_vib = 0.0
        
        for omega in freqs_eV:
            if omega > 0 and T > 0:
                # ℏω / kT
                x = omega / (KB * T)
                
                if x < 700:  # Avoid overflow
                    # Bose-Einstein occupation number
                    n_bose = 1.0 / (np.exp(x) - 1)
                    
                    # Internal energy contribution: ℏω(1/2 + n)
                    U_vib += omega * (0.5 + n_bose)
                    
                    # Entropy contribution: kB[(x*n) - ln(1 - exp(-x))]
                    S_vib += KB * (x * n_bose - np.log(1 - np.exp(-x)))
                else:
                    # High frequency limit: only ZPE contribution
                    U_vib += omega * 0.5
                    # S → 0 as x → ∞
                    
        H = E_pot + U_vib
        G = H - T * S_vib
        
        return ThermoResult(T, pressure, E_pot, phonon_result.zpe, U_vib, S_vib, H, G)


def calculate_zpe(atoms: Atoms, calculator=None) -> float:
    return PhononAnalyzer(atoms, calculator).calculate_vibrations().zpe


def calculate_gibbs(atoms: Atoms, calculator=None, temperature: float = 298.15) -> float:
    return PhononAnalyzer(atoms, calculator).calculate_thermodynamics(temperature).G
