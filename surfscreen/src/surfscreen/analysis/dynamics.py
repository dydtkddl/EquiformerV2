"""
Dynamics Analysis Module

분자 동역학 트라젝토리 분석 도구
- MSD (Mean Square Displacement)
- 확산 계수 (Diffusion Coefficient)
- 이온 전도도 (Ionic Conductivity)
- RDF (Radial Distribution Function)
- VAF (Velocity Autocorrelation Function)
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from ase import Atoms
from ase.io import read
from ase.io.trajectory import Trajectory
from scipy import stats
from scipy.ndimage import uniform_filter1d


@dataclass
class MSDResult:
    """MSD 분석 결과"""
    time: np.ndarray  # fs
    msd: np.ndarray  # Å²
    msd_x: np.ndarray
    msd_y: np.ndarray
    msd_z: np.ndarray
    species: str
    
    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "time_fs": self.time.tolist(),
            "msd_A2": self.msd.tolist(),
            "msd_x_A2": self.msd_x.tolist(),
            "msd_y_A2": self.msd_y.tolist(),
            "msd_z_A2": self.msd_z.tolist()
        }


@dataclass
class DiffusionResult:
    """확산 계수 결과"""
    D: float  # cm²/s
    D_error: float  # cm²/s
    D_x: float
    D_y: float
    D_z: float
    r_squared: float
    fit_start: float  # fs
    fit_end: float  # fs
    species: str
    
    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "D_cm2_s": self.D,
            "D_error_cm2_s": self.D_error,
            "D_x_cm2_s": self.D_x,
            "D_y_cm2_s": self.D_y,
            "D_z_cm2_s": self.D_z,
            "r_squared": self.r_squared,
            "fit_range_fs": [self.fit_start, self.fit_end]
        }


@dataclass
class ConductivityResult:
    """이온 전도도 결과"""
    sigma: float  # S/cm
    sigma_error: float
    temperature: float  # K
    n_carriers: int
    charge: int
    volume: float  # Å³
    species: str
    
    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "conductivity_S_cm": self.sigma,
            "conductivity_error_S_cm": self.sigma_error,
            "temperature_K": self.temperature,
            "n_carriers": self.n_carriers,
            "charge": self.charge,
            "volume_A3": self.volume
        }


@dataclass
class RDFResult:
    """RDF 결과"""
    r: np.ndarray  # Å
    g_r: np.ndarray  # dimensionless
    pair: Tuple[str, str]
    coordination_number: float
    first_peak_r: float
    first_peak_g: float
    
    def to_dict(self) -> dict:
        return {
            "pair": list(self.pair),
            "r_A": self.r.tolist(),
            "g_r": self.g_r.tolist(),
            "coordination_number": self.coordination_number,
            "first_peak_r_A": self.first_peak_r,
            "first_peak_g": self.first_peak_g
        }


class DynamicsAnalyzer:
    """동역학 분석기"""
    
    def __init__(self, trajectory_path: str, timestep: float = 1.0):
        """
        Args:
            trajectory_path: 트라젝토리 파일 경로
            timestep: 시간 간격 (fs)
        """
        self.trajectory_path = Path(trajectory_path)
        self.timestep = timestep
        self.frames: List[Atoms] = []
        
        self._load_trajectory()
        
    def _load_trajectory(self):
        """트라젝토리 로드"""
        if self.trajectory_path.suffix == ".traj":
            self.frames = read(str(self.trajectory_path), index=":")
        elif self.trajectory_path.suffix in [".xyz", ".extxyz"]:
            self.frames = read(str(self.trajectory_path), index=":")
        else:
            raise ValueError(f"Unknown trajectory format: {self.trajectory_path.suffix}")
            
        print(f"Loaded {len(self.frames)} frames from {self.trajectory_path}")
    
    def get_species_indices(self, species: str) -> List[int]:
        """특정 종의 원자 인덱스"""
        if not self.frames:
            return []
        symbols = self.frames[0].get_chemical_symbols()
        return [i for i, s in enumerate(symbols) if s == species]
    
    def calculate_msd(self, 
                      species: str,
                      unwrap: bool = True) -> MSDResult:
        """MSD 계산
        
        Args:
            species: 원자 종류 (예: "Li", "O")
            unwrap: PBC unwrapping 여부
            
        Returns:
            MSDResult
        """
        indices = self.get_species_indices(species)
        if not indices:
            raise ValueError(f"No atoms of species {species} found")
            
        n_frames = len(self.frames)
        n_atoms = len(indices)
        
        # 위치 추출
        positions = np.zeros((n_frames, n_atoms, 3))
        for i, frame in enumerate(self.frames):
            positions[i] = frame.positions[indices]
            
        # PBC unwrapping
        if unwrap and self.frames[0].pbc.any():
            positions = self._unwrap_positions(positions, self.frames[0].get_cell())
            
        # MSD 계산
        initial_pos = positions[0]
        displacements = positions - initial_pos
        
        msd = np.mean(np.sum(displacements**2, axis=2), axis=1)
        msd_x = np.mean(displacements[:, :, 0]**2, axis=1)
        msd_y = np.mean(displacements[:, :, 1]**2, axis=1)
        msd_z = np.mean(displacements[:, :, 2]**2, axis=1)
        
        time = np.arange(n_frames) * self.timestep
        
        return MSDResult(
            time=time,
            msd=msd,
            msd_x=msd_x,
            msd_y=msd_y,
            msd_z=msd_z,
            species=species
        )
    
    def _unwrap_positions(self, 
                          positions: np.ndarray, 
                          cell: np.ndarray) -> np.ndarray:
        """PBC unwrapping"""
        unwrapped = positions.copy()
        cell_lengths = np.linalg.norm(cell, axis=1)
        
        for i in range(1, len(positions)):
            diff = positions[i] - positions[i-1]
            
            # 각 축에 대해 점프 감지
            for axis in range(3):
                jumps = np.round(diff[:, axis] / cell_lengths[axis])
                unwrapped[i:, :, axis] -= jumps * cell_lengths[axis]
                
        return unwrapped
    
    def calculate_diffusion(self,
                            species: str,
                            fit_start: float = 0.2,
                            fit_end: float = 0.8) -> DiffusionResult:
        """확산 계수 계산 (Einstein relation)
        
        D = lim(t→∞) MSD / (2*d*t)
        
        Args:
            species: 원자 종류
            fit_start: 피팅 시작점 (전체 시간의 비율)
            fit_end: 피팅 끝점 (전체 시간의 비율)
            
        Returns:
            DiffusionResult (cm²/s 단위)
        """
        msd_result = self.calculate_msd(species)
        
        time = msd_result.time
        msd = msd_result.msd
        
        # 피팅 범위
        n_points = len(time)
        start_idx = int(n_points * fit_start)
        end_idx = int(n_points * fit_end)
        
        t_fit = time[start_idx:end_idx]
        msd_fit = msd[start_idx:end_idx]
        
        # 선형 피팅: MSD = 6*D*t (3D)
        slope, intercept, r_value, p_value, std_err = stats.linregress(t_fit, msd_fit)
        
        # D = slope / 6 (3D)
        # 단위 변환: Å²/fs -> cm²/s
        # 1 Å² = 1e-16 cm², 1 fs = 1e-15 s
        # D [Å²/fs] * 1e-16 / 1e-15 = D * 0.1 [cm²/s]
        D = slope / 6.0 * 0.1  # cm²/s
        D_error = std_err / 6.0 * 0.1
        
        # 각 축 방향 확산 계수
        slope_x, _, _, _, _ = stats.linregress(t_fit, msd_result.msd_x[start_idx:end_idx])
        slope_y, _, _, _, _ = stats.linregress(t_fit, msd_result.msd_y[start_idx:end_idx])
        slope_z, _, _, _, _ = stats.linregress(t_fit, msd_result.msd_z[start_idx:end_idx])
        
        D_x = slope_x / 2.0 * 0.1
        D_y = slope_y / 2.0 * 0.1
        D_z = slope_z / 2.0 * 0.1
        
        return DiffusionResult(
            D=D,
            D_error=D_error,
            D_x=D_x,
            D_y=D_y,
            D_z=D_z,
            r_squared=r_value**2,
            fit_start=time[start_idx],
            fit_end=time[end_idx],
            species=species
        )
    
    def calculate_conductivity(self,
                               species: str,
                               charge: int,
                               temperature: float) -> ConductivityResult:
        """이온 전도도 계산 (Nernst-Einstein)
        
        σ = (n * e² * D) / (k * T)
        
        Args:
            species: 이온 종류
            charge: 전하 (예: Li+ = 1, O2- = -2)
            temperature: 온도 (K)
            
        Returns:
            ConductivityResult (S/cm 단위)
        """
        diffusion = self.calculate_diffusion(species)
        
        indices = self.get_species_indices(species)
        n_carriers = len(indices)
        
        # 부피 계산
        volume = self.frames[0].get_volume()  # Å³
        
        # 상수
        e = 1.602176634e-19  # C
        kB = 1.380649e-23  # J/K
        
        # 농도 n (1/cm³)
        # volume: Å³ = 1e-24 cm³
        n = n_carriers / (volume * 1e-24)  # 1/cm³
        
        # D: cm²/s
        D = diffusion.D
        D_error = diffusion.D_error
        
        # σ = n * z² * e² * D / (kB * T)
        # 단위: (1/cm³) * C² * (cm²/s) / (J/K * K) = S/cm
        z = abs(charge)
        sigma = n * z**2 * e**2 * D / (kB * temperature)
        sigma_error = n * z**2 * e**2 * D_error / (kB * temperature)
        
        return ConductivityResult(
            sigma=sigma,
            sigma_error=sigma_error,
            temperature=temperature,
            n_carriers=n_carriers,
            charge=charge,
            volume=volume,
            species=species
        )
    
    def calculate_rdf(self,
                      pair: Tuple[str, str],
                      r_max: float = 10.0,
                      n_bins: int = 200,
                      frame_step: int = 1) -> RDFResult:
        """RDF 계산
        
        Args:
            pair: 원자 쌍 (예: ("Li", "O"))
            r_max: 최대 거리 (Å)
            n_bins: 히스토그램 빈 수
            frame_step: 프레임 샘플링 간격
            
        Returns:
            RDFResult
        """
        species_a, species_b = pair
        
        indices_a = self.get_species_indices(species_a)
        indices_b = self.get_species_indices(species_b)
        
        if not indices_a or not indices_b:
            raise ValueError(f"Species not found: {pair}")
            
        dr = r_max / n_bins
        r_edges = np.linspace(0, r_max, n_bins + 1)
        r_centers = (r_edges[:-1] + r_edges[1:]) / 2
        
        hist_sum = np.zeros(n_bins)
        n_samples = 0
        
        for i, frame in enumerate(self.frames[::frame_step]):
            pos_a = frame.positions[indices_a]
            pos_b = frame.positions[indices_b]
            cell = frame.get_cell()
            
            # 거리 계산 (PBC 고려)
            for pa in pos_a:
                diff = pos_b - pa
                
                # Minimum image convention
                if frame.pbc.any():
                    for axis in range(3):
                        if frame.pbc[axis]:
                            diff[:, axis] -= np.round(diff[:, axis] / cell[axis, axis]) * cell[axis, axis]
                            
                distances = np.linalg.norm(diff, axis=1)
                
                # 같은 원자 제외
                if species_a == species_b:
                    distances = distances[distances > 0.1]
                    
                hist, _ = np.histogram(distances, bins=r_edges)
                hist_sum += hist
                
            n_samples += len(indices_a)
            
        # 정규화
        volume = self.frames[0].get_volume()
        n_b = len(indices_b)
        rho_b = n_b / volume
        
        # g(r) = hist / (4πr²dr * ρ_b * N_samples)
        shell_volumes = 4 * np.pi * r_centers**2 * dr
        g_r = hist_sum / (shell_volumes * rho_b * n_samples)
        
        # 첫 번째 피크 찾기
        first_peak_idx = np.argmax(g_r[g_r > 0])
        first_peak_r = r_centers[first_peak_idx] if first_peak_idx > 0 else 0
        first_peak_g = g_r[first_peak_idx] if first_peak_idx > 0 else 0
        
        # 배위수 계산 (첫 번째 minimum까지 적분)
        # 간단히 첫 번째 피크 이후의 minimum 찾기
        if first_peak_idx > 0:
            after_peak = g_r[first_peak_idx:]
            min_idx = np.argmin(after_peak) + first_peak_idx
            r_min = r_centers[min_idx]
            
            # CN = 4π ∫ r² g(r) ρ dr
            cn_integral = 4 * np.pi * np.trapz(
                r_centers[:min_idx]**2 * g_r[:min_idx] * rho_b,
                r_centers[:min_idx]
            )
        else:
            cn_integral = 0
        
        return RDFResult(
            r=r_centers,
            g_r=g_r,
            pair=pair,
            coordination_number=cn_integral,
            first_peak_r=first_peak_r,
            first_peak_g=first_peak_g
        )
    
    def calculate_vaf(self, species: str) -> Dict:
        """속도 자기상관 함수 (VAF) 계산
        
        Args:
            species: 원자 종류
            
        Returns:
            VAF 결과 딕셔너리
        """
        indices = self.get_species_indices(species)
        if not indices:
            raise ValueError(f"No atoms of species {species} found")
            
        n_frames = len(self.frames)
        
        # 속도 추출 (유한 차분)
        velocities = []
        for i in range(1, n_frames):
            pos_prev = self.frames[i-1].positions[indices]
            pos_curr = self.frames[i].positions[indices]
            v = (pos_curr - pos_prev) / self.timestep
            velocities.append(v)
            
        velocities = np.array(velocities)  # (n_frames-1, n_atoms, 3)
        
        # VAF 계산
        n_steps = len(velocities)
        max_lag = min(n_steps // 2, 1000)
        
        vaf = np.zeros(max_lag)
        
        for lag in range(max_lag):
            v0 = velocities[:n_steps-lag]
            vt = velocities[lag:]
            
            # <v(0) · v(t)>
            dot_products = np.sum(v0 * vt, axis=2)  # (n_frames, n_atoms)
            vaf[lag] = np.mean(dot_products)
            
        # 정규화
        vaf = vaf / vaf[0] if vaf[0] != 0 else vaf
        
        time = np.arange(max_lag) * self.timestep
        
        return {
            "time_fs": time.tolist(),
            "vaf": vaf.tolist(),
            "species": species
        }
    
    def calculate_density_profile(self, 
                                   species: str,
                                   axis: int = 2,
                                   n_bins: int = 100) -> Dict:
        """밀도 프로파일 계산
        
        Args:
            species: 원자 종류
            axis: 방향 (0=x, 1=y, 2=z)
            n_bins: 빈 수
            
        Returns:
            밀도 프로파일 딕셔너리
        """
        indices = self.get_species_indices(species)
        if not indices:
            raise ValueError(f"No atoms of species {species} found")
            
        cell = self.frames[0].get_cell()
        cell_length = cell[axis, axis]
        
        hist_sum = np.zeros(n_bins)
        
        for frame in self.frames:
            coords = frame.positions[indices, axis]
            hist, edges = np.histogram(coords, bins=n_bins, range=(0, cell_length))
            hist_sum += hist
            
        # 평균
        density = hist_sum / len(self.frames)
        bin_centers = (edges[:-1] + edges[1:]) / 2
        
        # 정규화 (원자/Å)
        bin_width = cell_length / n_bins
        cross_section = np.prod([cell[i, i] for i in range(3) if i != axis])
        density = density / (bin_width * cross_section)
        
        axis_labels = ["x", "y", "z"]
        
        return {
            "position_A": bin_centers.tolist(),
            "density_per_A3": density.tolist(),
            "axis": axis_labels[axis],
            "species": species
        }
