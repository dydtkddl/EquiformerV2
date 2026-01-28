"""
MACE Calculator: MACE MLIP 통합
"""

from __future__ import annotations

from typing import Optional, Literal
from pathlib import Path

from ase import Atoms
from ase.calculators.calculator import Calculator as ASECalculator

from surfscreen.calculator.base import Calculator, CalculatorFactory


class MACECalculator(Calculator):
    """MACE MLIP Calculator
    
    Materials Project MACE 모델 사용
    
    Examples:
        calc = MACECalculator(model="medium", device="cuda")
        energy = calc.get_energy(atoms)
        result = calc.optimize(atoms)
    """
    
    name = "mace"
    
    def __init__(self,
                 model: str = "medium",
                 device: str = "cuda",
                 dtype: str = "float32",
                 model_path: Optional[str] = None,
                 **kwargs):
        """
        Args:
            model: 모델 크기 (small, medium, large)
            device: 디바이스 (cuda, cpu)
            dtype: 데이터 타입 (float32, float64)
            model_path: 커스텀 모델 경로
        """
        super().__init__(**kwargs)
        self.model = model
        self.device = device
        self.dtype = dtype
        self.model_path = model_path
        
        self._validate()
    
    def _validate(self):
        """MACE 설치 확인"""
        try:
            from mace.calculators import mace_mp
        except ImportError:
            raise ImportError(
                "MACE not installed. Install with: pip install mace-torch"
            )
    
    def get_ase_calculator(self) -> ASECalculator:
        """MACE ASE Calculator 반환"""
        if self._ase_calc is not None:
            return self._ase_calc
        
        from mace.calculators import mace_mp, MACECalculator as MACECalc
        
        if self.model_path:
            # 커스텀 모델
            self._ase_calc = MACECalc(
                model_paths=self.model_path,
                device=self.device,
                default_dtype=self.dtype
            )
        else:
            # Materials Project 모델
            self._ase_calc = mace_mp(
                model=self.model,
                device=self.device,
                default_dtype=self.dtype
            )
        
        return self._ase_calc
    
    @staticmethod
    def available_models() -> list:
        """사용 가능한 모델 목록"""
        return ["small", "medium", "large"]
    
    @staticmethod
    def check_gpu() -> bool:
        """GPU 사용 가능 여부"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False


# 팩토리 등록
CalculatorFactory.register("mace", MACECalculator)
