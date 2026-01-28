"""
MoleculeBuilder: 분자 생성 및 관리

다양한 소스에서 분자를 생성하고 조작하는 통합 인터페이스
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass, field

import numpy as np
from ase import Atoms
from ase.io import read, write

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False

from surfscreen.molecule.pubchem import PubChemFetcher
from surfscreen.molecule.conformers import ConformerGenerator


@dataclass
class FunctionalGroup:
    """작용기 정보"""
    name: str
    atoms: List[int]
    smarts: str


@dataclass
class Molecule:
    """분자 데이터 클래스"""
    atoms: Atoms
    name: str = ""
    smiles: str = ""
    formula: str = ""
    source: str = ""
    properties: dict = field(default_factory=dict)
    
    @property
    def n_atoms(self) -> int:
        return len(self.atoms)
    
    @property
    def symbols(self) -> List[str]:
        return list(self.atoms.get_chemical_symbols())
    
    @property
    def positions(self) -> np.ndarray:
        return self.atoms.get_positions()
    
    def copy(self) -> "Molecule":
        return Molecule(
            atoms=self.atoms.copy(),
            name=self.name,
            smiles=self.smiles,
            formula=self.formula,
            source=self.source,
            properties=self.properties.copy()
        )
    
    def save(self, path: str, format: str = "xyz") -> None:
        """분자를 파일로 저장"""
        write(path, self.atoms, format=format)
        
    def center(self) -> None:
        """분자 중심을 원점으로 이동"""
        self.atoms.positions -= self.atoms.get_center_of_mass()
        
    def rotate(self, angle: float, axis: str = "z") -> None:
        """분자 회전 (degrees)"""
        from ase.build import rotate
        self.atoms.rotate(angle, axis)


class MoleculeBuilder:
    """분자 생성기
    
    다양한 소스에서 분자를 생성:
    - SMILES 문자열
    - PubChem CID/이름
    - 파일 (xyz, mol, sdf, pdb 등)
    
    Examples:
        # SMILES에서
        mol = MoleculeBuilder.from_smiles("CCO")
        
        # PubChem에서
        mol = MoleculeBuilder.from_pubchem(cid=2244)
        mol = MoleculeBuilder.from_pubchem(name="aspirin")
        
        # 파일에서
        mol = MoleculeBuilder.from_file("molecule.xyz")
    """
    
    @classmethod
    def from_smiles(cls,
                    smiles: str,
                    name: str = "",
                    optimize: bool = True,
                    engine: str = "rdkit",
                    n_conformers: int = 1,
                    random_seed: int = 42) -> Union[Molecule, List[Molecule]]:
        """SMILES 문자열에서 분자 생성
        
        Args:
            smiles: SMILES 문자열
            name: 분자 이름
            optimize: MMFF 최적화 수행 여부
            engine: 최적화 엔진 (rdkit, xtb)
            n_conformers: 생성할 conformer 수
            random_seed: 랜덤 시드
            
        Returns:
            Molecule 또는 List[Molecule]
        """
        if not HAS_RDKIT:
            raise ImportError("RDKit is required for SMILES parsing. Install with: pip install rdkit")
            
        # RDKit 분자 생성
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES: {smiles}")
            
        mol = Chem.AddHs(mol)
        
        # Conformer 생성
        params = AllChem.ETKDGv3()
        params.randomSeed = random_seed
        
        if n_conformers == 1:
            AllChem.EmbedMolecule(mol, params)
            if optimize:
                AllChem.MMFFOptimizeMolecule(mol)
        else:
            AllChem.EmbedMultipleConfs(mol, numConfs=n_conformers, params=params)
            if optimize:
                AllChem.MMFFOptimizeMoleculeConfs(mol)
        
        # ASE Atoms로 변환
        formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
        
        def rdkit_to_ase(rdmol, conf_id: int = -1) -> Atoms:
            conf = rdmol.GetConformer(conf_id)
            symbols = [atom.GetSymbol() for atom in rdmol.GetAtoms()]
            positions = [conf.GetAtomPosition(i) for i in range(rdmol.GetNumAtoms())]
            positions = np.array([[p.x, p.y, p.z] for p in positions])
            return Atoms(symbols=symbols, positions=positions)
        
        if n_conformers == 1:
            atoms = rdkit_to_ase(mol, 0)
            return Molecule(
                atoms=atoms,
                name=name or formula,
                smiles=smiles,
                formula=formula,
                source="smiles"
            )
        else:
            molecules = []
            for i, conf in enumerate(mol.GetConformers()):
                atoms = rdkit_to_ase(mol, conf.GetId())
                molecules.append(Molecule(
                    atoms=atoms,
                    name=f"{name or formula}_conf{i}",
                    smiles=smiles,
                    formula=formula,
                    source="smiles"
                ))
            return molecules
    
    @classmethod
    def from_pubchem(cls,
                     cid: Optional[int] = None,
                     name: Optional[str] = None,
                     formula: Optional[str] = None,
                     output_dir: str = ".") -> Molecule:
        """PubChem에서 분자 가져오기
        
        Args:
            cid: PubChem Compound ID
            name: 화합물 이름 (CID 조회)
            formula: 분자식 (CID 조회)
            output_dir: 다운로드 디렉토리
            
        Returns:
            Molecule 객체
        """
        fetcher = PubChemFetcher()
        
        if cid is not None:
            mol_path = fetcher.fetch_by_cid(cid, output_dir)
        elif name is not None:
            cid = fetcher.search_by_name(name)
            mol_path = fetcher.fetch_by_cid(cid, output_dir)
        elif formula is not None:
            cid = fetcher.search_by_formula(formula)
            mol_path = fetcher.fetch_by_cid(cid, output_dir)
        else:
            raise ValueError("Must provide cid, name, or formula")
            
        return cls.from_file(mol_path, name=name or str(cid), source="pubchem")
    
    @classmethod
    def from_file(cls,
                  path: str,
                  format: str = "auto",
                  name: str = "",
                  source: str = "file") -> Molecule:
        """파일에서 분자 읽기
        
        Args:
            path: 파일 경로
            format: 파일 형식 (auto, xyz, mol, sdf, pdb, cif, gen)
            name: 분자 이름
            source: 소스 표시
            
        Returns:
            Molecule 객체
        """
        path = Path(path)
        
        if format == "auto":
            format = path.suffix.lstrip(".")
            
        atoms = read(str(path), format=format)
        
        return Molecule(
            atoms=atoms,
            name=name or path.stem,
            formula=atoms.get_chemical_formula(),
            source=source
        )
    
    @classmethod
    def from_atoms(cls, atoms: Atoms, name: str = "") -> Molecule:
        """ASE Atoms에서 Molecule 생성"""
        return Molecule(
            atoms=atoms,
            name=name,
            formula=atoms.get_chemical_formula(),
            source="atoms"
        )


class MoleculeAnalyzer:
    """분자 분석기"""
    
    # 일반적인 흡착 작용기
    ADSORPTION_GROUPS = {
        "alcohol": "[OH]",
        "carboxyl": "[CX3](=O)[OX1H]",
        "carbonyl": "[CX3]=[OX1]",
        "amine": "[NX3;H2,H1;!$(NC=O)]",
        "thiol": "[SH]",
        "ether": "[OD2]([#6])[#6]",
        "aromatic": "c1ccccc1",
    }
    
    @classmethod
    def get_functional_groups(cls, molecule: Molecule) -> List[FunctionalGroup]:
        """작용기 감지"""
        if not HAS_RDKIT or not molecule.smiles:
            return []
            
        mol = Chem.MolFromSmiles(molecule.smiles)
        if mol is None:
            return []
            
        groups = []
        for name, smarts in cls.ADSORPTION_GROUPS.items():
            pattern = Chem.MolFromSmarts(smarts)
            if pattern and mol.HasSubstructMatch(pattern):
                matches = mol.GetSubstructMatches(pattern)
                for match in matches:
                    groups.append(FunctionalGroup(
                        name=name,
                        atoms=list(match),
                        smarts=smarts
                    ))
        return groups
    
    @classmethod
    def get_adsorption_centers(cls, molecule: Molecule) -> List[int]:
        """흡착 중심 원자 자동 제안"""
        groups = cls.get_functional_groups(molecule)
        centers = set()
        
        for group in groups:
            # 작용기의 헤테로원자를 중심으로
            for idx in group.atoms:
                symbol = molecule.symbols[idx]
                if symbol in ["O", "N", "S"]:
                    centers.add(idx)
                    
        if not centers:
            # 작용기가 없으면 헤테로원자 탐색
            for i, symbol in enumerate(molecule.symbols):
                if symbol in ["O", "N", "S"]:
                    centers.add(i)
                    
        return list(centers)
    
    @classmethod
    def estimate_footprint(cls, molecule: Molecule) -> Tuple[float, float]:
        """분자 footprint 추정 (width, length)"""
        positions = molecule.positions
        
        # 주성분 분석으로 분자 방향 결정
        centered = positions - positions.mean(axis=0)
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        
        # 가장 큰 두 주성분 방향의 범위
        sorted_idx = np.argsort(eigenvalues)[::-1]
        
        projected = centered @ eigenvectors
        ranges = projected.max(axis=0) - projected.min(axis=0)
        
        # VdW 반지름 고려 (+3 Å)
        width = ranges[sorted_idx[0]] + 3.0
        length = ranges[sorted_idx[1]] + 3.0
        
        return (width, length)
