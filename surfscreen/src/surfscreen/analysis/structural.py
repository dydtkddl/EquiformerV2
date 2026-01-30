"""
Structural Analysis Module

흡착 구조 분석 도구
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from ase import Atoms
from ase.io import read
from scipy.spatial.distance import cdist


@dataclass
class StructuralAnalysisResult:
    """구조 분석 결과"""
    config_name: str
    adsorption_height: float  # Å
    min_surface_distance: float  # Å
    tilt_angle: float  # degrees
    bond_changes: Dict[str, float]  # bond_type -> change in Å
    coordination: Dict[str, int]  # atom -> coordination number
    site_type: str
    
    def to_dict(self) -> dict:
        return {
            "config_name": self.config_name,
            "adsorption_height_A": self.adsorption_height,
            "min_surface_distance_A": self.min_surface_distance,
            "tilt_angle_deg": self.tilt_angle,
            "bond_changes": self.bond_changes,
            "coordination": self.coordination,
            "site_type": self.site_type
        }


class StructuralAnalyzer:
    """구조 분석기"""
    
    def __init__(self, atoms: Atoms, n_surface_atoms: int = 0):
        """
        Args:
            atoms: 흡착 시스템 Atoms 객체
            n_surface_atoms: 표면 원자 수 (0이면 자동 감지)
        """
        self.atoms = atoms
        self.n_surface_atoms = n_surface_atoms
        
        if n_surface_atoms == 0:
            self._detect_surface_boundary()
    
    def _detect_surface_boundary(self):
        """표면/분자 경계 자동 감지"""
        z_coords = self.atoms.positions[:, 2]
        
        # Z 좌표 분포에서 gap 찾기
        z_sorted = np.sort(z_coords)
        z_diff = np.diff(z_sorted)
        
        # 가장 큰 gap이 표면-분자 경계
        if len(z_diff) > 0:
            gap_idx = np.argmax(z_diff)
            z_threshold = (z_sorted[gap_idx] + z_sorted[gap_idx + 1]) / 2
            self.n_surface_atoms = np.sum(z_coords < z_threshold)
        else:
            self.n_surface_atoms = len(self.atoms)
    
    def get_surface_atoms(self) -> Atoms:
        """표면 원자 반환"""
        return self.atoms[:self.n_surface_atoms]
    
    def get_molecule_atoms(self) -> Atoms:
        """분자 원자 반환"""
        return self.atoms[self.n_surface_atoms:]
    
    def calculate_adsorption_height(self) -> float:
        """흡착 높이 계산 (분자 최저점 - 표면 최고점)"""
        surface = self.get_surface_atoms()
        molecule = self.get_molecule_atoms()
        
        if len(molecule) == 0:
            return 0.0
            
        surface_z_max = surface.positions[:, 2].max()
        molecule_z_min = molecule.positions[:, 2].min()
        
        return molecule_z_min - surface_z_max
    
    def calculate_min_distance(self) -> float:
        """분자-표면 최소 거리"""
        surface = self.get_surface_atoms()
        molecule = self.get_molecule_atoms()
        
        if len(molecule) == 0 or len(surface) == 0:
            return 0.0
            
        distances = cdist(molecule.positions, surface.positions)
        return distances.min()
    
    def calculate_tilt_angle(self) -> float:
        """분자 기울기 각도 (표면에 대해)
        
        분자의 주축과 표면(xy 평면)이 이루는 각도
        """
        molecule = self.get_molecule_atoms()
        
        if len(molecule) < 2:
            return 0.0
            
        positions = molecule.positions
        
        # 분자의 주축 계산 (PCA)
        centered = positions - positions.mean(axis=0)
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        
        # 가장 큰 고유값에 해당하는 축
        main_axis = eigenvectors[:, np.argmax(eigenvalues)]
        
        # xy 평면과의 각도
        z_component = abs(main_axis[2])
        angle = np.degrees(np.arcsin(z_component))
        
        return angle
    
    def calculate_bond_lengths(self) -> Dict[Tuple[str, str], List[float]]:
        """분자 내 결합 길이"""
        molecule = self.get_molecule_atoms()
        
        if len(molecule) < 2:
            return {}
            
        symbols = molecule.get_chemical_symbols()
        positions = molecule.positions
        
        bonds = {}
        cutoff = 1.8  # Å
        
        for i in range(len(molecule)):
            for j in range(i + 1, len(molecule)):
                dist = np.linalg.norm(positions[i] - positions[j])
                if dist < cutoff:
                    bond_type = tuple(sorted([symbols[i], symbols[j]]))
                    if bond_type not in bonds:
                        bonds[bond_type] = []
                    bonds[bond_type].append(dist)
                    
        return bonds
    
    def calculate_coordination(self, cutoff: float = 3.0) -> Dict[int, int]:
        """흡착 원자의 배위수
        
        Args:
            cutoff: 배위 거리 cutoff (Å)
            
        Returns:
            분자 원자 인덱스 -> 표면 원자 배위수
        """
        surface = self.get_surface_atoms()
        molecule = self.get_molecule_atoms()
        
        if len(molecule) == 0 or len(surface) == 0:
            return {}
            
        distances = cdist(molecule.positions, surface.positions)
        
        coordination = {}
        for i in range(len(molecule)):
            n_coord = np.sum(distances[i] < cutoff)
            if n_coord > 0:
                coordination[i + self.n_surface_atoms] = n_coord
                
        return coordination
    
    def classify_site_type(self) -> str:
        """흡착 사이트 유형 분류
        
        Returns:
            "top", "bridge", "hollow", 또는 "unknown"
        """
        coordination = self.calculate_coordination(cutoff=2.8)
        
        if not coordination:
            return "unknown"
            
        # 가장 가까운 원자의 배위수로 판단
        max_coord = max(coordination.values())
        
        if max_coord == 1:
            return "top"
        elif max_coord == 2:
            return "bridge"
        elif max_coord >= 3:
            return "hollow"
        else:
            return "unknown"
    
    def analyze(self, config_name: str = "", 
                reference_molecule: Optional[Atoms] = None) -> StructuralAnalysisResult:
        """전체 구조 분석
        
        Args:
            config_name: 구성 이름
            reference_molecule: 비교용 기준 분자 (결합 변화 계산용)
            
        Returns:
            StructuralAnalysisResult
        """
        height = self.calculate_adsorption_height()
        min_dist = self.calculate_min_distance()
        tilt = self.calculate_tilt_angle()
        site_type = self.classify_site_type()
        coordination = self.calculate_coordination()
        
        # 결합 변화 계산
        bond_changes = {}
        if reference_molecule is not None:
            ref_analyzer = StructuralAnalyzer(reference_molecule, n_surface_atoms=0)
            ref_bonds = ref_analyzer.calculate_bond_lengths()
            current_bonds = self.calculate_bond_lengths()
            
            for bond_type, ref_lengths in ref_bonds.items():
                if bond_type in current_bonds:
                    ref_avg = np.mean(ref_lengths)
                    cur_avg = np.mean(current_bonds[bond_type])
                    bond_key = f"{bond_type[0]}-{bond_type[1]}"
                    bond_changes[bond_key] = cur_avg - ref_avg
        
        return StructuralAnalysisResult(
            config_name=config_name,
            adsorption_height=height,
            min_surface_distance=min_dist,
            tilt_angle=tilt,
            bond_changes=bond_changes,
            coordination={str(k): v for k, v in coordination.items()},
            site_type=site_type
        )


def analyze_screening_results(results_dir: str, 
                               n_surface_atoms: int = 0) -> List[StructuralAnalysisResult]:
    """스크리닝 결과 디렉토리 분석
    
    Args:
        results_dir: 결과 디렉토리 경로
        n_surface_atoms: 표면 원자 수
        
    Returns:
        분석 결과 리스트
    """
    results_path = Path(results_dir)
    results = []
    
    # XYZ 파일들 찾기
    xyz_files = list(results_path.glob("*.xyz")) + list(results_path.glob("*.extxyz"))
    
    for xyz_file in xyz_files:
        try:
            atoms = read(str(xyz_file))
            analyzer = StructuralAnalyzer(atoms, n_surface_atoms)
            result = analyzer.analyze(config_name=xyz_file.stem)
            results.append(result)
        except Exception as e:
            print(f"Warning: Failed to analyze {xyz_file}: {e}")
            
    return results
