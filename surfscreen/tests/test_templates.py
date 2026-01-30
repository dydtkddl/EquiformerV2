"""
Test Templates Module
"""

import pytest
import yaml
from pathlib import Path

from surfscreen.templates import (
    TemplateEngine,
    WorkflowTemplate,
    TemplateStep,
    DEFAULT_TEMPLATES,
    install_default_templates
)


@pytest.fixture
def templates_dir(tmp_path):
    """템플릿 디렉토리"""
    return tmp_path / "templates"


def test_workflow_template_creation():
    """워크플로우 템플릿 생성 테스트"""
    template = WorkflowTemplate(
        name="test_workflow",
        description="Test workflow",
        variables={"element": "Cu"},
        steps=[
            TemplateStep(name="Step 1", command="echo ${element}")
        ]
    )
    
    assert template.name == "test_workflow"
    assert len(template.steps) == 1
    assert template.variables["element"] == "Cu"


def test_template_to_yaml(tmp_path):
    """YAML 저장 테스트"""
    template = WorkflowTemplate(
        name="test",
        description="Test",
        steps=[TemplateStep(name="s1", command="echo hello")]
    )
    
    path = tmp_path / "test.yaml"
    template.to_yaml(str(path))
    
    assert path.exists()
    
    with open(path) as f:
        data = yaml.safe_load(f)
    assert data["name"] == "test"
    assert len(data["steps"]) == 1


def test_template_from_yaml(tmp_path):
    """YAML 로드 테스트"""
    data = {
        "name": "loaded_template",
        "description": "Loaded",
        "version": "2.0",
        "variables": {"var1": "value1"},
        "steps": [
            {"name": "Step1", "command": "echo ${var1}"}
        ]
    }
    
    path = tmp_path / "template.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
        
    template = WorkflowTemplate.from_yaml(str(path))
    
    assert template.name == "loaded_template"
    assert template.version == "2.0"
    assert template.variables["var1"] == "value1"


def test_template_engine_render():
    """변수 치환 테스트"""
    engine = TemplateEngine()
    
    command = "surfscreen surface create ${element} --miller ${miller}"
    variables = {"element": "Cu", "miller": "111"}
    
    rendered = engine.render_command(command, variables)
    
    assert rendered == "surfscreen surface create Cu --miller 111"


def test_template_engine_render_dollar():
    """$ 형식 변수 치환 테스트"""
    engine = TemplateEngine()
    
    command = "echo $name is $value"
    variables = {"name": "test", "value": "123"}
    
    rendered = engine.render_command(command, variables)
    
    assert rendered == "echo test is 123"


def test_template_engine_list(templates_dir):
    """템플릿 목록 테스트"""
    engine = TemplateEngine(str(templates_dir))
    
    # 빈 목록
    assert len(engine.list_templates()) == 0
    
    # 템플릿 저장
    template = WorkflowTemplate(name="test1", description="Test 1")
    engine.save_template(template)
    
    templates = engine.list_templates()
    assert len(templates) == 1
    assert templates[0]["name"] == "test1"


def test_template_dry_run(templates_dir):
    """드라이런 테스트"""
    engine = TemplateEngine(str(templates_dir))
    
    template = WorkflowTemplate(
        name="dry_test",
        steps=[
            TemplateStep(name="Step1", command="echo hello"),
            TemplateStep(name="Step2", command="echo world"),
        ]
    )
    engine.save_template(template)
    
    result = engine.run_template("dry_test", dry_run=True)
    
    assert result["success"] == True
    assert len(result["steps"]) == 2
    for step in result["steps"]:
        assert step["status"] == "dry_run"


def test_default_templates():
    """기본 템플릿 존재 확인"""
    assert "basic_screening" in DEFAULT_TEMPLATES
    assert "md_simulation" in DEFAULT_TEMPLATES
    
    basic = DEFAULT_TEMPLATES["basic_screening"]
    assert len(basic.steps) > 0
    assert "element" in basic.variables


def test_install_default_templates(templates_dir):
    """기본 템플릿 설치 테스트"""
    engine = TemplateEngine(str(templates_dir))
    install_default_templates(engine)
    
    templates = engine.list_templates()
    names = [t["name"] for t in templates]
    
    assert "basic_screening" in names
    assert "md_simulation" in names
