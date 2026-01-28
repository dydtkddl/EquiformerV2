"""
SurfScreen Report Generator

인터렉티브 HTML 리포트 생성
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import base64

import pandas as pd
import numpy as np


class ReportGenerator:
    """스크리닝 결과 HTML 리포트 생성기
    
    Examples:
        gen = ReportGenerator(results_dir="screening_results/ethanol")
        gen.generate("report.html")
    """
    
    HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SurfScreen Report - {title}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent: #22d3ee;
            --accent-green: #4ade80;
            --accent-orange: #fb923c;
            --accent-red: #f87171;
            --gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }}
        
        .header {{
            background: var(--gradient);
            padding: 2rem;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header .subtitle {{
            color: rgba(255,255,255,0.8);
            font-size: 1.1rem;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            margin-top: 0.5rem;
        }}
        
        .section {{
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .section h2 {{
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .chart-container {{
            width: 100%;
            height: 400px;
        }}
        
        .viewer-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }}
        
        @media (max-width: 900px) {{
            .viewer-container {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .mol-viewer {{
            height: 400px;
            background: var(--bg-card);
            border-radius: 12px;
            position: relative;
        }}
        
        .mol-viewer-label {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            z-index: 10;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        th {{
            background: var(--bg-card);
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        
        tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        .energy-bar {{
            height: 8px;
            background: var(--bg-card);
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .energy-bar-fill {{
            height: 100%;
            background: var(--gradient);
            border-radius: 4px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        
        .badge-top {{ background: rgba(34, 211, 238, 0.2); color: var(--accent); }}
        .badge-bridge {{ background: rgba(74, 222, 128, 0.2); color: var(--accent-green); }}
        .badge-hollow {{ background: rgba(251, 146, 60, 0.2); color: var(--accent-orange); }}
        .badge-fcc {{ background: rgba(167, 139, 250, 0.2); color: #a78bfa; }}
        .badge-hcp {{ background: rgba(248, 113, 113, 0.2); color: var(--accent-red); }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 SurfScreen Report</h1>
        <p class="subtitle">{title} | Generated: {timestamp}</p>
    </div>
    
    <div class="container">
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{n_configs}</div>
                <div class="stat-label">Configurations</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{best_energy:.3f}</div>
                <div class="stat-label">Best E_ads (eV)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{best_site}</div>
                <div class="stat-label">Optimal Site</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_steps:.0f}</div>
                <div class="stat-label">Avg. Opt Steps</div>
            </div>
        </div>
        
        <!-- Energy Distribution -->
        <div class="section">
            <h2>📊 Adsorption Energy Distribution</h2>
            <div id="energy-chart" class="chart-container"></div>
        </div>
        
        <!-- 3D Viewers -->
        <div class="section">
            <h2>🔬 3D Structure Viewer</h2>
            <div class="viewer-container">
                <div class="mol-viewer" id="viewer-best">
                    <div class="mol-viewer-label">Best: {best_config}</div>
                </div>
                <div class="mol-viewer" id="viewer-second">
                    <div class="mol-viewer-label">2nd: {second_config}</div>
                </div>
            </div>
        </div>
        
        <!-- Results Table -->
        <div class="section">
            <h2>📋 All Results</h2>
            <div style="max-height: 500px; overflow-y: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Configuration</th>
                            <th>Site Type</th>
                            <th>E_ads (eV)</th>
                            <th>Relative</th>
                            <th>Steps</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="footer">
        Generated by SurfScreen v0.1.0 | Enterprise Surface Adsorption Screening Platform
    </div>
    
    <script>
        // Energy Distribution Chart
        var energyData = {energy_data};
        
        var trace1 = {{
            x: energyData.names,
            y: energyData.energies,
            type: 'bar',
            marker: {{
                color: energyData.energies,
                colorscale: [[0, '#22d3ee'], [1, '#764ba2']],
                reversescale: true
            }},
            hovertemplate: '<b>%{{x}}</b><br>E_ads: %{{y:.4f}} eV<extra></extra>'
        }};
        
        var layout1 = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#f1f5f9' }},
            xaxis: {{
                tickangle: -45,
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            yaxis: {{
                title: 'E_ads (eV)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            margin: {{ t: 20, b: 100 }}
        }};
        
        Plotly.newPlot('energy-chart', [trace1], layout1, {{responsive: true}});
        
        // 3D Viewer - Best
        let viewer1 = $3Dmol.createViewer('viewer-best', {{
            backgroundColor: '#334155'
        }});
        viewer1.addModel(`{xyz_best}`, 'xyz');
        viewer1.setStyle({{}}, {{
            stick: {{ radius: 0.15 }},
            sphere: {{ scale: 0.25 }}
        }});
        viewer1.zoomTo();
        viewer1.render();
        
        // 3D Viewer - Second
        let viewer2 = $3Dmol.createViewer('viewer-second', {{
            backgroundColor: '#334155'
        }});
        viewer2.addModel(`{xyz_second}`, 'xyz');
        viewer2.setStyle({{}}, {{
            stick: {{ radius: 0.15 }},
            sphere: {{ scale: 0.25 }}
        }});
        viewer2.zoomTo();
        viewer2.render();
    </script>
</body>
</html>
'''
    
    def __init__(self, results_dir: str):
        """
        Args:
            results_dir: 스크리닝 결과 디렉토리
        """
        self.results_dir = Path(results_dir)
        self.results_csv = self.results_dir / "results.csv"
        
        if not self.results_csv.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_csv}")
        
        self.df = pd.read_csv(self.results_csv)
        self.df = self.df.sort_values("e_ads")
    
    def generate(self, output_path: str = "report.html") -> str:
        """HTML 리포트 생성
        
        Args:
            output_path: 출력 파일 경로
            
        Returns:
            생성된 파일 경로
        """
        # 통계
        n_configs = len(self.df)
        best_row = self.df.iloc[0]
        best_energy = best_row["e_ads"]
        best_config = best_row["name"]
        avg_steps = self.df["steps"].mean()
        
        # 사이트 타입
        best_site = best_row.get("site_type", "unknown") if "site_type" in self.df.columns else "unknown"
        
        # 에너지 데이터
        energy_data = {
            "names": self.df["name"].tolist()[:20],  # Top 20
            "energies": self.df["e_ads"].tolist()[:20]
        }
        
        # 테이블 행
        table_rows = []
        min_e = self.df["e_ads"].min()
        max_e = self.df["e_ads"].max()
        e_range = max_e - min_e if max_e != min_e else 1
        
        for i, row in self.df.iterrows():
            rel_e = row["e_ads"] - min_e
            bar_width = 100 - (rel_e / e_range * 100)
            
            site_type = row.get("site_type", "unknown") if "site_type" in self.df.columns else "unknown"
            badge_class = f"badge-{site_type}"
            
            table_rows.append(f'''
                <tr>
                    <td>{len(table_rows) + 1}</td>
                    <td>{row["name"]}</td>
                    <td><span class="badge {badge_class}">{site_type}</span></td>
                    <td>{row["e_ads"]:.4f}</td>
                    <td>
                        <div class="energy-bar">
                            <div class="energy-bar-fill" style="width: {bar_width:.1f}%"></div>
                        </div>
                    </td>
                    <td>{row["steps"]}</td>
                </tr>
            ''')
        
        # XYZ 파일 읽기
        xyz_best = self._read_xyz(best_config)
        second_config = self.df.iloc[1]["name"] if len(self.df) > 1 else best_config
        xyz_second = self._read_xyz(second_config)
        
        # HTML 생성
        html = self.HTML_TEMPLATE.format(
            title=self.results_dir.name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            n_configs=n_configs,
            best_energy=best_energy,
            best_site=best_site,
            avg_steps=avg_steps,
            best_config=best_config,
            second_config=second_config,
            energy_data=json.dumps(energy_data),
            table_rows="".join(table_rows),
            xyz_best=xyz_best,
            xyz_second=xyz_second
        )
        
        output_path = Path(output_path)
        output_path.write_text(html, encoding="utf-8")
        
        return str(output_path)
    
    def _read_xyz(self, config_name: str) -> str:
        """XYZ 파일 읽기"""
        xyz_path = self.results_dir / f"{config_name}.xyz"
        if xyz_path.exists():
            return xyz_path.read_text()
        return ""
