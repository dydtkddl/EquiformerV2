"""
Conformer Generator: 다중 conformer 생성

RDKit, CREST, xTB 엔진 지원
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import numpy as np
from ase import Atoms
from ase.io import read, write

if TYPE_CHECKING:
    from surfscreen.molecule.builder import Molecule

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False


class ConformerGenerator:
    """Conformer 생성기
    
    Engines:
        - rdkit: RDKit ETKDG (빠름, 기본)
        - crest: CREST conformer search (정확)
        - xtb: xTB metadynamics
        
    Examples:
        gen = ConformerGenerator(engine="rdkit")
        conformers = gen.generate(molecule, n_conformers=10)
        
        gen = ConformerGenerator(engine="crest")
        conformers = gen.generate(molecule, energy_window=6.0)
    """
    
    def __init__(self,
                 engine: str = "rdkit",
                 optimize: bool = True,
                 energy_window: float = 10.0,  # kcal/mol
                 **kwargs):
        """
        Args:
            engine: 엔진 (rdkit, crest, xtb)
            optimize: 생성 후 최적화
            energy_window: 에너지 윈도우 (kcal/mol)
            **kwargs: 엔진별 추가 옵션
        """
        self.engine = engine.lower()
        self.optimize = optimize
        self.energy_window = energy_window
        self.options = kwargs
        
        self._validate_engine()
        
    def _validate_engine(self):
        """엔진 사용 가능 여부 확인"""
        if self.engine == "rdkit" and not HAS_RDKIT:
            raise ImportError("RDKit not installed")
        elif self.engine == "crest":
            if not self._check_command("crest"):
                raise ImportError("CREST not found in PATH")
        elif self.engine == "xtb":
            if not self._check_command("xtb"):
                raise ImportError("xTB not found in PATH")
                
    @staticmethod
    def _check_command(cmd: str) -> bool:
        """명령어 존재 확인"""
        try:
            subprocess.run([cmd, "--version"], 
                          capture_output=True, 
                          check=False)
            return True
        except FileNotFoundError:
            return False
    
    def generate(self,
                 molecule: "Molecule",
                 n_conformers: int = 10,
                 random_seed: int = 42) -> List["Molecule"]:
        """Conformer 생성
        
        Args:
            molecule: 입력 분자
            n_conformers: 생성할 최대 conformer 수
            random_seed: 랜덤 시드
            
        Returns:
            Conformer 목록
        """
        if self.engine == "rdkit":
            return self._generate_rdkit(molecule, n_conformers, random_seed)
        elif self.engine == "crest":
            return self._generate_crest(molecule, n_conformers)
        elif self.engine == "xtb":
            return self._generate_xtb(molecule, n_conformers)
        else:
            raise ValueError(f"Unknown engine: {self.engine}")
            
    def _generate_rdkit(self,
                        molecule: "Molecule",
                        n_conformers: int,
                        random_seed: int) -> List["Molecule"]:
        """RDKit ETKDG로 conformer 생성"""
        from surfscreen.molecule.builder import Molecule
        
        if not molecule.smiles:
            raise ValueError("SMILES required for RDKit conformer generation")
            
        mol = Chem.MolFromSmiles(molecule.smiles)
        mol = Chem.AddHs(mol)
        
        # ETKDG 파라미터
        params = AllChem.ETKDGv3()
        params.randomSeed = random_seed
        params.useSmallRingTorsions = True
        params.useMacrocycleTorsions = True
        
        # Conformer 생성
        AllChem.EmbedMultipleConfs(mol, numConfs=n_conformers, params=params)
        
        if self.optimize:
            results = AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=500)
            energies = [r[1] for r in results if r[0] == 0]
        else:
            energies = [0.0] * mol.GetNumConformers()
            
        # 에너지 윈도우로 필터링
        if energies:
            min_e = min(energies)
            valid_idx = [i for i, e in enumerate(energies) 
                        if (e - min_e) <= self.energy_window]
        else:
            valid_idx = list(range(mol.GetNumConformers()))
            
        # ASE Atoms로 변환
        conformers = []
        for i, conf_id in enumerate(valid_idx):
            conf = mol.GetConformer(conf_id)
            symbols = [atom.GetSymbol() for atom in mol.GetAtoms()]
            positions = np.array([
                [conf.GetAtomPosition(j).x, 
                 conf.GetAtomPosition(j).y, 
                 conf.GetAtomPosition(j).z]
                for j in range(mol.GetNumAtoms())
            ])
            
            atoms = Atoms(symbols=symbols, positions=positions)
            
            conf_mol = Molecule(
                atoms=atoms,
                name=f"{molecule.name}_conf{i}",
                smiles=molecule.smiles,
                formula=molecule.formula,
                source="rdkit_conformer",
                properties={"energy": energies[conf_id] if energies else None}
            )
            conformers.append(conf_mol)
            
        return conformers
    
    def _generate_crest(self,
                        molecule: "Molecule",
                        n_conformers: int) -> List["Molecule"]:
        """CREST로 conformer 생성"""
        from surfscreen.molecule.builder import Molecule
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 입력 파일 저장
            input_file = tmpdir / "input.xyz"
            write(str(input_file), molecule.atoms, format="xyz")
            
            # CREST 실행
            cmd = [
                "crest", str(input_file),
                "--gfn2",
                "--ewin", str(self.energy_window),
                "-T", str(self.options.get("threads", 4)),
            ]
            
            if self.options.get("quick", False):
                cmd.append("--quick")
                
            result = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"CREST failed: {result.stderr}")
            
            # 결과 읽기
            ensemble_file = tmpdir / "crest_conformers.xyz"
            if not ensemble_file.exists():
                raise FileNotFoundError("CREST output not found")
                
            atoms_list = read(str(ensemble_file), index=":")
            
            conformers = []
            for i, atoms in enumerate(atoms_list[:n_conformers]):
                energy = atoms.info.get("energy", None)
                conf_mol = Molecule(
                    atoms=atoms,
                    name=f"{molecule.name}_conf{i}",
                    smiles=molecule.smiles,
                    formula=molecule.formula,
                    source="crest_conformer",
                    properties={"energy": energy}
                )
                conformers.append(conf_mol)
                
            return conformers
    
    def _generate_xtb(self,
                      molecule: "Molecule",
                      n_conformers: int) -> List["Molecule"]:
        """xTB metadynamics로 conformer 생성"""
        from surfscreen.molecule.builder import Molecule
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 입력 파일 저장
            input_file = tmpdir / "input.xyz"
            write(str(input_file), molecule.atoms, format="xyz")
            
            # xTB 실행 (metadynamics)
            cmd = [
                "xtb", str(input_file),
                "--gfn", "2",
                "--metadn",
                str(n_conformers * 2),  # 더 많이 생성 후 필터링
            ]
            
            result = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"xTB failed: {result.stderr}")
            
            # 결과 읽기
            traj_file = tmpdir / "xtb_metadyn.trj"
            if not traj_file.exists():
                # 단일 최적화된 구조 반환
                opt_file = tmpdir / "xtbopt.xyz"
                if opt_file.exists():
                    atoms = read(str(opt_file))
                    return [Molecule(
                        atoms=atoms,
                        name=f"{molecule.name}_opt",
                        source="xtb_opt"
                    )]
                raise FileNotFoundError("xTB output not found")
                
            atoms_list = read(str(traj_file), index=":")
            
            # 중복 제거 및 정렬
            unique = self._filter_unique(atoms_list)[:n_conformers]
            
            conformers = []
            for i, atoms in enumerate(unique):
                conf_mol = Molecule(
                    atoms=atoms,
                    name=f"{molecule.name}_conf{i}",
                    formula=molecule.formula,
                    source="xtb_conformer"
                )
                conformers.append(conf_mol)
                
            return conformers
    
    @staticmethod
    def _filter_unique(atoms_list: List[Atoms], 
                       rmsd_threshold: float = 0.5) -> List[Atoms]:
        """RMSD 기반 중복 제거"""
        if not atoms_list:
            return []
            
        unique = [atoms_list[0]]
        
        for atoms in atoms_list[1:]:
            is_unique = True
            for ref in unique:
                # 간단한 RMSD 계산
                rmsd = np.sqrt(np.mean((atoms.positions - ref.positions) ** 2))
                if rmsd < rmsd_threshold:
                    is_unique = False
                    break
            if is_unique:
                unique.append(atoms)
                
        return unique
