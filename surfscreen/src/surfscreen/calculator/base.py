"""
Calculator Base Classes
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass

import numpy as np
from ase import Atoms
from ase.optimize import BFGS, FIRE
from ase.io.trajectory import Trajectory

from surfscreen.logging_utils import calc_logger as logger

if TYPE_CHECKING:
    from ase.calculators.calculator import Calculator as ASECalculator


@dataclass
class OptimizationResult:
    """최적화 결과"""
    atoms: Atoms
    initial_energy: float
    final_energy: float
    steps: int
    converged: bool
    trajectory: Optional[str] = None
    
    @property
    def energy_change(self) -> float:
        return self.final_energy - self.initial_energy


class Calculator(ABC):
    """계산 엔진 베이스 클래스"""
    
    name: str = "base"
    
    def __init__(self, **kwargs):
        self.options = kwargs
        self._ase_calc = None
        logger.debug(f"Calculator initialized: {self.name}", options=kwargs)
    
    @abstractmethod
    def get_ase_calculator(self) -> "ASECalculator":
        """ASE Calculator 반환"""
        pass
    
    def get_energy(self, atoms: Atoms) -> float:
        """단일 포인트 에너지 계산"""
        logger.detail(f"Calculating single-point energy for {len(atoms)} atoms")
        logger.debug(f"  Symbols: {atoms.get_chemical_formula()}")
        logger.debug(f"  PBC: {atoms.pbc.tolist()}")
        
        atoms = atoms.copy()
        atoms.calc = self.get_ase_calculator()
        energy = atoms.get_potential_energy()
        
        logger.energy(f"E = {energy:.6f} eV", 
                     formula=atoms.get_chemical_formula(),
                     n_atoms=len(atoms))
        return energy
    
    def get_forces(self, atoms: Atoms) -> np.ndarray:
        """힘 계산"""
        logger.detail(f"Calculating forces for {len(atoms)} atoms")
        
        atoms = atoms.copy()
        atoms.calc = self.get_ase_calculator()
        forces = atoms.get_forces()
        
        fmax = np.sqrt((forces**2).sum(axis=1)).max()
        frms = np.sqrt((forces**2).mean())
        logger.calc(f"Forces: max={fmax:.4f} eV/Å, rms={frms:.4f} eV/Å")
        logger.debug(f"Force shape: {forces.shape}")
        
        return forces
    
    def optimize(self,
                 atoms: Atoms,
                 fmax: float = 0.05,
                 steps: int = 500,
                 optimizer: str = "BFGS",
                 trajectory: Optional[str] = None,
                 logfile: Optional[str] = None) -> OptimizationResult:
        """구조 최적화
        
        Args:
            atoms: 입력 구조
            fmax: 최대 힘 수렴 기준 (eV/Å)
            steps: 최대 스텝 수
            optimizer: 최적화 알고리즘 (BFGS, FIRE)
            trajectory: 트라젝토리 파일 경로
            logfile: 로그 파일 경로
            
        Returns:
            OptimizationResult
        """
        with logger.section(f"Structure Optimization ({optimizer})"):
            logger.info(f"Formula: {atoms.get_chemical_formula()}, N={len(atoms)}")
            logger.detail(f"fmax={fmax} eV/Å, max_steps={steps}")
            logger.debug(f"Trajectory: {trajectory}, Logfile: {logfile}")
            
            # Save constraints BEFORE copy (copy() doesn't preserve them in ASE)
            original_constraints = list(atoms.constraints) if atoms.constraints else []
            if original_constraints:
                logger.detail(f"Constraints: {len(original_constraints)} constraint(s)")
            
            atoms = atoms.copy()
            atoms.calc = self.get_ase_calculator()
            
            # Re-apply constraints
            if original_constraints:
                atoms.set_constraint(original_constraints)
            
            initial_energy = atoms.get_potential_energy()
            logger.energy(f"Initial: E = {initial_energy:.6f} eV")
            
            # 최적화 알고리즘 선택
            opt_cls = BFGS if optimizer == "BFGS" else FIRE
            logger.debug(f"Optimizer class: {opt_cls.__name__}")
            
            kwargs = {}
            if trajectory:
                kwargs["trajectory"] = trajectory
            if logfile:
                kwargs["logfile"] = logfile
                
            opt = opt_cls(atoms, **kwargs)
            
            # 최적화 콜백 (HIGH 이상에서 매 스텝 로깅)
            def _step_callback():
                step = opt.nsteps
                e = atoms.get_potential_energy()
                f = atoms.get_forces()
                fmax_curr = np.sqrt((f**2).sum(axis=1)).max()
                logger.detail(f"Step {step:4d}: E={e:.6f} eV, fmax={fmax_curr:.4f} eV/Å")
            
            opt.attach(_step_callback)
            
            logger.step("Running optimization...")
            converged = opt.run(fmax=fmax, steps=steps)
            
            final_energy = atoms.get_potential_energy()
            delta_e = final_energy - initial_energy
            
            logger.energy(f"Final: E = {final_energy:.6f} eV")
            logger.info(f"Steps: {opt.nsteps}, ΔE = {delta_e:.6f} eV")
            
            if converged:
                logger.success(f"Converged in {opt.nsteps} steps")
            else:
                logger.warning(f"Not converged after {opt.nsteps} steps")
            
            return OptimizationResult(
                atoms=atoms,
                initial_energy=initial_energy,
                final_energy=final_energy,
                steps=opt.nsteps,
                converged=converged,
                trajectory=trajectory
            )


class CalculatorFactory:
    """계산 엔진 팩토리
    
    Examples:
        calc = CalculatorFactory.create("mace", model="medium")
        calc = CalculatorFactory.create("xtb", method="gfn2")
    """
    
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, calculator_cls: type):
        """계산 엔진 등록"""
        cls._registry[name.lower()] = calculator_cls
    
    @classmethod
    def create(cls, 
               engine: str, 
               **kwargs) -> Calculator:
        """계산 엔진 생성
        
        Args:
            engine: 엔진 이름 (mace, cp2k, xtb, crest)
            **kwargs: 엔진별 옵션
            
        Returns:
            Calculator 인스턴스
        """
        engine = engine.lower()
        
        if engine not in cls._registry:
            # 동적 로딩 시도
            cls._try_load(engine)
            
        if engine not in cls._registry:
            raise ValueError(f"Unknown engine: {engine}. "
                           f"Available: {list(cls._registry.keys())}")
        
        return cls._registry[engine](**kwargs)
    
    @classmethod
    def _try_load(cls, engine: str):
        """엔진 동적 로딩"""
        if engine == "mace":
            from surfscreen.calculator.mace import MACECalculator
            cls.register("mace", MACECalculator)
        elif engine == "xtb":
            from surfscreen.calculator.xtb import XTBCalculator
            cls.register("xtb", XTBCalculator)
        elif engine == "cp2k":
            from surfscreen.calculator.cp2k import CP2KCalculator
            cls.register("cp2k", CP2KCalculator)
    
    @classmethod
    def available(cls) -> list:
        """사용 가능한 엔진 목록"""
        available = []
        
        # MACE
        try:
            import mace
            available.append("mace")
        except ImportError:
            pass
        
        # xTB
        try:
            from xtb.interface import Calculator as XTBCalc
            available.append("xtb")
        except ImportError:
            pass
        
        # CP2K (시스템 또는 Docker)
        import shutil
        if shutil.which("cp2k") or shutil.which("docker"):
            available.append("cp2k")
        
        return available
