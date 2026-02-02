"""
Test Report Module

MDReportGenerator, ScreeningReportGenerator 테스트
"""

import pytest
import json
from pathlib import Path


class TestReportImports:
    """Report 모듈 import 테스트"""
    
    def test_import_base_report_generator(self):
        """BaseReportGenerator import 확인"""
        from surfscreen.report.base import BaseReportGenerator
        assert BaseReportGenerator is not None
    
    def test_import_md_report_generator(self):
        """MDReportGenerator import 확인"""
        from surfscreen.report import MDReportGenerator
        assert MDReportGenerator is not None
    
    def test_import_screening_report_generator(self):
        """ScreeningReportGenerator import 확인"""
        from surfscreen.report import ScreeningReportGenerator
        assert ScreeningReportGenerator is not None


class TestBaseReportGenerator:
    """BaseReportGenerator 테스트"""
    
    def test_css_variables_defined(self):
        """CSS 변수가 정의되어 있는지"""
        from surfscreen.report.base import BaseReportGenerator
        
        assert "--bg-primary" in BaseReportGenerator.CSS_VARIABLES
        assert "--text-primary" in BaseReportGenerator.CSS_VARIABLES
        assert "--accent-primary" in BaseReportGenerator.CSS_VARIABLES
    
    def test_cdn_urls_defined(self):
        """CDN URL이 정의되어 있는지"""
        from surfscreen.report.base import BaseReportGenerator
        
        assert "plotly" in BaseReportGenerator.PLOTLY_CDN.lower()
        assert "3dmol" in BaseReportGenerator.THREEDMOL_CDN.lower()
    
    def test_base_js_has_theme_toggle(self):
        """테마 토글 함수가 있는지"""
        from surfscreen.report.base import BaseReportGenerator
        
        assert "toggleTheme" in BaseReportGenerator.BASE_JS
        assert "localStorage" in BaseReportGenerator.BASE_JS
    
    def test_format_energy(self):
        """에너지 포맷팅"""
        from surfscreen.report.base import BaseReportGenerator
        
        # 일반 값
        assert BaseReportGenerator.format_energy(-1.234) == "-1.234"
        # 작은 값
        assert BaseReportGenerator.format_energy(0.0012) == "0.0012"
    
    def test_sanitize_html(self):
        """HTML 이스케이프"""
        from surfscreen.report.base import BaseReportGenerator
        
        assert BaseReportGenerator.sanitize_html("<script>") == "&lt;script&gt;"
        assert BaseReportGenerator.sanitize_html("a & b") == "a &amp; b"


class TestMDReportGenerator:
    """MDReportGenerator 테스트"""
    
    def test_init_with_nonexistent_dir(self, tmp_path):
        """존재하지 않는 디렉토리로 초기화"""
        from surfscreen.report import MDReportGenerator
        
        nonexistent = tmp_path / "nonexistent"
        gen = MDReportGenerator(str(nonexistent))
        
        # 데이터는 비어있음
        assert gen.data["summary"] == {}
        assert gen.data["log"] == []
        assert gen.data["frames"] == []
    
    def test_init_with_mock_data(self, tmp_path):
        """Mock 데이터로 초기화"""
        from surfscreen.report import MDReportGenerator
        
        # 샘플 summary.json 생성
        summary = {
            "total_steps": 1000,
            "total_time_fs": 1000.0,
            "avg_temperature_K": 300.0
        }
        (tmp_path / "summary.json").write_text(json.dumps(summary))
        
        # 샘플 md.log 생성
        log_content = "# step time temperature e_pot e_kin e_tot\n"
        log_content += "0 0.0 300.0 -100.0 0.5 -99.5\n"
        log_content += "100 100.0 305.0 -99.8 0.55 -99.25\n"
        (tmp_path / "md.log").write_text(log_content)
        
        gen = MDReportGenerator(str(tmp_path))
        
        assert gen.data["summary"]["total_steps"] == 1000
        assert len(gen.data["log"]) == 2
    
    def test_generate_html(self, tmp_path):
        """HTML 생성"""
        from surfscreen.report import MDReportGenerator
        
        # 샘플 데이터
        summary = {"total_steps": 100, "total_time_fs": 100.0, "avg_temperature_K": 300.0}
        (tmp_path / "summary.json").write_text(json.dumps(summary))
        
        gen = MDReportGenerator(str(tmp_path))
        output_path = tmp_path / "test_report.html"
        
        result = gen.generate(str(output_path))
        
        assert Path(result).exists()
        html = Path(result).read_text()
        
        # 필수 요소 확인
        assert "<!DOCTYPE html>" in html
        assert "3Dmol" in html
        assert "Plotly" in html
        assert "toggleTheme" in html
    
    def test_theme_option(self, tmp_path):
        """테마 옵션"""
        from surfscreen.report import MDReportGenerator
        
        (tmp_path / "summary.json").write_text("{}")
        
        gen_dark = MDReportGenerator(str(tmp_path), theme="dark")
        gen_light = MDReportGenerator(str(tmp_path), theme="light")
        
        assert gen_dark.theme == "dark"
        assert gen_light.theme == "light"


