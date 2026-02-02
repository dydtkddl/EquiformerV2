"""
SurfScreen Report Base Module

모든 리포트 생성기의 추상 베이스 클래스 및 공통 유틸리티
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


class BaseReportGenerator(ABC):
    """
    리포트 생성기 추상 베이스 클래스
    
    모든 리포트 생성기는 이 클래스를 상속하여 공통 인터페이스를 구현합니다.
    """
    
    # CDN URLs (버전 고정)
    PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.26.1.min.js"
    THREEDMOL_CDN = "https://3Dmol.org/build/3Dmol-min.js"
    JSZIP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"
    
    # CSS 변수 (다크/라이트 테마)
    CSS_VARIABLES = """
        :root {
            /* 다크 테마 (기본) */
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #334155;
            --accent-primary: #3b82f6;
            --accent-secondary: #10b981;
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
            --shadow: rgba(0, 0, 0, 0.3);
            --transition: all 0.3s ease;
            --radius-sm: 0.5rem;
            --radius-md: 0.75rem;
            --radius-lg: 1rem;
        }
        
        .light-theme {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --border-color: #e2e8f0;
            --shadow: rgba(0, 0, 0, 0.1);
        }
    """
    
    # 공통 CSS 스타일
    BASE_CSS = """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
                         'Helvetica Neue', Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
            padding: 2rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.05'/%3E%3C/svg%3E");
            pointer-events: none;
        }
        
        .header h1 {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            position: relative;
        }
        
        .header p {
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.95rem;
            position: relative;
        }
        
        /* Container */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* Grid */
        .grid { display: grid; gap: 1.5rem; }
        .grid-2 { grid-template-columns: repeat(2, 1fr); }
        .grid-3 { grid-template-columns: repeat(3, 1fr); }
        .grid-4 { grid-template-columns: repeat(4, 1fr); }
        
        /* Cards */
        .card {
            background: var(--bg-card);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px var(--shadow);
            transition: var(--transition);
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px var(--shadow);
        }
        
        .card h3 {
            color: var(--accent-primary);
            font-size: 1.1rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        /* Stats */
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
        
        .stat-card {
            background: var(--bg-card);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            text-align: center;
            border: 1px solid var(--border-color);
            transition: var(--transition);
        }
        
        .stat-card:hover { border-color: var(--accent-primary); }
        
        .stat-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--accent-primary);
        }
        
        .stat-label {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.625rem 1.25rem;
            border-radius: var(--radius-sm);
            font-weight: 500;
            font-size: 0.875rem;
            cursor: pointer;
            transition: var(--transition);
            text-decoration: none;
            border: none;
        }
        
        .btn-primary {
            background: var(--accent-primary);
            color: white;
        }
        
        .btn-primary:hover { opacity: 0.9; }
        
        .btn-secondary {
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
        
        .btn-secondary:hover { border-color: var(--accent-primary); }
        
        /* Tables */
        .table-wrapper {
            overflow-x: auto;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            background: var(--bg-secondary);
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        tr:hover { background: rgba(59, 130, 246, 0.05); }
        
        /* Controls */
        .controls {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: var(--radius-sm);
            margin-top: 1rem;
        }
        
        input[type="range"] {
            flex: 1;
            height: 6px;
            accent-color: var(--accent-primary);
            background: var(--border-color);
            border-radius: 3px;
        }
        
        /* Viewer */
        .viewer-container {
            width: 100%;
            height: 450px;
            border-radius: var(--radius-md);
            background: #000;
            position: relative;
        }
        
        /* Responsive */
        @media (max-width: 1024px) {
            .grid-4 { grid-template-columns: repeat(2, 1fr); }
            .grid-3 { grid-template-columns: repeat(2, 1fr); }
        }
        
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
            .stats { grid-template-columns: repeat(2, 1fr); }
            .header { padding: 1.5rem 1rem; }
            .header h1 { font-size: 1.5rem; }
        }
        
        /* Theme toggle */
        .theme-toggle {
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 1000;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 1.25rem;
            transition: var(--transition);
        }
        
        .theme-toggle:hover {
            background: var(--accent-primary);
            color: white;
        }
        
        /* Collapsible */
        .collapsible {
            cursor: pointer;
            user-select: none;
        }
        
        .collapsible::after {
            content: '▼';
            float: right;
            font-size: 0.75rem;
            transition: transform 0.3s;
        }
        
        .collapsible.collapsed::after {
            transform: rotate(-90deg);
        }
        
        .collapsible-content {
            max-height: 2000px;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }
        
        .collapsible-content.collapsed {
            max-height: 0;
        }
        
        /* Download buttons */
        .download-section {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
        }
    """
    
    # 공통 JavaScript
    BASE_JS = """
        'use strict';
        
        // 테마 토글
        function toggleTheme() {
            const body = document.body;
            body.classList.toggle('light-theme');
            const isDark = !body.classList.contains('light-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            document.getElementById('theme-icon').textContent = isDark ? '🌙' : '☀️';
        }
        
        // 초기 테마 설정
        function initTheme() {
            const saved = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (saved === 'light' || (!saved && !prefersDark)) {
                document.body.classList.add('light-theme');
                document.getElementById('theme-icon').textContent = '☀️';
            }
        }
        
        // CSV 다운로드
        function downloadCSV(data, filename) {
            const csv = data.map(row => Object.values(row).join(',')).join('\\n');
            const headers = Object.keys(data[0]).join(',') + '\\n';
            const blob = new Blob([headers + csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // JSON 다운로드
        function downloadJSON(data, filename) {
            const json = JSON.stringify(data, null, 2);
            const blob = new Blob([json], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // XYZ 다운로드
        function downloadXYZ(xyzString, filename) {
            const blob = new Blob([xyzString], { type: 'chemical/x-xyz' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        // Collapsible 토글
        function toggleCollapsible(element) {
            element.classList.toggle('collapsed');
            const content = element.nextElementSibling;
            if (content) {
                content.classList.toggle('collapsed');
            }
        }
        
        // 숫자 포맷팅
        function formatNumber(num, decimals = 2) {
            if (typeof num !== 'number') return num;
            if (Math.abs(num) < 0.01 || Math.abs(num) > 1000) {
                return num.toExponential(decimals);
            }
            return num.toFixed(decimals);
        }
        
        // WebGL 지원 확인
        function checkWebGL() {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            return !!gl;
        }
        
        // 초기화
        document.addEventListener('DOMContentLoaded', () => {
            initTheme();
            
            if (!checkWebGL()) {
                const viewers = document.querySelectorAll('.viewer-container');
                viewers.forEach(v => {
                    v.innerHTML = '<div style="padding:2rem;text-align:center;color:#94a3b8;">WebGL is not supported in your browser. Please use a modern browser to view 3D structures.</div>';
                });
            }
        });
    """
    
    def __init__(self, data_dir: str, theme: str = "dark"):
        """
        Args:
            data_dir: 데이터 디렉토리 경로
            theme: 기본 테마 ('dark' or 'light')
        """
        self.data_dir = Path(data_dir)
        self.theme = theme
        self.generated_at = datetime.now()
    
    @abstractmethod
    def load_data(self) -> Dict[str, Any]:
        """데이터 로드 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def generate_content(self) -> str:
        """HTML 본문 컨텐츠 생성 (하위 클래스에서 구현)"""
        pass
    
    def render_html(self, title: str, content: str, 
                    extra_css: str = "", extra_js: str = "") -> str:
        """
        완전한 HTML 문서 렌더링
        
        Args:
            title: 페이지 제목
            content: HTML 본문 내용
            extra_css: 추가 CSS
            extra_js: 추가 JavaScript
        
        Returns:
            완전한 HTML 문자열
        """
        theme_class = "light-theme" if self.theme == "light" else ""
        
        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - SurfScreen</title>
    <script src="{self.PLOTLY_CDN}"></script>
    <script src="{self.THREEDMOL_CDN}"></script>
    <script src="{self.JSZIP_CDN}"></script>
    <style>
{self.CSS_VARIABLES}
{self.BASE_CSS}
{extra_css}
    </style>
</head>
<body class="{theme_class}">
    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">
        <span id="theme-icon">🌙</span>
    </button>
    
{content}

    <script>
{self.BASE_JS}
{extra_js}
    </script>
</body>
</html>'''
    
    def save(self, html: str, output_path: str) -> str:
        """
        HTML을 파일로 저장
        
        Args:
            html: HTML 문자열
            output_path: 출력 경로
            
        Returns:
            저장된 파일 경로
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        
        return str(output_file)
    
    @abstractmethod
    def generate(self, output_path: str) -> str:
        """리포트 생성 및 저장 (하위 클래스에서 구현)"""
        pass
    
    # 유틸리티 메서드
    @staticmethod
    def format_energy(energy: float) -> str:
        """에너지 값 포맷팅"""
        if abs(energy) < 0.01:
            return f"{energy:.4f}"
        return f"{energy:.3f}"
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """시간 포맷팅"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """HTML 이스케이프"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
