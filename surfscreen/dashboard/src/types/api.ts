// API Response Types for SurfScreen Dashboard

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type JobType = 'screening' | 'md' | 'analysis';
export type Ensemble = 'nvt' | 'npt' | 'nve';
export type Thermostat = 'langevin' | 'berendsen' | 'nose_hoover';

export interface Job {
  job_id: string;
  job_type: JobType;
  status: JobStatus;
  progress: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  result_path: string | null;
}

export interface ScreeningConfig {
  engine: string;
  model: string;
  device: string;
  rotations: number[];
  heights: number[];
  max_configs: number;
  fix_layers: number;
  fmax: number;
  steps: number;
}

export interface MDConfig {
  ensemble: Ensemble;
  temperature: number;
  pressure: number;
  timestep: number;
  steps: number;
  thermostat: Thermostat;
  engine: string;
  model: string;
  device: string;
  log_interval: number;
  traj_interval: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
  engines: string[];
}

export interface ReadinessStatus {
  ready: boolean;
  checks: Record<string, boolean>;
}

export interface JobListResponse {
  total: number;
  jobs: Job[];
}

export interface JobCreateResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface ScreeningResult {
  job_id: string;
  total_configs: number;
  converged_configs: number;
  best_e_ads: number;
  avg_e_ads: number;
  top_results: ScreeningResultItem[];
  completed_at: string;
}

export interface ScreeningResultItem {
  name: string;
  e_ads: number;
  height: number;
  site_type: string;
  converged: boolean;
}

export interface MDResult {
  job_id: string;
  total_steps: number;
  total_time_fs: number;
  avg_temperature: number;
  final_energy: number;
  trajectory_frames: number;
  completed_at: string;
}

export interface ApiError {
  detail: string;
  code?: string;
  timestamp?: string;
}
