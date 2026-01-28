"""
XTB Calculator: GFN-xTB 통합
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from ase import Atoms
from ase.io import read, write
from ase.calculators.calculator import Calculator as ASECalculator, all_changes

from surfscreen.calculator.base import Calculator, CalculatorFactory


class XTBCalculator(Calculator):
    """GFN-xTB Calculator
    
    GFN2-xTB semi-empirical method
    
    Examples:
        calc = XTBCalculator(method="gfn2")
        energy = calc.get_energy(atoms)
        result = calc.optimize(atoms)
    """
    
    name = "xtb"
    
    def __init__(self,
                 method: str = "gfn2",
                 accuracy: float = 1.0,
                 electronic_temperature: float = 300.0,
                 max_iterations: int = 250,
                 **kwargs):
        """
        Args:
            method: xTB 방법 (gfn0, gfn1, gfn2, gfnff)
            accuracy: 정확도 (낮을수록 정확, 기본 1.0)
            electronic_temperature: 전자 온도 (K)
            max_iterations: 최대 반복 횟수
        """
        super().__init__(**kwargs)
        self.method = method.lower()
        self.accuracy = accuracy
        self.electronic_temperature = electronic_temperature
        self.max_iterations = max_iterations
        
        self._validate()
    
    def _validate(self):
        """xTB 설치 확인"""
        if not self._check_xtb():
            raise ImportError(
                "xTB not found. Install with: conda install -c conda-forge xtb"
            )
    
    @staticmethod
    def _check_xtb() -> bool:
        """xTB 실행 가능 확인"""
        try:
            result = subprocess.run(
                ["xtb", "--version"],
                capture_output=True,
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_ase_calculator(self) -> ASECalculator:
        """xTB ASE Calculator 반환"""
        if self._ase_calc is not None:
            return self._ase_calc
        
        # 자체 구현 calculator 사용
        self._ase_calc = XTBASECalculator(
            method=self.method,
            accuracy=self.accuracy,
            electronic_temperature=self.electronic_temperature,
            max_iterations=self.max_iterations
        )
        
        return self._ase_calc
    
    @staticmethod
    def available_methods() -> list:
        """사용 가능한 방법 목록"""
        return ["gfn0", "gfn1", "gfn2", "gfnff"]


class XTBASECalculator(ASECalculator):
    """xTB용 ASE Calculator 구현"""
    
    implemented_properties = ['energy', 'forces']
    
    def __init__(self,
                 method: str = "gfn2",
                 accuracy: float = 1.0,
                 electronic_temperature: float = 300.0,
                 max_iterations: int = 250,
                 **kwargs):
        super().__init__(**kwargs)
        self.method = method
        self.accuracy = accuracy
        self.electronic_temperature = electronic_temperature
        self.max_iterations = max_iterations
    
    def calculate(self, atoms=None, properties=['energy'], system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # 입력 파일 저장
            input_file = tmpdir / "input.xyz"
            write(str(input_file), self.atoms, format="xyz")
            
            # xTB 실행
            cmd = [
                "xtb", str(input_file),
                f"--{self.method}",
                "--acc", str(self.accuracy),
                "--etemp", str(self.electronic_temperature),
                "--iterations", str(self.max_iterations),
                "--grad",
            ]
            
            result = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"xTB failed: {result.stderr}")
            
            # 에너지 파싱
            energy = self._parse_energy(result.stdout)
            forces = self._parse_forces(tmpdir / "gradient")
            
            self.results['energy'] = energy
            self.results['forces'] = forces
    
    def _parse_energy(self, output: str) -> float:
        """xTB 출력에서 에너지 추출"""
        for line in output.split('\n'):
            if 'TOTAL ENERGY' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'TOTAL' and i + 2 < len(parts):
                        try:
                            return float(parts[i + 2]) * 27.2114  # Hartree to eV
                        except ValueError:
                            pass
        raise ValueError("Could not parse energy from xTB output")
    
    def _parse_forces(self, gradient_file: Path) -> np.ndarray:
        """Gradient 파일에서 힘 추출"""
        if not gradient_file.exists():
            return np.zeros((len(self.atoms), 3))
        
        with open(gradient_file) as f:
            lines = f.readlines()
        
        # gradient를 forces로 변환 (부호 반전)
        n_atoms = len(self.atoms)
        forces = np.zeros((n_atoms, 3))
        
        # 그래디언트 라인 찾기 (원자 수 다음부터)
        start_idx = None
        for i, line in enumerate(lines):
            if '$grad' in line.lower():
                start_idx = i + 1
                break
        
        if start_idx is None:
            return forces
        
        # 좌표 라인 건너뛰기
        start_idx += n_atoms
        
        for i in range(n_atoms):
            if start_idx + i < len(lines):
                parts = lines[start_idx + i].split()
                if len(parts) >= 3:
                    # Hartree/Bohr to eV/Å
                    forces[i] = -np.array([float(x) for x in parts[:3]]) * 51.4221
        
        return forces


# 팩토리 등록
CalculatorFactory.register("xtb", XTBCalculator)
