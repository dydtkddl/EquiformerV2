"""
SurfaceBuilder: 표면 생성 및 관리

다양한 소스에서 표면 슬랩을 생성하고 관리
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass, field

import numpy as np
from ase import Atoms
from ase.io import read, write
from ase.constraints import FixAtoms
from ase.build import fcc111, bcc110, hcp0001, surface as ase_surface

from surfscreen.logging_utils import surface_logger as logger

try:
    from pymatgen.core import Structure
    from pymatgen.core.surface import SlabGenerator
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    from pymatgen.ext.matproj import MPRester
    HAS_PYMATGEN = True
except ImportError:
    HAS_PYMATGEN = False


# 원소별 격자 상수 (Å)
LATTICE_CONSTANTS = {
    # FCC metals
    "Cu": 3.615, "Ag": 3.893, "Au": 4.078, "Pd": 3.891, "Pt": 3.924,
    "Ni": 3.524, "Al": 4.050, "Pb": 4.951, "Rh": 3.803, "Ir": 3.839,
    # BCC metals
    "Fe": 2.867, "W": 3.165, "Mo": 3.147, "V": 3.024, "Cr": 2.884,
    "Nb": 3.303, "Ta": 3.303,
    # HCP metals
    "Ti": 2.951, "Zn": 2.665, "Co": 2.507, "Ru": 2.706, "Zr": 3.232,
}

# 결정 구조
CRYSTAL_STRUCTURES = {
    "Cu": "fcc", "Ag": "fcc", "Au": "fcc", "Pd": "fcc", "Pt": "fcc",
    "Ni": "fcc", "Al": "fcc", "Pb": "fcc", "Rh": "fcc", "Ir": "fcc",
    "Fe": "bcc", "W": "bcc", "Mo": "bcc", "V": "bcc", "Cr": "bcc",
    "Nb": "bcc", "Ta": "bcc",
    "Ti": "hcp", "Zn": "hcp", "Co": "hcp", "Ru": "hcp", "Zr": "hcp",
}


@dataclass
class Surface:
    """표면 데이터 클래스"""
    atoms: Atoms
    name: str = ""
    miller_index: Tuple[int, int, int] = (1, 1, 1)
    material: str = ""
    layers: int = 0
    vacuum: float = 0.0
    fixed_atoms: List[int] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    
    @property
    def n_atoms(self) -> int:
        return len(self.atoms)
    
    @property
    def cell(self) -> np.ndarray:
        return self.atoms.get_cell().array
    
    @property
    def area(self) -> float:
        """표면적 (Å²)"""
        a, b = self.cell[:2, :2]
        return np.linalg.norm(np.cross(a, b))
    
    def copy(self) -> "Surface":
        return Surface(
            atoms=self.atoms.copy(),
            name=self.name,
            miller_index=self.miller_index,
            material=self.material,
            layers=self.layers,
            vacuum=self.vacuum,
            fixed_atoms=self.fixed_atoms.copy(),
            properties=self.properties.copy()
        )
    
    def save(self, path: str, format: Optional[str] = None) -> None:
        """표면을 파일로 저장
        
        지원 형식: extxyz, cif, xyz, pdb, vasp, mol2 등 (ASE 지원 형식)
        format이 None이면 파일 확장자에서 자동 감지
        """
        if format is None:
            # 파일 확장자에서 format 추출
            ext = Path(path).suffix.lower().lstrip('.')
            # ASE format 매핑
            format_map = {
                'extxyz': 'extxyz',
                'xyz': 'xyz',
                'cif': 'cif',
                'pdb': 'proteindatabank',
                'mol2': 'mol2',
                'vasp': 'vasp',
                'poscar': 'vasp',
                'contcar': 'vasp',
                'car': 'dmol-car',
                'gen': 'dftb',
                'json': 'json',
            }
            format = format_map.get(ext, ext)  # 매핑 없으면 확장자 그대로 사용
        
        write(path, self.atoms, format=format)
        
    def get_surface_atoms(self) -> List[int]:
        """표면 원자 인덱스 반환"""
        positions = self.atoms.get_positions()
        z_coords = positions[:, 2]
        z_max = z_coords.max()
        
        # 상위 레이어 (z_max - 1.5 Å 이상)
        surface_idx = np.where(z_coords > z_max - 1.5)[0]
        return list(surface_idx)
    
    def get_bottom_atoms(self) -> List[int]:
        """하단 원자 인덱스 반환"""
        positions = self.atoms.get_positions()
        z_coords = positions[:, 2]
        z_min = z_coords.min()
        
        bottom_idx = np.where(z_coords < z_min + 1.5)[0]
        return list(bottom_idx)


class SurfaceBuilder:
    """표면 생성기
    
    다양한 소스에서 표면 슬랩 생성:
    - 원소 기호 (FCC/BCC/HCP 자동 감지)
    - 벌크 구조 파일
    - Materials Project
    
    Examples:
        # 원소에서 생성
        surface = SurfaceBuilder.from_element(
            "Cu", miller_index=(1,1,1), layers=4
        )
        
        # 벌크에서 생성
        surface = SurfaceBuilder.from_bulk(
            "bulk.cif", miller_index=(1,1,0)
        )
        
        # Materials Project에서
        surface = SurfaceBuilder.from_mp(
            "mp-30", miller_index=(1,1,1)
        )
    """
    
    @classmethod
    def from_element(cls,
                     element: str,
                     miller_index: Tuple[int, int, int] = (1, 1, 1),
                     layers: int = 4,
                     vacuum: float = 15.0,
                     supercell: Tuple[int, int, int] = (1, 1, 1),
                     fixed_layers: int = 2,
                     orthogonal: bool = True) -> Surface:
        """원소 기호에서 표면 생성
        
        Args:
            element: 원소 기호 (Cu, Au, Pt 등)
            miller_index: 밀러 지수
            layers: 레이어 수
            vacuum: 진공 두께 (Å)
            supercell: 슈퍼셀 (a, b, c)
            fixed_layers: 고정할 하단 레이어 수
            orthogonal: 직교 셀 사용
            
        Returns:
            Surface 객체
        """
        if element not in LATTICE_CONSTANTS:
            raise ValueError(f"Unknown element: {element}. "
                           f"Available: {list(LATTICE_CONSTANTS.keys())}")
        
        a = LATTICE_CONSTANTS[element]
        structure = CRYSTAL_STRUCTURES[element]
        
        # ASE 빌더 사용 (일반적인 표면)
        if structure == "fcc" and miller_index == (1, 1, 1):
            atoms = fcc111(element, size=(supercell[0], supercell[1], layers),
                          a=a, vacuum=vacuum, orthogonal=False)
        elif structure == "bcc" and miller_index == (1, 1, 0):
            atoms = bcc110(element, size=(supercell[0], supercell[1], layers),
                          a=a, vacuum=vacuum, orthogonal=orthogonal)
        elif structure == "hcp" and miller_index in [(0, 0, 0, 1), (0, 0, 1)]:
            # HCP (0001) 표면: 4-index (h,k,i,l) 또는 3-index (h,k,l) 모두 지원
            atoms = hcp0001(element, size=(supercell[0], supercell[1], layers),
                           a=a, vacuum=vacuum, orthogonal=orthogonal)
        else:
            # pymatgen 사용 - 4-index를 3-index로 변환
            if len(miller_index) == 4:
                # 4-index (h,k,i,l) → 3-index (h,k,l) 변환
                h, k, i, l = miller_index
                miller_index = (h, k, l)
            atoms = cls._build_with_pymatgen(
                element, structure, a, miller_index, 
                layers, vacuum, supercell
            )
        
        # 하단 레이어 고정
        fixed_atoms = []
        if fixed_layers > 0:
            positions = atoms.get_positions()
            z_coords = positions[:, 2]
            z_sorted = np.sort(np.unique(np.round(z_coords, 2)))
            
            # 하단 레이어
            z_threshold = z_sorted[min(fixed_layers, len(z_sorted)) - 1] + 0.1
            fixed_atoms = list(np.where(z_coords < z_threshold)[0])
            
            atoms.set_constraint(FixAtoms(indices=fixed_atoms))
        
        miller_str = "".join(map(str, miller_index))
        name = f"{element}({miller_str})_{supercell[0]}x{supercell[1]}"
        
        return Surface(
            atoms=atoms,
            name=name,
            miller_index=miller_index,
            material=element,
            layers=layers,
            vacuum=vacuum,
            fixed_atoms=fixed_atoms
        )
    
    @classmethod
    def _build_with_pymatgen(cls,
                             element: str,
                             structure: str,
                             a: float,
                             miller_index: Tuple[int, int, int],
                             layers: int,
                             vacuum: float,
                             supercell: Tuple[int, int, int]) -> Atoms:
        """pymatgen으로 일반 표면 생성"""
        if not HAS_PYMATGEN:
            raise ImportError("pymatgen required for this miller index. "
                            "Install with: pip install pymatgen")
        
        # 벌크 구조 생성
        if structure == "fcc":
            struct = Structure.from_spacegroup(
                "Fm-3m", [[a, 0, 0], [0, a, 0], [0, 0, a]],
                [element], [[0, 0, 0]]
            )
        elif structure == "bcc":
            struct = Structure.from_spacegroup(
                "Im-3m", [[a, 0, 0], [0, a, 0], [0, 0, a]],
                [element], [[0, 0, 0]]
            )
        elif structure == "hcp":
            # HCP 구조: c/a 비율 ≈ 1.633 (이상적)
            # 실제 c/a는 원소에 따라 다름
            c_over_a = {
                "Ti": 1.587, "Zn": 1.856, "Co": 1.622, 
                "Ru": 1.582, "Zr": 1.593, "Mg": 1.624
            }
            c = a * c_over_a.get(element, 1.633)
            
            # HCP 격자: P6_3/mmc (space group 194)
            struct = Structure.from_spacegroup(
                "P6_3/mmc",
                [[a, 0, 0], 
                 [-a/2, a*np.sqrt(3)/2, 0], 
                 [0, 0, c]],
                [element, element], 
                [[1/3, 2/3, 1/4], [2/3, 1/3, 3/4]]
            )
        else:
            raise ValueError(f"Unsupported structure type: {structure}")
        
        # 슬랩 생성
        slabgen = SlabGenerator(
            struct,
            miller_index,
            min_slab_size=layers * 2,  # Å
            min_vacuum_size=vacuum,
            center_slab=True
        )
        
        slabs = slabgen.get_slabs()
        if not slabs:
            raise ValueError(f"Could not generate slab for {miller_index}")
        
        slab = slabs[0]
        
        # 슈퍼셀
        slab.make_supercell([supercell[0], supercell[1], 1])
        
        # ASE Atoms로 변환
        return cls._pymatgen_to_ase(slab)
    
    @staticmethod
    def _pymatgen_to_ase(structure: "Structure") -> Atoms:
        """pymatgen Structure를 ASE Atoms로 변환"""
        symbols = [site.specie.symbol for site in structure]
        positions = structure.cart_coords
        cell = structure.lattice.matrix
        pbc = [True, True, True]
        
        return Atoms(symbols=symbols, positions=positions, cell=cell, pbc=pbc)
    
    @classmethod
    def from_bulk(cls,
                  structure: Union[str, Atoms],
                  miller_index: Tuple[int, int, int],
                  layers: int = 4,
                  vacuum: float = 15.0,
                  supercell: Tuple[int, int, int] = (1, 1, 1),
                  fixed_layers: int = 2) -> Surface:
        """벌크 구조에서 표면 생성
        
        Args:
            structure: 벌크 구조 파일 경로 또는 ASE Atoms
            miller_index: 밀러 지수
            layers: 레이어 수
            vacuum: 진공 두께
            supercell: 슈퍼셀
            fixed_layers: 고정 레이어 수
            
        Returns:
            Surface 객체
        """
        if not HAS_PYMATGEN:
            raise ImportError("pymatgen required. Install with: pip install pymatgen")
        
        # 구조 로드
        if isinstance(structure, str):
            pmg_struct = Structure.from_file(structure)
            name = Path(structure).stem
        else:
            # ASE to pymatgen
            from pymatgen.io.ase import AseAtomsAdaptor
            pmg_struct = AseAtomsAdaptor.get_structure(structure)
            name = structure.get_chemical_formula()
        
        # 슬랩 생성
        slabgen = SlabGenerator(
            pmg_struct,
            miller_index,
            min_slab_size=layers * 2.5,
            min_vacuum_size=vacuum,
            center_slab=True
        )
        
        slabs = slabgen.get_slabs()
        if not slabs:
            raise ValueError(f"Could not generate slab for {miller_index}")
        
        slab = slabs[0]
        slab.make_supercell([supercell[0], supercell[1], 1])
        
        atoms = cls._pymatgen_to_ase(slab)
        
        # 하단 고정
        fixed_atoms = []
        if fixed_layers > 0:
            positions = atoms.get_positions()
            z_coords = positions[:, 2]
            z_sorted = np.sort(np.unique(np.round(z_coords, 2)))
            z_threshold = z_sorted[min(fixed_layers, len(z_sorted)) - 1] + 0.1
            fixed_atoms = list(np.where(z_coords < z_threshold)[0])
            atoms.set_constraint(FixAtoms(indices=fixed_atoms))
        
        miller_str = "".join(map(str, miller_index))
        
        return Surface(
            atoms=atoms,
            name=f"{name}({miller_str})",
            miller_index=miller_index,
            material=name,
            layers=layers,
            vacuum=vacuum,
            fixed_atoms=fixed_atoms
        )
    
    @classmethod
    def from_mp(cls,
                mp_id: str,
                miller_index: Tuple[int, int, int],
                api_key: Optional[str] = None,
                **kwargs) -> Surface:
        """Materials Project에서 표면 생성
        
        Args:
            mp_id: Materials Project ID (예: "mp-30")
            miller_index: 밀러 지수
            api_key: MP API 키 (환경변수 MP_API_KEY 사용 가능)
            **kwargs: from_bulk에 전달할 추가 인자
            
        Returns:
            Surface 객체
        """
        if not HAS_PYMATGEN:
            raise ImportError("pymatgen required. Install with: pip install pymatgen")
        
        import os
        api_key = api_key or os.environ.get("MP_API_KEY")
        
        with MPRester(api_key) as mpr:
            structure = mpr.get_structure_by_material_id(mp_id)
        
        return cls.from_bulk(
            cls._pymatgen_to_ase(structure),
            miller_index,
            **kwargs
        )
    
    @classmethod
    def from_file(cls,
                  path: str,
                  miller_index: Tuple[int, int, int] = (1, 1, 1),
                  name: str = "",
                  fixed_layers: int = 2) -> Surface:
        """파일에서 표면 읽기 (이미 슬랩인 경우)
        
        Args:
            path: 파일 경로
            miller_index: 밀러 지수
            name: 표면 이름
            fixed_layers: 고정할 하단 레이어 수 (기본: 2)
        """
        atoms = read(path)
        
        # cell이 없으면 원자 위치에서 자동 생성
        cell = atoms.get_cell()
        if not cell.any():
            positions = atoms.get_positions()
            x_min, y_min, z_min = positions.min(axis=0)
            x_max, y_max, z_max = positions.max(axis=0)
            
            # Cu nearest-neighbor distance ~2.55Å 기준으로 cell 경계 확장
            padding = 2.55 / 2  # 반경만큼 확장
            cell_a = x_max - x_min + 2 * padding
            cell_b = y_max - y_min + 2 * padding
            cell_c = z_max - z_min + 15.0  # vacuum 포함
            
            atoms.set_cell([cell_a, cell_b, cell_c])
            atoms.set_pbc([True, True, True])
            
            # 원점 이동 (원자가 cell 중앙에 오도록)
            atoms.positions[:, 0] -= x_min - padding
            atoms.positions[:, 1] -= y_min - padding
        
        # 하단 레이어 고정
        fixed_atoms = []
        if fixed_layers > 0:
            positions = atoms.get_positions()
            z_coords = positions[:, 2]
            z_sorted = np.sort(np.unique(np.round(z_coords, 2)))
            
            z_threshold = z_sorted[min(fixed_layers, len(z_sorted)) - 1] + 0.1
            fixed_atoms = list(np.where(z_coords < z_threshold)[0])
            
            atoms.set_constraint(FixAtoms(indices=fixed_atoms))
        
        return Surface(
            atoms=atoms,
            name=name or Path(path).stem,
            miller_index=miller_index,
            fixed_atoms=fixed_atoms
        )
    
    @classmethod
    def available_elements(cls) -> List[str]:
        """사용 가능한 원소 목록"""
        return list(LATTICE_CONSTANTS.keys())
    
    @classmethod
    def get_common_surfaces(cls) -> dict:
        """일반적인 표면 조합"""
        return {
            "fcc": [(1, 1, 1), (1, 0, 0), (1, 1, 0)],
            "bcc": [(1, 1, 0), (1, 0, 0), (1, 1, 1)],
            "hcp": [(0, 0, 0, 1), (1, 0, -1, 0)],
        }
