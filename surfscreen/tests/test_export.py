"""
Test Export Module
"""

import pytest
import json
import tempfile
from pathlib import Path

from surfscreen.export import ExportManager, ExportConfig


@pytest.fixture
def sample_results_dir(tmp_path):
    """샘플 결과 디렉토리 생성"""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    
    # results.json 생성
    results = {
        "results": [
            {"name": "config1", "e_ads": -1.5, "height": 2.0},
            {"name": "config2", "e_ads": -1.2, "height": 2.5},
            {"name": "config3", "e_ads": -1.8, "height": 1.8},
        ],
        "summary": {"best_energy": -1.8, "total_configs": 3}
    }
    
    with open(results_dir / "results.json", "w") as f:
        json.dump(results, f)
        
    return results_dir


def test_export_manager_load(sample_results_dir):
    """ExportManager 로드 테스트"""
    manager = ExportManager(str(sample_results_dir))
    
    assert len(manager.data["results"]) == 3
    assert manager.data["summary"]["best_energy"] == -1.8


def test_export_to_csv(sample_results_dir, tmp_path):
    """CSV 내보내기 테스트"""
    manager = ExportManager(str(sample_results_dir))
    output = tmp_path / "export.csv"
    
    result = manager.to_csv(str(output))
    
    assert Path(result).exists()
    content = Path(result).read_text()
    assert "name" in content
    assert "config1" in content
    assert "-1.5" in content


def test_export_to_json(sample_results_dir, tmp_path):
    """JSON 내보내기 테스트"""
    manager = ExportManager(str(sample_results_dir))
    output = tmp_path / "export.json"
    
    result = manager.to_json(str(output))
    
    assert Path(result).exists()
    with open(result) as f:
        data = json.load(f)
    assert "results" in data
    assert len(data["results"]) == 3


def test_export_to_zip(sample_results_dir, tmp_path):
    """ZIP 내보내기 테스트"""
    config = ExportConfig(include_structures=False, include_trajectories=False)
    manager = ExportManager(str(sample_results_dir), config)
    output = tmp_path / "export.zip"
    
    result = manager.to_zip(str(output))
    
    assert Path(result).exists()
    assert Path(result).stat().st_size > 0


def test_export_config_defaults():
    """ExportConfig 기본값 테스트"""
    config = ExportConfig()
    
    assert config.include_structures == False
    assert config.include_plots == True
    assert config.decimal_places == 6
