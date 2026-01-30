"""
Materials Project Integration

Materials Project API를 통한 구조 검색 및 표면 생성
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

try:
    from mp_api.client import MPRester
    HAS_MP_API = True
except ImportError:
    HAS_MP_API = False

from ase import Atoms
from ase.io import write
from ase.build import surface


@dataclass
class MPConfig:
    """Materials Project 설정"""
    api_key: Optional[str] = None
    endpoint: str = "https://api.materialsproject.org"
    
    def __post_init__(self):
        # 환경 변수에서 API 키 가져오기
        if self.api_key is None:
            self.api_key = os.environ.get("MP_API_KEY")


class MPIntegration:
    """Materials Project 연동 클래스"""
    
    def __init__(self, config: Optional[MPConfig] = None):
        """
        Args:
            config: MP 설정 (None이면 환경 변수에서 API 키 로드)
        """
        if not HAS_MP_API:
            raise ImportError(
                "mp-api가 필요합니다: pip install mp-api\n"
                "API 키는 https://materialsproject.org/api 에서 발급받으세요."
            )
            
        self.config = config or MPConfig()
        
        if not self.config.api_key:
            raise ValueError(
                "Materials Project API 키가 필요합니다.\n"
                "설정 방법:\n"
                "1. 환경 변수: export MP_API_KEY=your_key\n"
                "2. 또는: surfscreen config set mp-api-key your_key"
            )
            
        self.mpr = MPRester(self.config.api_key)
        
    def get_structure(self, material_id: str) -> Atoms:
        """Materials Project ID로 구조 가져오기
        
        Args:
            material_id: MP ID (예: "mp-30")
            
        Returns:
            ASE Atoms 객체
        """
        # mp- 접두사 추가
        if not material_id.startswith("mp-"):
            material_id = f"mp-{material_id}"
            
        doc = self.mpr.get_structure_by_material_id(material_id)
        
        # pymatgen Structure -> ASE Atoms 변환
        atoms = self._structure_to_atoms(doc)
        
        return atoms
    
    def _structure_to_atoms(self, structure) -> Atoms:
        """pymatgen Structure를 ASE Atoms로 변환"""
        from pymatgen.io.ase import AseAtomsAdaptor
        return AseAtomsAdaptor.get_atoms(structure)
    
    def create_surface(self, 
                       material_id: str,
                       miller: tuple = (1, 1, 1),
                       layers: int = 4,
                       vacuum: float = 15.0,
                       fix_layers: int = 2) -> Atoms:
        """Materials Project 구조에서 표면 생성
        
        Args:
            material_id: MP ID
            miller: 밀러 지수 (h, k, l)
            layers: 층 수
            vacuum: 진공 두께 (Å)
            fix_layers: 고정할 하층 수
            
        Returns:
            표면 Atoms 객체
        """
        bulk = self.get_structure(material_id)
        
        # ASE surface 함수 사용
        slab = surface(bulk, miller, layers, vacuum=vacuum)
        
        # 하층 고정
        if fix_layers > 0:
            positions = slab.get_positions()
            z_coords = positions[:, 2]
            z_min = z_coords.min()
            z_range = z_coords.max() - z_min
            layer_height = z_range / layers
            
            constraints = []
            from ase.constraints import FixAtoms
            
            fixed_indices = []
            for i, z in enumerate(z_coords):
                if z < z_min + fix_layers * layer_height:
                    fixed_indices.append(i)
                    
            if fixed_indices:
                slab.set_constraint(FixAtoms(indices=fixed_indices))
                
        return slab
    
    def search_materials(self, 
                         formula: Optional[str] = None,
                         elements: Optional[List[str]] = None,
                         spacegroup: Optional[Union[int, str]] = None,
                         crystal_system: Optional[str] = None,
                         is_stable: bool = True,
                         max_results: int = 20) -> List[Dict[str, Any]]:
        """재료 검색
        
        Args:
            formula: 화학식 (예: "Cu", "TiO2")
            elements: 포함할 원소 목록
            spacegroup: 공간군 (번호 또는 기호)
            crystal_system: 결정계 (cubic, hexagonal 등)
            is_stable: 안정한 구조만 검색
            max_results: 최대 결과 수
            
        Returns:
            검색 결과 목록
        """
        # 검색 파라미터 구성
        search_params = {}
        
        if formula:
            search_params["formula"] = formula
        if elements:
            search_params["elements"] = elements
        if is_stable:
            search_params["is_stable"] = True
            
        # 검색 실행
        docs = self.mpr.summary.search(
            **search_params,
            fields=["material_id", "formula_pretty", "spacegroup", 
                   "energy_above_hull", "band_gap", "density"],
            num_chunks=1
        )
        
        # 결과 필터링
        results = []
        for doc in docs[:max_results]:
            result = {
                "material_id": str(doc.material_id),
                "formula": doc.formula_pretty,
                "spacegroup": doc.symmetry.symbol if hasattr(doc, 'symmetry') else None,
                "energy_above_hull": doc.energy_above_hull,
                "band_gap": doc.band_gap,
                "density": doc.density
            }
            
            # 공간군 필터
            if spacegroup:
                sg = result.get("spacegroup")
                if sg and str(spacegroup) not in str(sg):
                    continue
                    
            # 결정계 필터
            if crystal_system:
                sg = result.get("spacegroup") or ""
                crystal_sys_map = {
                    "cubic": ["Pm-3m", "Fm-3m", "Im-3m", "Fd-3m", "Pa-3"],
                    "hexagonal": ["P6", "P63", "R3", "R-3"],
                    "tetragonal": ["P4", "I4", "P42"],
                    "orthorhombic": ["Pnma", "Cmcm", "Pbca"],
                    "monoclinic": ["P21", "C2"],
                    "triclinic": ["P1", "P-1"],
                }
                valid_sgs = crystal_sys_map.get(crystal_system.lower(), [])
                if not any(v in str(sg) for v in valid_sgs):
                    continue
                
            results.append(result)
            
        return results
    
    def get_similar_structures(self, material_id: str, max_results: int = 10) -> List[Dict]:
        """유사 구조 검색
        
        Args:
            material_id: 기준 MP ID
            max_results: 최대 결과 수
            
        Returns:
            유사 구조 목록
        """
        # 기준 구조 정보 가져오기
        base = self.mpr.summary.get_data_by_id(material_id)
        
        if not base:
            return []
            
        # 같은 화학식으로 검색
        return self.search_materials(
            formula=base.formula_pretty,
            max_results=max_results
        )


# 편의 함수들
def mp_get_structure(material_id: str, api_key: Optional[str] = None) -> Atoms:
    """MP ID로 구조 가져오기"""
    config = MPConfig(api_key=api_key) if api_key else None
    return MPIntegration(config).get_structure(material_id)


def mp_create_surface(material_id: str, 
                      miller: tuple = (1, 1, 1),
                      layers: int = 4,
                      vacuum: float = 15.0,
                      api_key: Optional[str] = None) -> Atoms:
    """MP ID로 표면 생성"""
    config = MPConfig(api_key=api_key) if api_key else None
    return MPIntegration(config).create_surface(material_id, miller, layers, vacuum)


def mp_search_materials(formula: str, 
                        max_results: int = 20,
                        api_key: Optional[str] = None) -> List[Dict]:
    """재료 검색"""
    config = MPConfig(api_key=api_key) if api_key else None
    return MPIntegration(config).search_materials(formula=formula, max_results=max_results)
