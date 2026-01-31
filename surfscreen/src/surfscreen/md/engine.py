"""
Molecular Dynamics Engine

MACE/EquiformerV2 기반 분자 동역학 시뮬레이션 엔진
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import time

from ase import Atoms, units
from ase.io import write, read
from ase.io.trajectory import Trajectory
from ase.md.langevin import Langevin
from ase.md.npt import NPT
from ase.md.nvtberendsen import NVTBerendsen
from ase.md.nptberendsen import NPTBerendsen
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution

from surfscreen.logging_utils import md_logger as slog, VerboseLevel, get_verbose


@dataclass
class MDConfig:
    """MD 시뮬레이션 설정"""
    # Ensemble
    ensemble: str = "nvt"  # nvt, npt, nve
    
    # Temperature & Pressure
    temperature: float = 300.0  # K
    pressure: float = 1.0  # bar (NPT only)
    
    # Dynamics
    timestep: float = 1.0  # fs
    steps: int = 10000
    equilibration: int = 1000
    
    # Thermostat
    thermostat: str = "langevin"  # langevin, berendsen, nose-hoover
    friction: float = 0.01  # 1/fs (Langevin)
    taut: float = 100.0  # fs (Nose-Hoover, Berendsen)
    
    # Barostat (NPT)
    barostat: str = "berendsen"  # berendsen, parrinello-rahman
    taup: float = 1000.0  # fs
    compressibility: float = 4.5e-5  # 1/bar
    
    # Output
    trajectory_interval: int = 10
    log_interval: int = 100
    checkpoint_interval: int = 1000
    
    # Calculator
    engine: str = "mace"
    model: str = "medium"
    device: str = "cuda"
    force_xtb: bool = False  # Force xTB even with PBC (may fail)
    
    @classmethod
    def from_dict(cls, d: dict) -> "MDConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_yaml(cls, path: str) -> "MDConfig":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class MDState:
    """MD 시뮬레이션 상태"""
    step: int = 0
    time: float = 0.0  # fs
    temperature: float = 0.0  # K
    potential_energy: float = 0.0  # eV
    kinetic_energy: float = 0.0  # eV
    total_energy: float = 0.0  # eV
    pressure: float = 0.0  # bar (NPT)
    volume: float = 0.0  # Å³
    
    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "time_fs": self.time,
            "temperature_K": self.temperature,
            "potential_energy_eV": self.potential_energy,
            "kinetic_energy_eV": self.kinetic_energy,
            "total_energy_eV": self.total_energy,
            "pressure_bar": self.pressure,
            "volume_A3": self.volume
        }


class MDLogger:
    """MD 로그 기록기"""
    
    def __init__(self, log_path: str, config: MDConfig):
        self.log_path = Path(log_path)
        self.config = config
        self.history: List[Dict] = []
        self.start_time = time.time()
        
        # 헤더 작성
        with open(self.log_path, "w") as f:
            f.write("# SurfScreen MD Log\n")
            f.write(f"# Started: {datetime.now().isoformat()}\n")
            f.write(f"# Ensemble: {config.ensemble.upper()}\n")
            f.write(f"# Temperature: {config.temperature} K\n")
            if config.ensemble == "npt":
                f.write(f"# Pressure: {config.pressure} bar\n")
            f.write("#\n")
            f.write("# Step  Time(fs)  Temp(K)  E_pot(eV)  E_kin(eV)  E_tot(eV)")
            if config.ensemble == "npt":
                f.write("  Press(bar)  Vol(Å³)")
            f.write("\n")
    
    def log(self, state: MDState):
        """상태 기록"""
        self.history.append(state.to_dict())
        
        with open(self.log_path, "a") as f:
            line = f"{state.step:8d}  {state.time:10.2f}  {state.temperature:8.2f}  "
            line += f"{state.potential_energy:12.6f}  {state.kinetic_energy:12.6f}  "
            line += f"{state.total_energy:12.6f}"
            if self.config.ensemble == "npt":
                line += f"  {state.pressure:10.2f}  {state.volume:10.2f}"
            f.write(line + "\n")
    
    def get_summary(self) -> Dict:
        """요약 통계"""
        if not self.history:
            return {}
            
        temps = [h["temperature_K"] for h in self.history]
        etots = [h["total_energy_eV"] for h in self.history]
        
        return {
            "total_steps": len(self.history),
            "total_time_fs": self.history[-1]["time_fs"],
            "avg_temperature_K": np.mean(temps),
            "std_temperature_K": np.std(temps),
            "avg_total_energy_eV": np.mean(etots),
            "std_total_energy_eV": np.std(etots),
            "wall_time_s": time.time() - self.start_time
        }


class MDEngine:
    """분자 동역학 시뮬레이션 엔진"""
    
    def __init__(self, 
                 atoms: Atoms,
                 config: MDConfig,
                 output_dir: str = "md_output"):
        """
        Args:
            atoms: 초기 구조
            config: MD 설정
            output_dir: 출력 디렉토리
        """
        self.atoms = atoms.copy()
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.calculator = None
        self.dynamics = None
        self.trajectory = None
        self.logger = None
        self.state = MDState()
        
        self._setup_calculator()
        self._setup_dynamics()
        
    def _setup_calculator(self):
        """계산기 설정"""
        if self.config.engine == "mace":
            from mace.calculators import mace_mp
            self.calculator = mace_mp(
                model=self.config.model,
                device=self.config.device,
                default_dtype="float64"
            )
        elif self.config.engine == "xtb":
            # PBC 체크 - xTB는 주기적 경계 조건에서 제한이 있음
            if self.atoms.pbc.any():
                import warnings
                warnings.warn(
                    "\n⚠️  WARNING: xTB with PBC (Periodic Boundary Conditions) detected!\n"
                    "   xTB does not fully support multipole calculations with PBC.\n"
                    "   This may cause 'Multipoles not available with PBC' errors.\n"
                    "\n"
                    "   Recommended solutions:\n"
                    "   1. Use MACE instead: --engine mace\n"
                    "   2. For molecules without PBC, xTB works fine\n"
                    "   3. Use --force-xtb to proceed anyway (may fail)\n",
                    UserWarning
                )
                if not getattr(self.config, 'force_xtb', False):
                    raise RuntimeError(
                        "xTB + PBC is not supported. Use --engine mace for surface/periodic systems, "
                        "or use --force-xtb to attempt anyway."
                    )
            
            from xtb.ase.calculator import XTB
            self.calculator = XTB(method="GFN2-xTB")
        else:
            raise ValueError(f"Unknown engine: {self.config.engine}")
            
        self.atoms.calc = self.calculator
        
    def _setup_dynamics(self):
        """동역학 설정"""
        # 초기 속도 분포
        MaxwellBoltzmannDistribution(self.atoms, temperature_K=self.config.temperature)
        
        timestep = self.config.timestep * units.fs
        
        if self.config.ensemble == "nvt":
            if self.config.thermostat == "langevin":
                self.dynamics = Langevin(
                    self.atoms,
                    timestep=timestep,
                    temperature_K=self.config.temperature,
                    friction=self.config.friction
                )
            elif self.config.thermostat == "berendsen":
                self.dynamics = NVTBerendsen(
                    self.atoms,
                    timestep=timestep,
                    temperature_K=self.config.temperature,
                    taut=self.config.taut * units.fs
                )
            else:
                raise ValueError(f"Unknown thermostat: {self.config.thermostat}")
                
        elif self.config.ensemble == "npt":
            if self.config.barostat == "berendsen":
                self.dynamics = NPTBerendsen(
                    self.atoms,
                    timestep=timestep,
                    temperature_K=self.config.temperature,
                    pressure_au=self.config.pressure * units.bar,
                    taut=self.config.taut * units.fs,
                    taup=self.config.taup * units.fs,
                    compressibility_au=self.config.compressibility / units.bar
                )
            else:
                # Parrinello-Rahman like
                self.dynamics = NPT(
                    self.atoms,
                    timestep=timestep,
                    temperature_K=self.config.temperature,
                    externalstress=self.config.pressure * units.bar,
                    ttime=self.config.taut * units.fs,
                    pfactor=self.config.taup * units.fs * units.bar
                )
                
        elif self.config.ensemble == "nve":
            from ase.md.verlet import VelocityVerlet
            self.dynamics = VelocityVerlet(self.atoms, timestep=timestep)
        else:
            raise ValueError(f"Unknown ensemble: {self.config.ensemble}")
            
        # Trajectory 설정
        traj_path = self.output_dir / "trajectory.traj"
        self.trajectory = Trajectory(str(traj_path), "w", self.atoms)
        self.dynamics.attach(self.trajectory.write, interval=self.config.trajectory_interval)
        
        # Logger 설정
        log_path = self.output_dir / "md.log"
        self.logger = MDLogger(str(log_path), self.config)
        self.dynamics.attach(self._log_step, interval=self.config.log_interval)
        
        # Checkpoint 설정
        self.dynamics.attach(self._save_checkpoint, interval=self.config.checkpoint_interval)
        
    def _log_step(self):
        """현재 상태 로깅"""
        self.state = MDState(
            step=self.dynamics.nsteps,
            time=self.dynamics.nsteps * self.config.timestep,
            temperature=self.atoms.get_temperature(),
            potential_energy=self.atoms.get_potential_energy(),
            kinetic_energy=self.atoms.get_kinetic_energy(),
            total_energy=self.atoms.get_total_energy(),
            pressure=0.0,  # NPT에서 계산 필요
            volume=self.atoms.get_volume() if self.atoms.pbc.any() else 0.0
        )
        self.logger.log(self.state)
        
    def _save_checkpoint(self):
        """체크포인트 저장"""
        checkpoint_path = self.output_dir / "checkpoint.xyz"
        write(str(checkpoint_path), self.atoms, format="extxyz")
        
        # 상태 저장
        state_path = self.output_dir / "checkpoint_state.json"
        with open(state_path, "w") as f:
            json.dump({
                "step": self.dynamics.nsteps,
                "config": self.config.to_dict(),
                "state": self.state.to_dict()
            }, f, indent=2)
    
    def run(self, 
            steps: Optional[int] = None,
            callback: Optional[Callable] = None) -> Dict:
        """MD 실행
        
        Args:
            steps: 스텝 수 (None이면 config에서)
            callback: 각 스텝 후 호출할 함수
            
        Returns:
            실행 결과 요약
        """
        if steps is None:
            steps = self.config.steps
        
        with slog.section(f"MD Simulation ({self.config.ensemble.upper()})"):
            slog.info(f"System: {len(self.atoms)} atoms", icon='atom')
            slog.info(f"Temperature: {self.config.temperature} K")
            slog.info(f"Steps: {steps}, Timestep: {self.config.timestep} fs")
            slog.detail(f"Total time: {steps * self.config.timestep:.1f} fs")
            slog.debug(f"Engine: {self.config.engine}, Model: {self.config.model}")
            slog.debug(f"Thermostat: {self.config.thermostat}, Friction: {self.config.friction}")
            
            if self.config.ensemble == "npt":
                slog.info(f"Pressure: {self.config.pressure} bar")
                slog.debug(f"Barostat: {self.config.barostat}, taup: {self.config.taup} fs")
            
            # 진행률 로깅 간격 설정
            log_interval = max(1, steps // 10)
            
            try:
                for i in range(steps):
                    self.dynamics.run(1)
                    
                    if callback:
                        callback(self.state)
                    
                    # 진행 상황 출력 (verbose 레벨에 따라)
                    if (i + 1) % log_interval == 0:
                        progress = (i + 1) / steps * 100
                        slog.progress(
                            f"T={self.state.temperature:.1f}K, E={self.state.total_energy:.4f}eV",
                            current=i+1, total=steps
                        )
                    
                    # 상세 로깅 (HIGH 이상)
                    if (i + 1) % (log_interval * 2) == 0 and get_verbose() >= VerboseLevel.HIGH:
                        slog.data(
                            f"Thermodynamics at step {i+1}",
                            T_K=self.state.temperature,
                            E_pot_eV=self.state.potential_energy,
                            E_kin_eV=self.state.kinetic_energy,
                            E_tot_eV=self.state.total_energy
                        )
                        if self.config.ensemble == "npt":
                            slog.detail(f"Volume: {self.state.volume:.2f} Å³")
                            
            except KeyboardInterrupt:
                slog.warning("MD interrupted by user")
                
            finally:
                self.trajectory.close()
            
            # 최종 구조 저장
            final_path = self.output_dir / "final.xyz"
            write(str(final_path), self.atoms, format="extxyz")
            slog.detail(f"Final structure saved: {final_path}")
            
            # 다중 포맷 궤적 저장
            self._export_trajectory_formats()
            
            # 요약 저장
            summary = self.logger.get_summary()
            summary_path = self.output_dir / "summary.json"
            with open(summary_path, "w") as f:
                json.dump(summary, f, indent=2)
            
            slog.success(f"MD completed! Total time: {summary.get('total_time_fs', 0):.1f} fs")
            slog.info(f"Avg temperature: {summary.get('avg_temperature_K', 0):.1f} K")
            slog.info(f"Output: {self.output_dir}", icon='file')
            
            return summary
    
    def _export_trajectory_formats(self):
        """다양한 포맷으로 궤적 내보내기 (OVITO 등 호환)"""
        traj_path = self.output_dir / "trajectory.traj"
        
        if not traj_path.exists():
            return
            
        # ASE trajectory 읽기
        frames = read(str(traj_path), index=":")
        
        if not frames:
            return
            
        print(f"   📁 Exporting {len(frames)} frames...")
        
        # 1. Extended XYZ (권장 - cell 정보 포함)
        extxyz_path = self.output_dir / "trajectory.extxyz"
        write(str(extxyz_path), frames, format="extxyz")
        print(f"   ✓ trajectory.extxyz (OVITO/ASE compatible)")
        
        # 2. XYZ multi-frame
        xyz_path = self.output_dir / "trajectory.xyz"
        write(str(xyz_path), frames, format="xyz")
        print(f"   ✓ trajectory.xyz (VMD/Jmol compatible)")
    
    @classmethod
    def continue_from_checkpoint(cls, 
                                  checkpoint_dir: str,
                                  additional_steps: int) -> "MDEngine":
        """체크포인트에서 재시작
        
        Args:
            checkpoint_dir: 체크포인트 디렉토리
            additional_steps: 추가 스텝 수
            
        Returns:
            MDEngine 인스턴스
        """
        checkpoint_path = Path(checkpoint_dir)
        
        # 구조 로드
        atoms = read(str(checkpoint_path / "checkpoint.xyz"))
        
        # 상태 로드
        with open(checkpoint_path / "checkpoint_state.json") as f:
            state_data = json.load(f)
            
        config = MDConfig.from_dict(state_data["config"])
        config.steps = additional_steps
        
        # 새 출력 디렉토리
        output_dir = checkpoint_path / f"continue_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return cls(atoms, config, str(output_dir))
