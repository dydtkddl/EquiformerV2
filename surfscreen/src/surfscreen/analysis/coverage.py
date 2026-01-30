"""
Coverage Analysis Module

표면 피복도 (Coverage) 분석
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ase import Atoms


@dataclass
class CoverageResult:
    """피복도 분석 결과"""
    surface_area: float  # Å²
    n_adsorbates: int
    molecular_area: float  # Å² per molecule
    coverage_abs: float  # molecules/Å²
    coverage_ml: float  # monolayer fraction


class CoverageAnalyzer:
    """피복도 분석"""
    
    def __init__(self, atoms: Atoms, n_surface_atoms: int = 0):
        self.atoms = atoms
        self.n_surface = n_surface_atoms or self._detect_surface_atoms()
        
    def _detect_surface_atoms(self) -> int:
        """표면 원자 수 자동 감지"""
        if not self.atoms.pbc.any():
            return 0
        positions = self.atoms.get_positions()
        z_coords = positions[:, 2]
        z_mean = np.mean(z_coords)
        return int(np.sum(z_coords > z_mean))
        
    def calculate_surface_area(self) -> float:
        """표면적 계산 (Å²)"""
        cell = self.atoms.get_cell()
        a = cell[0][:2]
        b = cell[1][:2]
        return abs(np.cross(a, b))
    
    def calculate_coverage(self, molecular_area: float = 10.0) -> CoverageResult:
        """피복도 계산
        
        Args:
            molecular_area: 분자당 점유 면적 (Å²)
        """
        surface_area = self.calculate_surface_area()
        n_adsorbates = len(self.atoms) - self.n_surface
        
        if n_adsorbates < 0:
            n_adsorbates = 0
            
        coverage_abs = n_adsorbates / surface_area if surface_area > 0 else 0
        max_coverage = surface_area / molecular_area
        coverage_ml = n_adsorbates / max_coverage if max_coverage > 0 else 0
        
        return CoverageResult(
            surface_area=surface_area,
            n_adsorbates=n_adsorbates,
            molecular_area=molecular_area,
            coverage_abs=coverage_abs,
            coverage_ml=coverage_ml
        )


def calculate_coverage(atoms: Atoms, n_surface: int, molecular_area: float = 10.0) -> Dict:
    """편의 함수"""
    result = CoverageAnalyzer(atoms, n_surface).calculate_coverage(molecular_area)
    return {
        "surface_area_A2": result.surface_area,
        "n_adsorbates": result.n_adsorbates,
        "coverage_per_A2": result.coverage_abs,
        "coverage_ML": result.coverage_ml
    }
