"""
SurfScreen MD Report Generator

MD 시뮬레이션 결과를 위한 인터랙티브 HTML 리포트
- 3Dmol.js 기반 trajectory playback
- Plotly 기반 에너지/온도 시계열
- 다운로드 기능 (extxyz, xyz, traj)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import numpy as np

from surfscreen.report.base import BaseReportGenerator


class MDReportGenerator(BaseReportGenerator):
    """MD 시뮬레이션 리포트 생성기"""
    
    def __init__(self, md_output_dir: str, theme: str = "dark", max_frames: int = 100):
        """
        Args:
            md_output_dir: MD 출력 디렉토리 (trajectory.traj, md.log 등 포함)
            theme: 테마 ('dark' or 'light')
            max_frames: 최대 프레임 수 (성능 최적화)
        """
        super().__init__(md_output_dir, theme)
        self.max_frames = max_frames
        
        # 파일 경로
        self.summary_path = self.data_dir / "summary.json"
        self.log_path = self.data_dir / "md.log"
        self.traj_path = self.data_dir / "trajectory.traj"
        self.extxyz_path = self.data_dir / "trajectory.extxyz"
        
        # 데이터 로드
        self.data = self.load_data()
    
    def load_data(self) -> Dict[str, Any]:
        """모든 MD 데이터 로드"""
        return {
            "summary": self._load_summary(),
            "log": self._parse_log(),
            "frames": self._load_frames(),
            "cell": self._load_cell_info()
        }
    
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
    
    def _load_frames(self) -> List[Dict]:
        """궤적 프레임 로드"""
        frames = []
        
        # extxyz 우선
        path = self.extxyz_path if self.extxyz_path.exists() else self.traj_path
        
        if not path.exists():
            return frames
        
        try:
            from ase.io import read
            all_frames = read(str(path), index=":")
            
            # 샘플링
            if len(all_frames) > self.max_frames:
                indices = np.linspace(0, len(all_frames) - 1, self.max_frames, dtype=int)
                all_frames = [all_frames[i] for i in indices]
            
            for i, atoms in enumerate(all_frames):
                # XYZ 문자열 생성
                xyz_lines = [str(len(atoms))]
                energy = atoms.info.get('energy', 
                    atoms.get_potential_energy() if atoms.calc else 0)
                xyz_lines.append(f"Energy={energy:.6f}")
                
                for atom in atoms:
                    xyz_lines.append(
                        f"{atom.symbol} {atom.position[0]:.6f} "
                        f"{atom.position[1]:.6f} {atom.position[2]:.6f}"
                    )
                
                frames.append({
                    "index": i,
                    "xyz": "\\n".join(xyz_lines),
                    "energy": energy
                })
        
        except Exception as e:
            print(f"Warning: Could not load trajectory: {e}")
        
        return frames
    
    def _load_cell_info(self) -> Optional[Dict]:
        """셀 파라미터 로드"""
        try:
            from ase.io import read
            path = self.extxyz_path if self.extxyz_path.exists() else self.traj_path
            if path.exists():
                atoms = read(str(path), index=0)
                cell = atoms.get_cell()
                return {
                    "a": float(cell[0, 0]),
                    "b": float(cell[1, 1]),
                    "c": float(cell[2, 2])
                }
        except:
            pass
        return None
    
    def generate_content(self) -> str:
        """HTML 본문 생성"""
        summary = self.data["summary"]
        log_data = self.data["log"]
        frames = self.data["frames"]
        
        # 통계 계산
        total_steps = summary.get('total_steps', len(log_data))
        total_time = summary.get('total_time_fs', log_data[-1]['time'] if log_data else 0)
        avg_temp = summary.get('avg_temperature_K', 
            np.mean([d['temperature'] for d in log_data]) if log_data else 0)
        
        return f'''
    <div class="header">
        <h1>🔬 MD Simulation Report</h1>
        <p>{self.data_dir.name} | Generated {self.generated_at.strftime("%Y-%m-%d %H:%M")}</p>
    </div>
    
    <div class="container">
        <!-- Stats Cards -->
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total_steps:,}</div>
                <div class="stat-label">Total Steps</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_time:.1f}</div>
                <div class="stat-label">Time (fs)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_temp:.1f}</div>
                <div class="stat-label">Avg Temp (K)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(frames)}</div>
                <div class="stat-label">Saved Frames</div>
            </div>
        </div>
        
        <!-- Trajectory & Energy -->
        <div class="grid grid-2">
            <div class="card">
                <h3>🎬 Trajectory Playback</h3>
                <div id="viewer" class="viewer-container"></div>
                <div class="controls">
                    <button class="btn btn-primary" id="play-btn" onclick="togglePlay()">
                        ▶ Play
                    </button>
                    <input type="range" id="frame-slider" min="0" 
                           max="{max(len(frames)-1, 0)}" value="0" 
                           oninput="showFrame(this.value)">
                    <span id="frame-info" style="min-width:100px;text-align:right;">
                        Frame 1 / {len(frames)}
                    </span>
                    <select id="speed-select" onchange="updateSpeed()" style="padding:0.5rem;">
                        <option value="200">0.5x</option>
                        <option value="100" selected>1x</option>
                        <option value="50">2x</option>
                        <option value="25">4x</option>
                    </select>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 Total Energy</h3>
                <div id="energy-plot" style="height:450px;"></div>
            </div>
        </div>
        
        <!-- Temperature & Energy Breakdown -->
        <div class="grid grid-2" style="margin-top:1.5rem;">
            <div class="card">
                <h3>🌡️ Temperature Profile</h3>
                <div id="temp-plot" style="height:300px;"></div>
            </div>
            
            <div class="card">
                <h3>⚡ E<sub>pot</sub> vs E<sub>kin</sub></h3>
                <div id="energy-breakdown" style="height:300px;"></div>
            </div>
        </div>
        
        <!-- Downloads -->
        <div class="card" style="margin-top:1.5rem;">
            <h3>📥 Downloads</h3>
            <div class="download-section" style="margin-top:0;padding-top:0;border-top:none;">
                <a class="btn btn-secondary" href="trajectory.extxyz" download>
                    📄 trajectory.extxyz (OVITO)
                </a>
                <a class="btn btn-secondary" href="trajectory.xyz" download>
                    📄 trajectory.xyz (VMD)
                </a>
                <a class="btn btn-secondary" href="trajectory.traj" download>
                    📄 trajectory.traj (ASE)
                </a>
                <a class="btn btn-secondary" href="final.xyz" download>
                    📄 final.xyz
                </a>
                <button class="btn btn-primary" onclick="downloadCurrentFrame()">
                    💾 Current Frame
                </button>
            </div>
        </div>
    </div>
'''
    
    def _generate_js(self) -> str:
        """JavaScript 생성"""
        frames_json = json.dumps([f["xyz"] for f in self.data["frames"]])
        log_json = json.dumps(self.data["log"])
        
        return f'''
        const frames = {frames_json};
        const logData = {log_json};
        
        let viewer = null;
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        let playSpeed = 100;
        
        // 3Dmol viewer 초기화
        function initViewer() {{
            const element = document.getElementById('viewer');
            if (!element || !checkWebGL()) return;
            
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
            viewer.setStyle({{}}, {{
                sphere: {{radius: 0.35, colorscheme: 'Jmol'}},
                stick: {{radius: 0.1, colorscheme: 'Jmol'}}
            }});
            viewer.zoomTo();
            viewer.render();
            
            document.getElementById('frame-slider').value = currentFrame;
            document.getElementById('frame-info').textContent = 
                `Frame ${{currentFrame + 1}} / ${{frames.length}}`;
        }}
        
        // 재생/일시정지
        function togglePlay() {{
            const btn = document.getElementById('play-btn');
            
            if (isPlaying) {{
                clearInterval(playInterval);
                btn.innerHTML = '▶ Play';
            }} else {{
                playInterval = setInterval(() => {{
                    currentFrame = (currentFrame + 1) % frames.length;
                    showFrame(currentFrame);
                }}, playSpeed);
                btn.innerHTML = '⏸ Pause';
            }}
            
            isPlaying = !isPlaying;
        }}
        
        // 속도 변경
        function updateSpeed() {{
            playSpeed = parseInt(document.getElementById('speed-select').value);
            if (isPlaying) {{
                clearInterval(playInterval);
                playInterval = setInterval(() => {{
                    currentFrame = (currentFrame + 1) % frames.length;
                    showFrame(currentFrame);
                }}, playSpeed);
            }}
        }}
        
        // 현재 프레임 다운로드
        function downloadCurrentFrame() {{
            if (frames.length === 0) return;
            const xyz = frames[currentFrame].replace(/\\\\n/g, '\\n');
            downloadXYZ(xyz, `frame_${{currentFrame}}.xyz`);
        }}
        
        // Plotly 그래프
        function initPlots() {{
            if (logData.length === 0) return;
            
            const times = logData.map(d => d.time);
            const temps = logData.map(d => d.temperature);
            const ePot = logData.map(d => d.e_pot);
            const eKin = logData.map(d => d.e_kin);
            const eTot = logData.map(d => d.e_tot);
            
            const layout = {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: {{ color: '#94a3b8' }},
                margin: {{ t: 20, r: 20, b: 50, l: 60 }}
            }};
            
            // Total Energy
            Plotly.newPlot('energy-plot', [{{
                x: times, y: eTot,
                type: 'scatter', mode: 'lines',
                name: 'E_total',
                line: {{ color: '#3b82f6', width: 2 }}
            }}], {{
                ...layout,
                xaxis: {{ title: 'Time (fs)', gridcolor: '#334155' }},
                yaxis: {{ title: 'Energy (eV)', gridcolor: '#334155' }}
            }});
            
            // Temperature
            Plotly.newPlot('temp-plot', [{{
                x: times, y: temps,
                type: 'scatter', mode: 'lines',
                name: 'Temperature',
                line: {{ color: '#f59e0b', width: 2 }}
            }}], {{
                ...layout,
                xaxis: {{ title: 'Time (fs)', gridcolor: '#334155' }},
                yaxis: {{ title: 'Temperature (K)', gridcolor: '#334155' }}
            }});
            
            // Energy breakdown
            Plotly.newPlot('energy-breakdown', [
                {{
                    x: times, y: ePot,
                    type: 'scatter', mode: 'lines',
                    name: 'E_pot',
                    line: {{ color: '#10b981', width: 2 }}
                }},
                {{
                    x: times, y: eKin,
                    type: 'scatter', mode: 'lines',
                    name: 'E_kin',
                    line: {{ color: '#ef4444', width: 2 }}
                }}
            ], {{
                ...layout,
                xaxis: {{ title: 'Time (fs)', gridcolor: '#334155' }},
                yaxis: {{ title: 'Energy (eV)', gridcolor: '#334155' }},
                legend: {{ x: 0.02, y: 0.98 }}
            }});
        }}
        
        // 초기화
        document.addEventListener('DOMContentLoaded', () => {{
            initViewer();
            initPlots();
        }});
        '''
    
    def generate(self, output_path: str = "md_report.html") -> str:
        """리포트 생성"""
        content = self.generate_content()
        extra_js = self._generate_js()
        
        html = self.render_html(
            title="MD Simulation Report",
            content=content,
            extra_js=extra_js
        )
        
        output_file = self.save(html, output_path)
        print(f"✓ MD Report generated: {output_file}")
        return output_file
