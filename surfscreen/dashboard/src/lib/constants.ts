// App Constants

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'SurfScreen Dashboard';
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';
export const POLLING_INTERVAL = parseInt(process.env.NEXT_PUBLIC_POLLING_INTERVAL || '5000');

// Calculator Engines
export const ENGINES = ['mace', 'xtb', 'emt'] as const;
export const MACE_MODELS = ['small', 'medium', 'large'] as const;
export const DEVICES = ['cuda', 'cpu'] as const;

// MD Settings
export const ENSEMBLES = ['nvt', 'npt', 'nve'] as const;
export const THERMOSTATS = ['langevin', 'berendsen', 'nose_hoover'] as const;

// Default Configurations
export const DEFAULT_SCREENING_CONFIG = {
  engine: 'mace',
  model: 'medium',
  device: 'cuda',
  rotations: [0, 45, 90, 135],
  heights: [1.5, 2.0, 2.5],
  max_configs: 50,
  fix_layers: 2,
  fmax: 0.05,
  steps: 500
};

export type Ensemble = 'nvt' | 'npt' | 'nve';
export type Thermostat = 'langevin' | 'berendsen' | 'nose_hoover';

export interface MDConfigType {
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

export const DEFAULT_MD_CONFIG: MDConfigType = {
  ensemble: 'nvt',
  temperature: 300,
  pressure: 1.0,
  timestep: 1.0,
  steps: 10000,
  thermostat: 'langevin',
  engine: 'mace',
  model: 'medium',
  device: 'cuda',
  log_interval: 100,
  traj_interval: 100
};

// Status Labels
export const STATUS_LABELS: Record<string, string> = {
  pending: '대기 중',
  running: '실행 중',
  completed: '완료',
  failed: '실패',
  cancelled: '취소됨'
};

export const JOB_TYPE_LABELS: Record<string, string> = {
  screening: '스크리닝',
  md: 'MD 시뮬레이션',
  analysis: '분석'
};

// File Extensions
export const ALLOWED_EXTENSIONS = ['.xyz', '.poscar', '.cif', '.pdb', '.extxyz', '.vasp'];

// Navigation
export const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: 'Home' },
  { href: '/screening', label: 'Screening', icon: 'Zap' },
  { href: '/md', label: 'MD Simulation', icon: 'Activity' },
  { href: '/jobs', label: 'All Jobs', icon: 'List' },
  { href: '/settings', label: 'Settings', icon: 'Settings' }
] as const;
