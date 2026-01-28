#!/usr/bin/env python3
"""
DockOnSurf + MACE/CP2K Unified Pipeline
WSL 및 Linux HPC 클러스터 호환
"""
import argparse
import subprocess
import shutil
import yaml
import os
from pathlib import Path
from string import Template
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PipelineConfig:
    """YAML 설정 파일 로더"""
    
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self._expand_env_vars()
    
    def _expand_env_vars(self):
        """${VAR} 형식의 환경변수 확장"""
        def expand(obj):
            if isinstance(obj, str):
                return os.path.expandvars(obj)
            elif isinstance(obj, dict):
                return {k: expand(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [expand(v) for v in obj]
            return obj
        self.config = expand(self.config)
    
    def get(self, key: str, default=None):
        """Dot notation으로 중첩 키 접근"""
        keys = key.split('.')
        val = self.config
        for k in keys:
            if val is None:
                return default
            val = val.get(k, default) if isinstance(val, dict) else default
        return val


class DockOnSurfRunner:
    """DockOnSurf 실행 래퍼"""
    
    def __init__(self, config: PipelineConfig, work_dir: Path):
        self.config = config
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_dos_input(self, run_type: str, calculator: str) -> Path:
        """DockOnSurf 입력 파일 생성"""
        
        inp_content = f"""# Auto-generated DockOnSurf input file
[Global]
project_name = {self.config.get('project.name', 'project')}
run_type = {run_type}
code = {calculator}
"""
        
        if calculator == "mace":
            inp_content += f"model_mace = {self.config.get('mace.model_path')}\n"
        
        # Isolated 섹션
        if "isolated" in run_type:
            inp_content += f"""
[Isolated]
isol_inp_file = mace_input.yaml
molec_file = {self.config.get('inputs.molecule_file')}
num_conformers = {self.config.get('dockonsurf.num_conformers', 30)}
pre_opt = {self.config.get('dockonsurf.pre_opt', 'MMFF')}
"""
        
        # Screening 섹션
        if "screening" in run_type:
            screen_inp = 'mace_input.yaml' if calculator == 'mace' else 'screening.inp'
            inp_content += f"""
[Screening]
screen_inp_file = {screen_inp}
surf_file = {self.config.get('inputs.surface_file')}
set_angles = euler
sample_points_per_angle = {self.config.get('dockonsurf.sample_points_per_angle', 6)}
sites = auto
molec_ctrs = auto
select_magns = energy MOI
confs_per_magn = 2
adsorption_height = {self.config.get('dockonsurf.adsorption_height', 2.5)}
collision_threshold = {self.config.get('dockonsurf.collision_threshold', 0.9)}
max_structures = {self.config.get('dockonsurf.max_structures', 100)}
"""
        
        # Refinement 섹션
        if "refinement" in run_type:
            refine_inp = 'mace_input.yaml' if calculator == 'mace' else 'refinement.inp'
            inp_content += f"""
[Refinement]
refine_inp_file = {refine_inp}
energy_cutoff = {self.config.get('dockonsurf.energy_cutoff', 0.5)}
"""
        
        inp_path = self.work_dir / f"DOS_{calculator}.inp"
        inp_path.write_text(inp_content)
        logger.info(f"Generated DockOnSurf input: {inp_path}")
        return inp_path
    
    def generate_mace_yaml(self) -> Path:
        """MACE 설정 YAML 생성"""
        cell = self.config.get('cell')
        
        mace_config = {
            'optimizer': 'BFGS',
            'fmax': 0.05,
            'max_steps': 200,
        }
        
        if cell:
            mace_config['pbc'] = [cell['a'], cell['b'], cell['c']]
        
        yaml_path = self.work_dir / "mace_input.yaml"
        with open(yaml_path, 'w') as f:
            yaml.dump(mace_config, f, default_flow_style=False)
        
        logger.info(f"Generated MACE config: {yaml_path}")
        return yaml_path
    
    def generate_cp2k_input(self, template_path: Path) -> Path:
        """CP2K 입력 파일 생성 (템플릿 변수 치환)"""
        
        with open(template_path) as f:
            template = Template(f.read())
        
        cell = self.config.get('cell', {})
        
        substitutions = {
            'PROJECT_NAME': self.config.get('project.name', 'project'),
            'BASIS_SET_FILE': self.config.get('cp2k.basis_set_file', ''),
            'POTENTIAL_FILE': self.config.get('cp2k.potential_file', ''),
            'DFTD3_FILE': self.config.get('cp2k.dftd3_file', ''),
            'XC_FUNCTIONAL': self.config.get('cp2k.xc_functional', 'PBE'),
            'CUTOFF': self.config.get('cp2k.cutoff', 400),
            'SCF_EPS': self.config.get('cp2k.scf_eps', '1.0E-6'),
            'CELL_A': ' '.join(map(str, cell.get('a', [15.0, 0.0, 0.0]))),
            'CELL_B': ' '.join(map(str, cell.get('b', [0.0, 15.0, 0.0]))),
            'CELL_C': ' '.join(map(str, cell.get('c', [0.0, 0.0, 25.0]))),
            'PERIODIC': cell.get('periodic', 'XYZ'),
        }
        
        content = template.safe_substitute(substitutions)
        
        inp_path = self.work_dir / "screening.inp"
        inp_path.write_text(content)
        logger.info(f"Generated CP2K input: {inp_path}")
        
        # refinement.inp도 같이 생성 (동일 내용)
        refinement_path = self.work_dir / "refinement.inp"
        refinement_path.write_text(content)
        
        return inp_path
    
    def copy_input_files(self):
        """분자/표면 파일 복사"""
        mol_file = Path(self.config.get('inputs.molecule_file', ''))
        surf_file = Path(self.config.get('inputs.surface_file', ''))
        
        if mol_file.exists():
            shutil.copy(mol_file, self.work_dir / mol_file.name)
            logger.info(f"Copied molecule file: {mol_file}")
        
        if surf_file.exists():
            shutil.copy(surf_file, self.work_dir / surf_file.name)
            logger.info(f"Copied surface file: {surf_file}")
    
    def run(self, calculator: str, run_type: str = "isolated,screening,refinement", 
            dry_run: bool = False):
        """파이프라인 실행"""
        
        dos_conda = self.config.get('environment.dockonsurf_conda', 'dockonsurf')
        
        # 입력 파일 생성
        dos_inp = self.generate_dos_input(run_type, calculator)
        
        if calculator == "mace":
            self.generate_mace_yaml()
        else:
            template = Path(__file__).parent / "config" / "cp2k_template.inp"
            if template.exists():
                self.generate_cp2k_input(template)
            else:
                logger.warning(f"CP2K template not found: {template}")
        
        # DockOnSurf 실행 명령어
        cmd = f"conda run -n {dos_conda} dockonsurf.py {dos_inp.name}"
        logger.info(f"Command: {cmd}")
        logger.info(f"Working directory: {self.work_dir}")
        
        if dry_run:
            logger.info("Dry run - skipping execution")
            return None
        
        result = subprocess.run(
            cmd, shell=True, cwd=self.work_dir,
            capture_output=True, text=True
        )
        
        # 로그 저장
        log_path = self.work_dir / f"run_{calculator}.log"
        with open(log_path, 'w') as f:
            f.write(f"=== STDOUT ===\n{result.stdout}\n")
            f.write(f"=== STDERR ===\n{result.stderr}\n")
            f.write(f"=== RETURN CODE: {result.returncode} ===\n")
        
        if result.returncode != 0:
            logger.error(f"DockOnSurf failed. Check log: {log_path}")
        else:
            logger.info(f"DockOnSurf completed. Log: {log_path}")
        
        return result


def main():
    parser = argparse.ArgumentParser(
        description="DockOnSurf Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # MACE로 전체 파이프라인 실행
  python run_pipeline.py -c config/pipeline_config.yaml --calc mace
  
  # CP2K로 refinement만 실행
  python run_pipeline.py -c config/pipeline_config.yaml --calc cp2k --run-type refinement
  
  # Dry run (입력 파일만 생성, 실행 안함)
  python run_pipeline.py -c config/pipeline_config.yaml --dry-run
        """
    )
    parser.add_argument("--config", "-c", required=True, help="Path to pipeline_config.yaml")
    parser.add_argument("--calc", choices=["mace", "cp2k", "both"], default="mace",
                        help="Calculator to use (default: mace)")
    parser.add_argument("--run-type", default="isolated,screening,refinement",
                        help="DockOnSurf run types (comma-separated)")
    parser.add_argument("--work-dir", "-w", type=Path, default=Path("./work"),
                        help="Working directory (default: ./work)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate input files only, don't run")
    args = parser.parse_args()
    
    config = PipelineConfig(args.config)
    runner = DockOnSurfRunner(config, args.work_dir)
    
    if args.calc == "both":
        # MACE 먼저, 그 다음 CP2K
        logger.info("=" * 50)
        logger.info("Phase 1: MACE Pre-screening")
        logger.info("=" * 50)
        runner.run("mace", args.run_type, dry_run=args.dry_run)
        
        logger.info("=" * 50)
        logger.info("Phase 2: CP2K Refinement")
        logger.info("=" * 50)
        # CP2K는 refinement만
        runner.run("cp2k", "refinement", dry_run=args.dry_run)
    else:
        runner.run(args.calc, args.run_type, dry_run=args.dry_run)
    
    logger.info("Pipeline finished")


if __name__ == "__main__":
    main()
