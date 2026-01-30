"""
SurfScreen Templates Module

워크플로우 템플릿 시스템
"""

import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import subprocess
import shlex


@dataclass
class TemplateStep:
    """템플릿 단일 스텝"""
    name: str
    command: str
    description: str = ""
    continue_on_error: bool = False
    timeout: int = 3600  # 초
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowTemplate:
    """워크플로우 템플릿"""
    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    steps: List[TemplateStep] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, path: str) -> "WorkflowTemplate":
        """YAML 파일에서 로드"""
        with open(path) as f:
            data = yaml.safe_load(f)
            
        steps = []
        for step_data in data.get("steps", []):
            steps.append(TemplateStep(**step_data))
            
        return cls(
            name=data.get("name", Path(path).stem),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            author=data.get("author", ""),
            variables=data.get("variables", {}),
            steps=steps
        )
    
    def to_yaml(self, path: str):
        """YAML 파일로 저장"""
        data = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "variables": self.variables,
            "steps": [
                {
                    "name": step.name,
                    "command": step.command,
                    "description": step.description,
                    "continue_on_error": step.continue_on_error,
                    "timeout": step.timeout,
                }
                for step in self.steps
            ]
        }
        
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


class TemplateEngine:
    """템플릿 엔진"""
    
    TEMPLATES_DIR = Path.home() / ".surfscreen" / "templates"
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Args:
            templates_dir: 템플릿 디렉토리 (기본: ~/.surfscreen/templates)
        """
        self.templates_dir = Path(templates_dir) if templates_dir else self.TEMPLATES_DIR
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
    def list_templates(self) -> List[Dict[str, str]]:
        """사용 가능한 템플릿 목록"""
        templates = []
        
        for path in self.templates_dir.glob("*.yaml"):
            try:
                template = WorkflowTemplate.from_yaml(str(path))
                templates.append({
                    "name": template.name,
                    "description": template.description,
                    "path": str(path),
                    "version": template.version
                })
            except Exception:
                continue
                
        return templates
    
    def get_template(self, name: str) -> WorkflowTemplate:
        """템플릿 가져오기"""
        # 이름으로 검색
        path = self.templates_dir / f"{name}.yaml"
        if path.exists():
            return WorkflowTemplate.from_yaml(str(path))
            
        # 전체 경로인 경우
        if Path(name).exists():
            return WorkflowTemplate.from_yaml(name)
            
        raise FileNotFoundError(f"Template not found: {name}")
    
    def save_template(self, template: WorkflowTemplate) -> str:
        """템플릿 저장"""
        path = self.templates_dir / f"{template.name}.yaml"
        template.to_yaml(str(path))
        return str(path)
    
    def render_command(self, command: str, variables: Dict[str, Any]) -> str:
        """변수를 치환하여 명령어 렌더링
        
        Args:
            command: 템플릿 명령어 (예: "surfscreen surface create ${element}")
            variables: 변수 딕셔너리
            
        Returns:
            렌더링된 명령어
        """
        result = command
        
        # ${var} 형식 치환
        for key, value in variables.items():
            pattern = r'\$\{' + re.escape(key) + r'\}'
            result = re.sub(pattern, str(value), result)
            
        # $var 형식 치환
        for key, value in variables.items():
            pattern = r'\$' + re.escape(key) + r'(?![a-zA-Z0-9_])'
            result = re.sub(pattern, str(value), result)
            
        return result
    
    def run_template(self, 
                     template: Union[str, WorkflowTemplate],
                     variables: Optional[Dict[str, Any]] = None,
                     dry_run: bool = False,
                     output_dir: Optional[str] = None) -> Dict[str, Any]:
        """템플릿 실행
        
        Args:
            template: 템플릿 이름 또는 객체
            variables: 변수 오버라이드
            dry_run: 실제 실행 없이 명령어 출력만
            output_dir: 작업 디렉토리
            
        Returns:
            실행 결과
        """
        if isinstance(template, str):
            template = self.get_template(template)
            
        # 변수 병합 (기본값 + 오버라이드)
        final_vars = {**template.variables, **(variables or {})}
        
        results = {
            "template": template.name,
            "variables": final_vars,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "success": True
        }
        
        work_dir = Path(output_dir) if output_dir else Path.cwd()
        
        for i, step in enumerate(template.steps):
            step_result = {
                "name": step.name,
                "command": step.command,
                "rendered": self.render_command(step.command, final_vars),
                "status": "pending"
            }
            
            if dry_run:
                step_result["status"] = "dry_run"
                print(f"[{i+1}/{len(template.steps)}] {step.name}")
                print(f"    $ {step_result['rendered']}")
            else:
                print(f"[{i+1}/{len(template.steps)}] {step.name}...")
                
                try:
                    proc = subprocess.run(
                        step_result["rendered"],
                        shell=True,
                        cwd=work_dir,
                        capture_output=True,
                        text=True,
                        timeout=step.timeout
                    )
                    
                    step_result["stdout"] = proc.stdout
                    step_result["stderr"] = proc.stderr
                    step_result["returncode"] = proc.returncode
                    
                    if proc.returncode == 0:
                        step_result["status"] = "success"
                        print(f"    ✅ Success")
                    else:
                        step_result["status"] = "failed"
                        print(f"    ❌ Failed (exit code: {proc.returncode})")
                        
                        if not step.continue_on_error:
                            results["success"] = False
                            results["steps"].append(step_result)
                            break
                            
                except subprocess.TimeoutExpired:
                    step_result["status"] = "timeout"
                    print(f"    ⏰ Timeout ({step.timeout}s)")
                    
                    if not step.continue_on_error:
                        results["success"] = False
                        results["steps"].append(step_result)
                        break
                        
                except Exception as e:
                    step_result["status"] = "error"
                    step_result["error"] = str(e)
                    print(f"    ❌ Error: {e}")
                    
                    if not step.continue_on_error:
                        results["success"] = False
                        results["steps"].append(step_result)
                        break
                        
            results["steps"].append(step_result)
            
        results["end_time"] = datetime.now().isoformat()
        return results


# 기본 템플릿 정의
DEFAULT_TEMPLATES = {
    "basic_screening": WorkflowTemplate(
        name="basic_screening",
        description="Basic adsorption screening workflow",
        variables={
            "element": "Cu",
            "miller": "111",
            "molecule": "water",
            "engine": "mace"
        },
        steps=[
            TemplateStep(
                name="Create surface",
                command="surfscreen surface create ${element} --miller ${miller} --layers 4 --supercell 3x3x1 -o surface.xyz"
            ),
            TemplateStep(
                name="Fetch molecule",
                command="surfscreen molecule from-pubchem ${molecule} -o molecule.xyz"
            ),
            TemplateStep(
                name="Run screening",
                command="surfscreen screen run -s surface.xyz -m molecule.xyz --engine ${engine} -o results/"
            ),
            TemplateStep(
                name="Generate report",
                command="surfscreen screen report results/ -o report.html"
            )
        ]
    ),
    "md_simulation": WorkflowTemplate(
        name="md_simulation",
        description="MD simulation with analysis",
        variables={
            "structure": "structure.xyz",
            "temperature": "300",
            "steps": "10000",
            "engine": "mace"
        },
        steps=[
            TemplateStep(
                name="Run MD",
                command="surfscreen md run ${structure} --ensemble nvt -T ${temperature} -n ${steps} --engine ${engine} -o md_output/"
            ),
            TemplateStep(
                name="Analyze MSD",
                command="surfscreen analysis msd md_output/trajectory.traj -o msd.html",
                continue_on_error=True
            ),
            TemplateStep(
                name="Generate MD report",
                command="surfscreen md report md_output/ -o md_report.html"
            )
        ]
    )
}


def install_default_templates(engine: Optional[TemplateEngine] = None):
    """기본 템플릿 설치"""
    engine = engine or TemplateEngine()
    
    for template in DEFAULT_TEMPLATES.values():
        engine.save_template(template)
        print(f"✓ Installed: {template.name}")
