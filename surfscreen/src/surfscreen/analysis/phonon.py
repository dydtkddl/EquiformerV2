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
            
    def calculate_vibrations(self, indices: Optional[List[int]] = None) -> PhononResult:
        """진동 주파수 계산"""
        from ase.vibrations import Vibrations
        
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
        vib.clean()
        
        return PhononResult(freq_cm1, freq_meV, zpe, n_imaginary)
    
    def calculate_thermodynamics(self, temperature: float = 298.15, 
                                  pressure: float = 1.0,
                                  phonon_result: Optional[PhononResult] = None) -> ThermoResult:
        """열역학량 계산"""
        if phonon_result is None:
            phonon_result = self.calculate_vibrations()
            
        E_pot = self.atoms.get_potential_energy() if self.atoms.calc else 0.0
        freqs_eV = phonon_result.frequencies_cm1 * 1.23984e-4
        
        T = temperature
        beta = 1.0 / (KB * T) if T > 0 else float('inf')
        U_vib = S_vib = 0.0
        
        for omega in freqs_eV:
            if omega > 0 and T > 0:
                x = omega * beta
                if x < 700:
                    n_bose = 1.0 / (np.exp(x) - 1)
                    U_vib += omega * (0.5 + n_bose)
                    S_vib += omega * n_bose / T - KB * np.log(1 - np.exp(-x))
                else:
                    U_vib += omega * 0.5
                    
        H = E_pot + U_vib
        G = H - T * S_vib
        
        return ThermoResult(T, pressure, E_pot, phonon_result.zpe, U_vib, S_vib, H, G)


def calculate_zpe(atoms: Atoms, calculator=None) -> float:
    return PhononAnalyzer(atoms, calculator).calculate_vibrations().zpe


def calculate_gibbs(atoms: Atoms, calculator=None, temperature: float = 298.15) -> float:
    return PhononAnalyzer(atoms, calculator).calculate_thermodynamics(temperature).G
