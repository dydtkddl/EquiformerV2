"""
AdsorptionSystem: 표면-분자 흡착 시스템

표면에 분자를 배치하고 최적화하는 통합 클래스
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import itertools

import numpy as np
from ase import Atoms
from ase.io import write
from ase.constraints import FixAtoms

if TYPE_CHECKING:
    from surfscreen.surface.builder import Surface
    from surfscreen.molecule.builder import Molecule
    from surfscreen.calculator.base import Calculator
    from surfscreen.surface.sites import AdsorptionSite


@dataclass
class AdsorptionResult:
    """흡착 계산 결과"""
    config_name: str
    atoms: Atoms
    site_idx: int
    site_type: str
    rotation: float
    center_atom: int
    initial_energy: float
    final_energy: float
    adsorption_energy: float
    steps: int
    converged: bool
    
    def save(self, path: str, format: str = "xyz"):
        write(path, self.atoms, format=format)


class AdsorptionSystem:
    """표면-분자 흡착 시스템
    
    표면에 분자를 다양한 위치/방향으로 배치하고 최적화
    
    Examples:
        from surfscreen import SurfaceBuilder, MoleculeBuilder
        from surfscreen.adsorption import AdsorptionSystem
        from surfscreen.calculator import CalculatorFactory
        
        surface = SurfaceBuilder.from_element("Cu", (1,1,1), layers=4)
        molecule = MoleculeBuilder.from_smiles("CCO")
        
        system = AdsorptionSystem(surface, molecule)
        configs = system.generate_configurations()
        
        calc = CalculatorFactory.create("mace")
        results = system.optimize_all(calc)
    """
    
    def __init__(self,
                 surface: "Surface",
                 molecule: "Molecule"):
        """
        Args:
            surface: Surface 객체
            molecule: Molecule 객체
        """
        self.surface = surface
        self.molecule = molecule
        
        # 에너지 참조값
        self._e_surface: Optional[float] = None
        self._e_molecule: Optional[float] = None
        
        # 생성된 구성
        self.configurations: List[Atoms] = []
        self.config_info: List[dict] = []
    
    def generate_configurations(self,
                               sites: Union[str, List["AdsorptionSite"]] = "auto",
                               rotations: List[float] = [0, 45, 90, 135],
                               heights: List[float] = [2.0],
                               center_atoms: Optional[List[int]] = None,
                               max_configs: int = 100) -> List[Atoms]:
        """흡착 구성 생성
        
        Args:
            sites: 흡착 사이트 ("auto" 또는 AdsorptionSite 목록)
            rotations: z축 회전 각도 (degrees)
            heights: 표면으로부터 높이 (Å)
            center_atoms: 분자 중심 원자 인덱스 (None=자동)
            max_configs: 최대 구성 수
            
        Returns:
            Atoms 목록
        """
        from surfscreen.surface.sites import SiteDetector
        from surfscreen.molecule.builder import MoleculeAnalyzer
        
        # 사이트 감지
        if sites == "auto":
            detector = SiteDetector(self.surface)
            sites = detector.detect_all()
        
        # 분자 중심 원자 감지
        if center_atoms is None:
            center_atoms = MoleculeAnalyzer.get_adsorption_centers(self.molecule)
            if not center_atoms:
                # 기본값: 첫 번째 무거운 원자
                heavy = [i for i, s in enumerate(self.molecule.symbols) 
                        if s not in ['H']]
                center_atoms = [heavy[0]] if heavy else [0]
        
        self.configurations = []
        self.config_info = []
        
        # 모든 조합 생성
        count = 0
        for site_idx, site in enumerate(sites):
            for rot in rotations:
                for height in heights:
                    for center in center_atoms:
                        if count >= max_configs:
                            break
                        
                        config = self._place_molecule(
                            site.position[:2],
                            site.position[2] + height - self.surface.atoms.positions[:, 2].max(),
                            rotation=rot,
                            center_atom=center
                        )
                        
                        # 충돌 체크
                        if not self._check_overlap(config):
                            self.configurations.append(config)
                            self.config_info.append({
                                'site_idx': site_idx,
                                'site_type': site.site_type.value,
                                'rotation': rot,
                                'height': height,
                                'center_atom': center
                            })
                            count += 1
        
        return self.configurations
    
    def _place_molecule(self,
                        xy: Tuple[float, float],
                        height: float,
                        rotation: float,
                        center_atom: int) -> Atoms:
        """분자를 표면에 배치"""
        # 표면 복사
        surface = self.surface.atoms.copy()
        molecule = self.molecule.atoms.copy()
        
        # 분자 중심을 center_atom으로 이동
        mol_center = molecule.positions[center_atom]
        molecule.positions -= mol_center
        
        # z축 회전
        angle_rad = np.radians(rotation)
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        rot_matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])
        molecule.positions = molecule.positions @ rot_matrix.T
        
        # 흡착 위치로 이동
        z_surface = surface.positions[:, 2].max()
        molecule.positions += np.array([xy[0], xy[1], z_surface + height])
        
        # 결합
        system = surface + molecule
        
        # 표면 원자 고정 유지
        if self.surface.fixed_atoms:
            system.set_constraint(FixAtoms(indices=self.surface.fixed_atoms))
        
        return system
    
    def _check_overlap(self, config: Atoms, min_distance: float = 1.5) -> bool:
        """원자 충돌 체크
        
        Returns:
            True if overlap exists
        """
        n_surf = self.surface.n_atoms
        n_mol = self.molecule.n_atoms
        
        surf_pos = config.positions[:n_surf]
        mol_pos = config.positions[n_surf:n_surf + n_mol]
        
        for mp in mol_pos:
            for sp in surf_pos:
                if np.linalg.norm(mp - sp) < min_distance:
                    return True
        return False
    
    def optimize_all(self,
                    calculator: "Calculator",
                    fmax: float = 0.05,
                    steps: int = 500,
                    parallel: bool = False,
                    n_jobs: int = 4,
                    output_dir: Optional[str] = None,
                    progress: bool = True) -> List[AdsorptionResult]:
        """모든 구성 최적화
        
        Args:
            calculator: Calculator 인스턴스
            fmax: 최대 힘 수렴 기준
            steps: 최대 스텝 수
            parallel: 병렬 처리 여부
            n_jobs: 병렬 작업 수
            output_dir: 출력 디렉토리
            progress: 진행률 표시
            
        Returns:
            AdsorptionResult 목록
        """
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # 참조 에너지 계산
        if self._e_surface is None:
            self._e_surface = calculator.get_energy(self.surface.atoms)
        if self._e_molecule is None:
            self._e_molecule = calculator.get_energy(self.molecule.atoms)
        
        results = []
        n_configs = len(self.configurations)
        
        for i, (config, info) in enumerate(zip(self.configurations, self.config_info)):
            name = f"site{info['site_idx']}_rot{int(info['rotation'])}"
            
            if progress:
                print(f"\n=== {name} ({i+1}/{n_configs}) ===")
                print(f"  Site: {info['site_type']}, Rotation: {info['rotation']}°")
            
            try:
                # 초기 에너지
                initial_e = calculator.get_energy(config)
                
                # 최적화
                traj_file = str(output_dir / f"{name}.traj") if output_dir else None
                opt_result = calculator.optimize(
                    config,
                    fmax=fmax,
                    steps=steps,
                    trajectory=traj_file
                )
                
                # 흡착 에너지
                e_ads = opt_result.final_energy - self._e_surface - self._e_molecule
                
                if progress:
                    print(f"  Initial E: {initial_e:.4f} eV")
                    print(f"  Final E: {opt_result.final_energy:.4f} eV ({opt_result.steps} steps)")
                    print(f"  E_ads: {e_ads:.4f} eV")
                
                result = AdsorptionResult(
                    config_name=name,
                    atoms=opt_result.atoms,
                    site_idx=info['site_idx'],
                    site_type=info['site_type'],
                    rotation=info['rotation'],
                    center_atom=info['center_atom'],
                    initial_energy=initial_e,
                    final_energy=opt_result.final_energy,
                    adsorption_energy=e_ads,
                    steps=opt_result.steps,
                    converged=opt_result.converged
                )
                
                if output_dir:
                    result.save(str(output_dir / f"{name}.xyz"))
                
                results.append(result)
                
            except Exception as e:
                if progress:
                    print(f"  Error: {e}")
        
        # 결과 정렬 (흡착 에너지 기준)
        results.sort(key=lambda x: x.adsorption_energy)
        
        return results
    
    def get_best_result(self, results: List[AdsorptionResult]) -> AdsorptionResult:
        """가장 안정적인 구성 반환"""
        return min(results, key=lambda x: x.adsorption_energy)
    
    def export_results(self,
                       results: List[AdsorptionResult],
                       output_path: str,
                       format: str = "csv"):
        """결과 내보내기"""
        import pandas as pd
        
        data = []
        for r in results:
            data.append({
                'name': r.config_name,
                'site_idx': r.site_idx,
                'site_type': r.site_type,
                'rotation': r.rotation,
                'initial_energy': r.initial_energy,
                'final_energy': r.final_energy,
                'e_ads': r.adsorption_energy,
                'steps': r.steps,
                'converged': r.converged
            })
        
        df = pd.DataFrame(data)
        
        if format == "csv":
            df.to_csv(output_path, index=False)
        elif format == "json":
            df.to_json(output_path, orient="records", indent=2)
        else:
            raise ValueError(f"Unknown format: {format}")