class TestScreeningReportGenerator:
    """ScreeningReportGenerator 테스트"""
    
    def test_init_with_nonexistent_dir(self, tmp_path):
        """존재하지 않는 디렉토리로 초기화"""
        from surfscreen.report import ScreeningReportGenerator
        
        nonexistent = tmp_path / "nonexistent"
        gen = ScreeningReportGenerator(str(nonexistent))
        
        assert gen.data["results"] == []
    
    def test_init_with_mock_results(self, tmp_path):
        """Mock 결과로 초기화"""
        from surfscreen.report import ScreeningReportGenerator
        
        # 샘플 results.json 생성
        results = {
            "results": [
                {"name": "config_001", "e_ads": -1.5, "height": 2.0, "site_type": "top"},
                {"name": "config_002", "e_ads": -1.2, "height": 2.5, "site_type": "bridge"},
                {"name": "config_003", "e_ads": -0.8, "height": 3.0, "site_type": "hollow"}
            ]
        }
        (tmp_path / "results.json").write_text(json.dumps(results))
        
        gen = ScreeningReportGenerator(str(tmp_path))
        
        # 에너지로 정렬되어야 함
        assert len(gen.data["results"]) == 3
        assert gen.data["results"][0]["e_ads"] == -1.5
    
    def test_boltzmann_calculation(self, tmp_path):
        """Boltzmann 분포 계산"""
        from surfscreen.report import ScreeningReportGenerator
        
        results = {
            "results": [
                {"name": "a", "e_ads": -1.5},
                {"name": "b", "e_ads": -1.2},
                {"name": "c", "e_ads": -1.0}
            ]
        }
        (tmp_path / "results.json").write_text(json.dumps(results))
        
        gen = ScreeningReportGenerator(str(tmp_path))
        boltzmann = gen.data["boltzmann"]
        
        # 확률 합은 1
        import numpy as np
        assert np.isclose(sum(boltzmann["probabilities"]), 1.0)
        
        # 가장 낮은 에너지가 가장 높은 확률
        assert boltzmann["probabilities"][0] >= boltzmann["probabilities"][1]
    
    def test_generate_html(self, tmp_path):
        """HTML 생성"""
        from surfscreen.report import ScreeningReportGenerator
        
        results = {
            "results": [
                {"name": "config_001", "e_ads": -1.5, "height": 2.0, "site_type": "top"}
            ]
        }
        (tmp_path / "results.json").write_text(json.dumps(results))
        
        gen = ScreeningReportGenerator(str(tmp_path))
        output_path = tmp_path / "test_report.html"
        
        result = gen.generate(str(output_path))
        
        assert Path(result).exists()
        html = Path(result).read_text()
        
        assert "<!DOCTYPE html>" in html
        assert "config_001" in html
        assert "Boltzmann" in html


class TestReportRendering:
    """리포트 렌더링 상세 테스트"""
    
    def test_render_html_structure(self, tmp_path):
        """HTML 구조 확인"""
        from surfscreen.report import MDReportGenerator
        
        (tmp_path / "summary.json").write_text("{}")
        gen = MDReportGenerator(str(tmp_path))
        
        html = gen.render_html("Test", "<p>Content</p>")
        
        # 구조 확인
        assert "<html" in html
        assert "<head>" in html
        assert "<body" in html
        assert "Content" in html
    
    def test_extra_css_included(self, tmp_path):
        """추가 CSS 포함"""
        from surfscreen.report import MDReportGenerator
        
        (tmp_path / "summary.json").write_text("{}")
        gen = MDReportGenerator(str(tmp_path))
        
        extra_css = ".custom-class { color: red; }"
        html = gen.render_html("Test", "<p>Test</p>", extra_css=extra_css)
        
        assert ".custom-class" in html
    
    def test_extra_js_included(self, tmp_path):
        """추가 JavaScript 포함"""
        from surfscreen.report import MDReportGenerator
        
        (tmp_path / "summary.json").write_text("{}")
        gen = MDReportGenerator(str(tmp_path))
        
        extra_js = "function customFunction() { return 42; }"
        html = gen.render_html("Test", "<p>Test</p>", extra_js=extra_js)
        
        assert "customFunction" in html
