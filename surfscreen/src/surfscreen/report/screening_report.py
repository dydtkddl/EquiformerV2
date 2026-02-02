"""
SurfScreen Screening Report Generator

흡착 스크리닝 결과를 위한 인터랙티브 HTML 리포트
- 에너지 분포 히스토그램
- Boltzmann 분석
- 구조 갤러리 및 비교
- 결과 테이블 (정렬/필터)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import numpy as np

from surfscreen.report.base import BaseReportGenerator


class ScreeningReportGenerator(BaseReportGenerator):
    """흡착 스크리닝 리포트 생성기"""
    
    def __init__(self, results_dir: str, theme: str = "dark", top_n: int = 20):
        """
        Args:
            results_dir: 결과 디렉토리 (results.json 포함)
            theme: 테마 ('dark' or 'light')
            top_n: 테이블에 표시할 상위 N개
        """
        super().__init__(results_dir, theme)
        self.top_n = top_n
        
        # 파일 경로
        self.results_path = self.data_dir / "results.json"
        
        # 데이터 로드
        self.data = self.load_data()
    
    def load_data(self) -> Dict[str, Any]:
        """결과 데이터 로드"""
        if not self.results_path.exists():
            return {"results": [], "summary": {}}
        
        with open(self.results_path) as f:
            data = json.load(f)
        
        results = data.get("results", [])
        
        # 에너지로 정렬
        results = sorted(results, key=lambda x: x.get("e_ads", 0))
        
        # Boltzmann 분석 추가
        boltzmann = self._calculate_boltzmann(results)
        
        return {
            "results": results,
            "summary": data.get("summary", {}),
            "boltzmann": boltzmann
        }
    
    def _calculate_boltzmann(self, results: List[Dict], T: float = 300) -> Dict:
        """Boltzmann 분포 계산"""
        if not results:
            return {}
        
        kB_eV = 8.617333262e-5  # eV/K
        kT = kB_eV * T
        
        energies = np.array([r.get("e_ads", 0) for r in results])
        
        # 가장 낮은 에너지를 기준으로
        e_min = np.min(energies)
        weights = np.exp(-(energies - e_min) / kT)
        probabilities = weights / np.sum(weights)
        
        return {
            "temperature": T,
            "probabilities": probabilities.tolist(),
            "names": [r.get("name", f"config_{i}") for i, r in enumerate(results)]
        }
    
    def _load_structure(self, config_name: str) -> Optional[str]:
        """구조 파일 로드"""
        for ext in [".xyz", ".extxyz"]:
            path = self.data_dir / f"{config_name}{ext}"
            if path.exists():
                return path.read_text()
        return None
    
    def generate_content(self) -> str:
        """HTML 본문 생성"""
        results = self.data["results"]
        summary = self.data["summary"]
        boltzmann = self.data["boltzmann"]
        
        # 통계
        total = len(results)
        if results:
            e_min = min(r.get("e_ads", 0) for r in results)
            e_max = max(r.get("e_ads", 0) for r in results)
            e_avg = np.mean([r.get("e_ads", 0) for r in results])
        else:
            e_min = e_max = e_avg = 0
        
        # 상위 N개 결과
        top_results = results[:self.top_n]
        
        # 테이블 행 생성
        table_rows = ""
        for i, r in enumerate(top_results):
            prob = boltzmann["probabilities"][i] * 100 if boltzmann else 0
            table_rows += f'''
            <tr onclick="showStructure({i})" style="cursor:pointer;">
                <td>{i + 1}</td>
                <td><strong>{r.get("name", "N/A")}</strong></td>
                <td>{r.get("e_ads", 0):.4f}</td>
                <td>{r.get("height", 0):.2f}</td>
                <td>{r.get("site_type", "N/A")}</td>
                <td>
                    <div style="display:flex;align-items:center;gap:0.5rem;">
                        <div style="width:{min(prob, 100)}px;height:8px;background:var(--accent-primary);border-radius:4px;"></div>
                        <span>{prob:.1f}%</span>
                    </div>
                </td>
            </tr>
            '''
        
        return f'''
    <div class="header">
        <h1>🎯 Adsorption Screening Report</h1>
        <p>{self.data_dir.name} | Generated {self.generated_at.strftime("%Y-%m-%d %H:%M")}</p>
    </div>
    
    <div class="container">
        <!-- Stats Cards -->
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Total Configs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{e_min:.3f}</div>
                <div class="stat-label">Best E_ads (eV)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{e_avg:.3f}</div>
                <div class="stat-label">Avg E_ads (eV)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.get("converged", total)}</div>
                <div class="stat-label">Converged</div>
            </div>
        </div>
        
        <!-- Charts Row -->
        <div class="grid grid-2">
            <div class="card">
                <h3>📊 Energy Distribution</h3>
                <div id="energy-hist" style="height:350px;"></div>
            </div>
            
            <div class="card">
                <h3>🎲 Boltzmann Population (T = {boltzmann.get("temperature", 300)} K)</h3>
                <div id="boltzmann-pie" style="height:350px;"></div>
            </div>
        </div>
        
        <!-- Structure Viewer & Table -->
        <div class="grid grid-2" style="margin-top:1.5rem;">
            <div class="card">
                <h3>🔬 Structure Viewer</h3>
                <div id="viewer" class="viewer-container"></div>
                <div style="margin-top:0.75rem;display:flex;gap:0.5rem;">
                    <button class="btn btn-secondary" onclick="toggleStyle('sphere')">Sphere</button>
                    <button class="btn btn-secondary" onclick="toggleStyle('stick')">Stick</button>
                    <button class="btn btn-secondary" onclick="toggleStyle('ball')">Ball & Stick</button>
                    <button class="btn btn-primary" onclick="downloadCurrentStructure()" style="margin-left:auto;">
                        💾 Download
                    </button>
                </div>
            </div>
            
            <div class="card">
                <h3 class="collapsible" onclick="toggleCollapsible(this)">
                    📋 Top {self.top_n} Configurations
                </h3>
                <div class="collapsible-content">
                    <div class="table-wrapper" style="max-height:400px;overflow-y:auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Name</th>
                                    <th>E_ads (eV)</th>
                                    <th>Height (Å)</th>
                                    <th>Site</th>
                                    <th>Probability</th>
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Box Plot -->
        <div class="card" style="margin-top:1.5rem;">
            <h3>📈 Energy by Site Type</h3>
            <div id="site-boxplot" style="height:300px;"></div>
        </div>
        
        <!-- Downloads -->
        <div class="card" style="margin-top:1.5rem;">
            <h3>📥 Downloads</h3>
            <div class="download-section" style="margin-top:0;padding-top:0;border-top:none;">
                <button class="btn btn-secondary" onclick="downloadResultsCSV()">
                    📄 results.csv
                </button>
                <button class="btn btn-secondary" onclick="downloadResultsJSON()">
                    📄 results.json
                </button>
                <a class="btn btn-secondary" href="best_config.xyz" download>
                    📄 best_config.xyz
                </a>
            </div>
        </div>
    </div>
'''
    
    def _generate_js(self) -> str:
        """JavaScript 생성"""
        results_json = json.dumps(self.data["results"][:self.top_n])
        boltzmann_json = json.dumps(self.data["boltzmann"])
        all_results_json = json.dumps(self.data["results"])
        
        # 구조 데이터 로드
        structures = {}
        for i, r in enumerate(self.data["results"][:self.top_n]):
            name = r.get("name", f"config_{i}")
            xyz = self._load_structure(name)
            if xyz:
                structures[i] = xyz.replace("\n", "\\n").replace("'", "\\'")
        
        structures_json = json.dumps(structures)
        
        return f'''
        const results = {results_json};
        const allResults = {all_results_json};
        const boltzmann = {boltzmann_json};
        const structures = {structures_json};
        
        let viewer = null;
        let currentIndex = 0;
        let currentStyle = 'ball';
        
        // Viewer 초기화
        function initViewer() {{
            const element = document.getElementById('viewer');
            if (!element || !checkWebGL()) return;
            
            viewer = $3Dmol.createViewer(element, {{
                backgroundColor: '#0f172a'
            }});
            
            if (Object.keys(structures).length > 0) {{
                showStructure(0);
            }}
        }}
        
        // 구조 표시
        function showStructure(idx) {{
            if (!viewer) return;
            currentIndex = idx;
            
            viewer.removeAllModels();
            
            const xyz = structures[idx];
            if (xyz) {{
                viewer.addModel(xyz.replace(/\\\\n/g, '\\n'), 'xyz');
                applyStyle(currentStyle);
                viewer.zoomTo();
                viewer.render();
            }}
            
            // 테이블 하이라이트
            document.querySelectorAll('tbody tr').forEach((row, i) => {{
                row.style.background = i === idx ? 'rgba(59, 130, 246, 0.2)' : '';
            }});
        }}
        
        // 스타일 변경
        function toggleStyle(style) {{
            currentStyle = style;
            applyStyle(style);
        }}
        
        function applyStyle(style) {{
            if (!viewer) return;
            
            switch(style) {{
                case 'sphere':
                    viewer.setStyle({{}}, {{sphere: {{radius: 0.5, colorscheme: 'Jmol'}}}});
                    break;
                case 'stick':
                    viewer.setStyle({{}}, {{stick: {{radius: 0.15, colorscheme: 'Jmol'}}}});
                    break;
                case 'ball':
                default:
                    viewer.setStyle({{}}, {{
                        sphere: {{radius: 0.35, colorscheme: 'Jmol'}},
                        stick: {{radius: 0.1, colorscheme: 'Jmol'}}
                    }});
            }}
            viewer.render();
        }}
        
        // 현재 구조 다운로드
        function downloadCurrentStructure() {{
            const xyz = structures[currentIndex];
            if (xyz) {{
                const name = results[currentIndex]?.name || `config_${{currentIndex}}`;
                downloadXYZ(xyz.replace(/\\\\n/g, '\\n'), `${{name}}.xyz`);
            }}
        }}
        
        // CSV 다운로드
        function downloadResultsCSV() {{
            downloadCSV(allResults, 'screening_results.csv');
        }}
        
        // JSON 다운로드
        function downloadResultsJSON() {{
            downloadJSON({{results: allResults, boltzmann: boltzmann}}, 'screening_results.json');
        }}
        
        // Plotly 그래프
        function initPlots() {{
            const energies = allResults.map(r => r.e_ads || 0);
            const names = results.map(r => r.name || 'N/A');
            const probs = boltzmann.probabilities?.slice(0, {self.top_n}) || [];
            
            const layout = {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ color: '#94a3b8' }},
                margin: {{ t: 30, r: 20, b: 50, l: 60 }}
            }};
            
            // Energy Distribution
            Plotly.newPlot('energy-hist', [{{
                x: energies,
                type: 'histogram',
                nbinsx: 30,
                marker: {{ color: '#3b82f6' }}
            }}], {{
                ...layout,
                xaxis: {{ title: 'E_ads (eV)', gridcolor: '#334155' }},
                yaxis: {{ title: 'Count', gridcolor: '#334155' }}
            }});
            
            // Boltzmann Pie (Top 5)
            const topN = 5;
            const pieLabels = names.slice(0, topN);
            const pieValues = probs.slice(0, topN);
            const otherProb = probs.slice(topN).reduce((a, b) => a + b, 0);
            
            if (otherProb > 0) {{
                pieLabels.push('Others');
                pieValues.push(otherProb);
            }}
            
            Plotly.newPlot('boltzmann-pie', [{{
                labels: pieLabels,
                values: pieValues,
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b']
                }}
            }}], {{
                ...layout,
                showlegend: true,
                legend: {{ x: 1, y: 0.5 }}
            }});
            
            // Box Plot by Site Type
            const siteTypes = [...new Set(allResults.map(r => r.site_type || 'Unknown'))];
            const boxData = siteTypes.map(site => ({{
                y: allResults.filter(r => (r.site_type || 'Unknown') === site).map(r => r.e_ads),
                type: 'box',
                name: site,
                boxpoints: 'outliers'
            }}));
            
            Plotly.newPlot('site-boxplot', boxData, {{
                ...layout,
                xaxis: {{ title: 'Site Type', gridcolor: '#334155' }},
                yaxis: {{ title: 'E_ads (eV)', gridcolor: '#334155' }},
                showlegend: false
            }});
        }}
        
        // 초기화
        document.addEventListener('DOMContentLoaded', () => {{
            initViewer();
            initPlots();
        }});
        '''
    
    def generate(self, output_path: str = "screening_report.html") -> str:
        """리포트 생성"""
        content = self.generate_content()
        extra_js = self._generate_js()
        
        html = self.render_html(
            title="Adsorption Screening Report",
            content=content,
            extra_js=extra_js
        )
        
        output_file = self.save(html, output_path)
        print(f"✓ Screening Report generated: {output_file}")
        return output_file
