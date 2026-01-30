"""
SurfScreen MD Report Generator

MD 시뮬레이션 결과를 위한 인터랙티브 HTML 리포트
- 궤적 스텝별 플레이백 (3Dmol.js)
- 에너지/온도 시계열 그래프 (Plotly)
- 다운로드 링크 (extxyz, xyz, traj)
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import base64

import numpy as np
from ase.io import read


class MDReportGenerator:
    """MD 시뮬레이션 리포트 생성기"""
    
    def __init__(self, md_output_dir: str):
        """
        Args:
            md_output_dir: MD 출력 디렉토리 (trajectory.traj, md.log 등 포함)
        """
        self.output_dir = Path(md_output_dir)
        self.summary_path = self.output_dir / "summary.json"
        self.log_path = self.output_dir / "md.log"
        self.traj_path = self.output_dir / "trajectory.traj"
        self.extxyz_path = self.output_dir / "trajectory.extxyz"
        
        # 데이터 로드
        self.summary = self._load_summary()
        self.log_data = self._parse_log()
        self.frames = self._load_frames()
        
    def _load_summary(self) -> Dict:
        """summary.json 로드"""
        if self.summary_path.exists():
            with open(self.summary_path) as f:
                return json.load(f)
        return {}
    
    def _parse_log(self) -> List[Dict]:
        """md.log 파싱"""
        data = []
        if not self.log_path.exists():
            return data
            
        with open(self.log_path) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        data.append({
                            "step": int(parts[0]),
                            "time": float(parts[1]),
                            "temperature": float(parts[2]),
                            "e_pot": float(parts[3]),
                            "e_kin": float(parts[4]),
                            "e_tot": float(parts[5])
                        })
                    except (ValueError, IndexError):
                        continue
        return data
    
    def _load_frames(self, max_frames: int = 100) -> List[str]:
        """궤적 프레임 로드 (XYZ 문자열)"""
        frames = []
        
        # extxyz 우선
        path = self.extxyz_path if self.extxyz_path.exists() else self.traj_path
        
        if not path.exists():
            return frames
            
        try:
            all_frames = read(str(path), index=":")
            
            # 샘플링 (최대 max_frames)
            if len(all_frames) > max_frames:
                indices = np.linspace(0, len(all_frames) - 1, max_frames, dtype=int)
                all_frames = [all_frames[i] for i in indices]
            
            for atoms in all_frames:
                xyz_lines = [f"{len(atoms)}"]
                # 에너지 정보 포함
                energy = atoms.info.get('energy', atoms.get_potential_energy() if atoms.calc else 0)
                xyz_lines.append(f"Energy={energy:.6f}")
                
                for atom in atoms:
                    xyz_lines.append(f"{atom.symbol} {atom.position[0]:.6f} {atom.position[1]:.6f} {atom.position[2]:.6f}")
                
                frames.append("\\n".join(xyz_lines))
                
        except Exception as e:
            print(f"Warning: Could not load trajectory: {e}")
            
        return frames
    
    def generate(self, output_path: str = "md_report.html") -> str:
        """HTML 리포트 생성"""
        
        # 로그 데이터를 JSON으로
        log_json = json.dumps(self.log_data)
        frames_json = json.dumps(self.frames)
        
        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MD Simulation Report - SurfScreen</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        :root {{
            --primary: #3b82f6;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --text: #e2e8f0;
            --text-muted: #94a3b8;
            --border: #334155;
            --success: #10b981;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3a8a, #3b82f6);
            padding: 2rem;
            text-align: center;
        }}
        
        .header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        .header p {{ color: rgba(255,255,255,0.8); }}
        
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem; }}
        
        .card {{
            background: var(--bg-card);
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid var(--border);
        }}
        
        .card h3 {{
            color: var(--primary);
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat {{
            background: var(--bg-card);
            border-radius: 0.75rem;
            padding: 1.25rem;
            text-align: center;
            border: 1px solid var(--border);
        }}
        
        .stat-value {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--primary);
        }}
        
        .stat-label {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}
        
        #viewer {{
            width: 100%;
            height: 450px;
            border-radius: 0.5rem;
            background: #000;
        }}
        
        .controls {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(0,0,0,0.3);
            border-radius: 0.5rem;
        }}
        
        .controls button {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
        }}
        
        .controls button:hover {{ opacity: 0.9; }}
        
        #frame-slider {{
            flex: 1;
            height: 8px;
            accent-color: var(--primary);
        }}
        
        #frame-info {{
            color: var(--text-muted);
            font-size: 0.875rem;
            min-width: 120px;
            text-align: right;
        }}
        
        .download-section {{
            display: flex;
            gap: 1rem;
            margin-top: 2rem;
        }}
        
        .download-btn {{
            background: var(--bg-card);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            text-decoration: none;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .download-btn:hover {{ border-color: var(--primary); }}
        
        @media (max-width: 768px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 MD Simulation Report</h1>
        <p>{self.output_dir.name} | Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{self.summary.get('total_steps', len(self.log_data))}</div>
                <div class="stat-label">Total Steps</div>
            </div>
            <div class="stat">
                <div class="stat-value">{self.summary.get('total_time_fs', 0):.1f}</div>
                <div class="stat-label">Time (fs)</div>
            </div>
            <div class="stat">
                <div class="stat-value">{self.summary.get('avg_temperature_K', 0):.1f}</div>
                <div class="stat-label">Avg Temp (K)</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(self.frames)}</div>
                <div class="stat-label">Saved Frames</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🎬 Trajectory Playback</h3>
                <div id="viewer"></div>
                <div class="controls">
                    <button id="play-btn" onclick="togglePlay()">▶ Play</button>
                    <input type="range" id="frame-slider" min="0" max="{max(len(self.frames)-1, 0)}" value="0" onchange="showFrame(this.value)">
                    <span id="frame-info">Frame 1 / {len(self.frames)}</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 Energy Profile</h3>
                <div id="energy-plot" style="height: 450px;"></div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🌡️ Temperature Profile</h3>
                <div id="temp-plot" style="height: 300px;"></div>
            </div>
            
            <div class="card">
                <h3>⚡ Kinetic vs Potential Energy</h3>
                <div id="energy-breakdown-plot" style="height: 300px;"></div>
            </div>
        </div>
        
        <div class="download-section">
            <a class="download-btn" href="trajectory.extxyz" download>📥 trajectory.extxyz (OVITO)</a>
            <a class="download-btn" href="trajectory.xyz" download>📥 trajectory.xyz (VMD)</a>
            <a class="download-btn" href="trajectory.traj" download>📥 trajectory.traj (ASE)</a>
            <a class="download-btn" href="final.xyz" download>📥 final.xyz</a>
        </div>
    </div>
    
    <script>
        const frames = {frames_json};
        const logData = {log_json};
        
        let viewer = null;
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        
        // 3Dmol viewer 초기화
        function initViewer() {{
            const element = document.getElementById('viewer');
            viewer = $3Dmol.createViewer(element, {{
                backgroundColor: '#0f172a'
            }});
            
            if (frames.length > 0) {{
                showFrame(0);
            }}
        }}
        
        // 프레임 표시
        function showFrame(idx) {{
            if (!viewer || frames.length === 0) return;
            
            currentFrame = parseInt(idx);
            viewer.removeAllModels();
            
            const xyz = frames[currentFrame].replace(/\\\\n/g, '\\n');
            viewer.addModel(xyz, 'xyz');
            viewer.setStyle({{}}, {{sphere: {{radius: 0.4, colorscheme: 'Jmol'}}}});
            viewer.zoomTo();
            viewer.render();
            
            document.getElementById('frame-slider').value = currentFrame;
            document.getElementById('frame-info').textContent = `Frame ${{currentFrame + 1}} / ${{frames.length}}`;
        }}
        
        // 재생/일시정지
        function togglePlay() {{
            const btn = document.getElementById('play-btn');
            
            if (isPlaying) {{
                clearInterval(playInterval);
                btn.textContent = '▶ Play';
            }} else {{
                playInterval = setInterval(() => {{
                    currentFrame = (currentFrame + 1) % frames.length;
                    showFrame(currentFrame);
                }}, 100);
                btn.textContent = '⏸ Pause';
            }}
            
            isPlaying = !isPlaying;
        }}
        
        // Plotly 그래프
        function initPlots() {{
            if (logData.length === 0) return;
            
            const steps = logData.map(d => d.step);
            const times = logData.map(d => d.time);
            const temps = logData.map(d => d.temperature);
            const ePot = logData.map(d => d.e_pot);
            const eKin = logData.map(d => d.e_kin);
            const eTot = logData.map(d => d.e_tot);
            
            // 총 에너지 플롯
            Plotly.newPlot('energy-plot', [{{
                x: times,
                y: eTot,
                type: 'scatter',
                mode: 'lines',
                name: 'Total Energy',
                line: {{ color: '#3b82f6', width: 2 }}
            }}], {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ color: '#94a3b8' }},
                xaxis: {{ title: 'Time (fs)', gridcolor: '#334155' }},
                yaxis: {{ title: 'Energy (eV)', gridcolor: '#334155' }},
                margin: {{ t: 20, r: 20, b: 50, l: 60 }}
            }});
            
            // 온도 플롯
            Plotly.newPlot('temp-plot', [{{
                x: times,
                y: temps,
                type: 'scatter',
                mode: 'lines',
                name: 'Temperature',
                line: {{ color: '#f59e0b', width: 2 }}
            }}], {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ color: '#94a3b8' }},
                xaxis: {{ title: 'Time (fs)', gridcolor: '#334155' }},
                yaxis: {{ title: 'Temperature (K)', gridcolor: '#334155' }},
                margin: {{ t: 20, r: 20, b: 50, l: 60 }}
            }});
            
            // E_pot vs E_kin
            Plotly.newPlot('energy-breakdown-plot', [
                {{
                    x: times,
                    y: ePot,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Potential',
                    line: {{ color: '#10b981', width: 2 }}
                }},
                {{
                    x: times,
                    y: eKin,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Kinetic',
                    line: {{ color: '#ef4444', width: 2 }}
                }}
            ], {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ color: '#94a3b8' }},
                xaxis: {{ title: 'Time (fs)', gridcolor: '#334155' }},
                yaxis: {{ title: 'Energy (eV)', gridcolor: '#334155' }},
                margin: {{ t: 20, r: 20, b: 50, l: 60 }},
                legend: {{ x: 0.02, y: 0.98 }}
            }});
        }}
        
        // 초기화
        document.addEventListener('DOMContentLoaded', () => {{
            initViewer();
            initPlots();
        }});
    </script>
</body>
</html>'''
        
        output_file = Path(output_path)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
            
        print(f"✓ MD Report generated: {output_file}")
        return str(output_file)
