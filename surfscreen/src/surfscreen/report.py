"""
SurfScreen Enterprise Report Generator

고급 인터렉티브 HTML 리포트 생성
- 다크/라이트 모드
- 고급 필터링 및 검색
- 에너지 분포 히스토그램
- 사이트 타입별 파이 차트
- 구조 비교 모드
- CSV/JSON 내보내기
- 반응형 디자인
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import pandas as pd
import numpy as np


class ReportGenerator:
    """엔터프라이즈급 스크리닝 결과 HTML 리포트 생성기"""
    
    HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SurfScreen Report - {title}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0f1c;
            --bg-secondary: #111827;
            --bg-card: #1f2937;
            --bg-hover: #374151;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent: #06b6d4;
            --accent-hover: #22d3ee;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --purple: #8b5cf6;
            --pink: #ec4899;
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-accent: linear-gradient(135deg, #06b6d4 0%, #8b5cf6 100%);
            --shadow-lg: 0 10px 40px rgba(0,0,0,0.4);
            --shadow-glow: 0 0 30px rgba(6, 182, 212, 0.3);
            --border-radius: 16px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        [data-theme="light"] {{
            --bg-primary: #f3f4f6;
            --bg-secondary: #ffffff;
            --bg-card: #f9fafb;
            --bg-hover: #e5e7eb;
            --text-primary: #111827;
            --text-secondary: #4b5563;
            --text-muted: #9ca3af;
            --shadow-lg: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        /* Header */
        .header {{
            background: var(--gradient-primary);
            padding: 2.5rem 2rem;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        }}
        
        .header-content {{
            position: relative;
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header h1 {{
            font-size: 2rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .header h1 span {{
            font-size: 2.5rem;
        }}
        
        .header-meta {{
            display: flex;
            gap: 2rem;
            align-items: center;
        }}
        
        .header-stat {{
            text-align: right;
        }}
        
        .header-stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
        }}
        
        .header-stat-label {{
            font-size: 0.85rem;
            opacity: 0.8;
        }}
        
        /* Theme Toggle */
        .theme-toggle {{
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 50%;
            width: 44px;
            height: 44px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: var(--transition);
            font-size: 1.25rem;
        }}
        
        .theme-toggle:hover {{
            background: rgba(255,255,255,0.3);
            transform: rotate(15deg);
        }}
        
        /* Container */
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-secondary);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            transition: var(--transition);
            border: 1px solid rgba(255,255,255,0.05);
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-accent);
        }}
        
        .stat-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .stat-icon.cyan {{ background: rgba(6, 182, 212, 0.2); }}
        .stat-icon.green {{ background: rgba(16, 185, 129, 0.2); }}
        .stat-icon.purple {{ background: rgba(139, 92, 246, 0.2); }}
        .stat-icon.orange {{ background: rgba(245, 158, 11, 0.2); }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            background: var(--gradient-accent);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }}
        
        .stat-change {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.85rem;
            margin-top: 0.5rem;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
        }}
        
        .stat-change.positive {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
        .stat-change.negative {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
        
        /* Section */
        .section {{
            background: var(--bg-secondary);
            border-radius: var(--border-radius);
            margin-bottom: 2rem;
            border: 1px solid rgba(255,255,255,0.05);
            overflow: hidden;
        }}
        
        .section-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .section-content {{
            padding: 1.5rem;
        }}
        
        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }}
        
        @media (max-width: 1024px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .chart-container {{
            height: 350px;
        }}
        
        /* 3D Viewer Section */
        .viewer-section {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }}
        
        @media (max-width: 900px) {{
            .viewer-section {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .viewer-card {{
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }}
        
        .viewer-header {{
            padding: 1rem;
            background: rgba(0,0,0,0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .viewer-title {{
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .viewer-badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        
        .viewer-badge.rank-1 {{ background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; }}
        .viewer-badge.rank-2 {{ background: linear-gradient(135deg, #9ca3af, #6b7280); color: #fff; }}
        .viewer-badge.rank-3 {{ background: linear-gradient(135deg, #cd7f32, #b8860b); color: #fff; }}
        
        .mol-viewer {{
            height: 350px;
            background: #1a1a2e;
            position: relative;
            overflow: hidden;
        }}
        
        .viewer-controls {{
            display: flex;
            gap: 0.5rem;
        }}
        
        .viewer-btn {{
            padding: 0.35rem 0.7rem;
            border-radius: 6px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: var(--transition);
            background: var(--bg-hover);
            border: 1px solid rgba(255,255,255,0.1);
            color: var(--text-primary);
        }}
        
        .viewer-btn:hover {{
            background: var(--accent);
            color: white;
        }}
        
        .viewer-btn.active {{
            background: var(--accent);
            color: white;
        }}
        
        .viewer-info {{
            padding: 1rem;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.75rem;
        }}
        
        .viewer-info-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .viewer-info-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .viewer-info-value {{
            font-weight: 600;
            color: var(--accent);
        }}
        
        /* Toolbar */
        .toolbar {{
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .search-box {{
            display: flex;
            align-items: center;
            background: var(--bg-card);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            gap: 0.5rem;
            flex: 1;
            max-width: 300px;
        }}
        
        .search-box input {{
            background: transparent;
            border: none;
            color: var(--text-primary);
            outline: none;
            width: 100%;
            font-size: 0.9rem;
        }}
        
        .search-box input::placeholder {{
            color: var(--text-muted);
        }}
        
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            border: none;
        }}
        
        .btn-primary {{
            background: var(--gradient-accent);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-glow);
        }}
        
        .btn-secondary {{
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .btn-secondary:hover {{
            background: var(--bg-hover);
        }}
        
        .filter-chips {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        
        .chip {{
            padding: 0.4rem 0.9rem;
            border-radius: 20px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: var(--transition);
            background: var(--bg-card);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .chip:hover, .chip.active {{
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }}
        
        /* Table */
        .table-container {{
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            background: var(--bg-card);
            position: sticky;
            top: 0;
            z-index: 10;
            cursor: pointer;
            user-select: none;
        }}
        
        th:hover {{
            color: var(--accent);
        }}
        
        th .sort-icon {{
            margin-left: 0.25rem;
            opacity: 0.5;
        }}
        
        td {{
            padding: 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        
        tr {{
            transition: var(--transition);
        }}
        
        tr:hover {{
            background: var(--bg-hover);
        }}
        
        tr.selected {{
            background: rgba(6, 182, 212, 0.1);
            border-left: 3px solid var(--accent);
        }}
        
        .badge {{
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}
        
        .badge-top {{ background: rgba(6, 182, 212, 0.2); color: var(--accent); }}
        .badge-bridge {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
        .badge-hollow {{ background: rgba(139, 92, 246, 0.2); color: var(--purple); }}
        .badge-fcc {{ background: rgba(236, 72, 153, 0.2); color: var(--pink); }}
        .badge-hcp {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}
        .badge-unknown {{ background: rgba(107, 114, 128, 0.2); color: var(--text-muted); }}
        
        .energy-bar {{
            height: 6px;
            background: var(--bg-hover);
            border-radius: 3px;
            overflow: hidden;
            min-width: 100px;
        }}
        
        .energy-bar-fill {{
            height: 100%;
            background: var(--gradient-accent);
            border-radius: 3px;
            transition: width 0.5s ease;
        }}
        
        .rank-badge {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.85rem;
        }}
        
        .rank-badge.gold {{ background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; }}
        .rank-badge.silver {{ background: linear-gradient(135deg, #9ca3af, #6b7280); color: #fff; }}
        .rank-badge.bronze {{ background: linear-gradient(135deg, #cd7f32, #b8860b); color: #fff; }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.9rem;
            border-top: 1px solid rgba(255,255,255,0.05);
        }}
        
        .footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .animate-in {{
            animation: fadeIn 0.5s ease forwards;
        }}
        
        /* Modal */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(4px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            padding: 2rem;
        }}
        
        .modal-overlay.active {{
            display: flex;
        }}
        
        .modal {{
            background: var(--bg-secondary);
            border-radius: var(--border-radius);
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: var(--shadow-lg);
            animation: modalIn 0.3s ease;
        }}
        
        @keyframes modalIn {{
            from {{ opacity: 0; transform: scale(0.9); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        
        .modal-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .modal-title {{
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .modal-close {{
            background: transparent;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-muted);
            transition: var(--transition);
        }}
        
        .modal-close:hover {{
            color: var(--danger);
        }}
        
        .modal-body {{
            padding: 1.5rem;
        }}
        
        .modal-viewer {{
            height: 450px;
            background: #1a1a2e;
            border-radius: 12px;
            margin-bottom: 1rem;
            position: relative;
            overflow: hidden;
        }}
        
        .modal-info {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }}
        
        @media (max-width: 600px) {{
            .modal-info {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        .modal-info-item {{
            background: var(--bg-card);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }}
        
        .modal-info-value {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--accent);
        }}
        
        .modal-info-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        
        tr.clickable {{
            cursor: pointer;
        }}
        
        tr.clickable:hover {{
            background: rgba(6, 182, 212, 0.1);
        }}
        
        /* Print Styles */
        @media print {{
            .theme-toggle, .toolbar, .btn {{ display: none !important; }}
            body {{ background: white; color: black; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1><span>🧪</span> SurfScreen Report</h1>
            <div class="header-meta">
                <div class="header-stat">
                    <div class="header-stat-value">{title}</div>
                    <div class="header-stat-label">{timestamp}</div>
                </div>
                <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">🌙</button>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- Stats -->
        <div class="stats-grid animate-in">
            <div class="stat-card">
                <div class="stat-icon cyan">📊</div>
                <div class="stat-value">{n_configs}</div>
                <div class="stat-label">Total Configurations</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon green">⚡</div>
                <div class="stat-value">{best_energy:.3f}</div>
                <div class="stat-label">Best E_ads (eV)</div>
                <div class="stat-change negative">↓ Most Stable</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon purple">🎯</div>
                <div class="stat-value">{best_site}</div>
                <div class="stat-label">Optimal Site Type</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon orange">🔄</div>
                <div class="stat-value">{avg_steps:.0f}</div>
                <div class="stat-label">Avg. Optimization Steps</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts-grid">
            <div class="section animate-in" style="animation-delay: 0.1s">
                <div class="section-header">
                    <div class="section-title">📈 Energy Distribution</div>
                </div>
                <div class="section-content">
                    <div id="energy-bar-chart" class="chart-container"></div>
                </div>
            </div>
            
            <div class="section animate-in" style="animation-delay: 0.2s">
                <div class="section-header">
                    <div class="section-title">🎨 Site Type Breakdown</div>
                </div>
                <div class="section-content">
                    <div id="site-pie-chart" class="chart-container"></div>
                </div>
            </div>
        </div>
        
        <!-- Energy Histogram -->
        <div class="section animate-in" style="animation-delay: 0.3s">
            <div class="section-header">
                <div class="section-title">📊 Energy Histogram</div>
            </div>
            <div class="section-content">
                <div id="energy-histogram" class="chart-container"></div>
            </div>
        </div>
        
        <!-- 3D Viewers -->
        <div class="section animate-in" style="animation-delay: 0.4s">
            <div class="section-header">
                <div class="section-title">🔬 Top Structures</div>
            </div>
            <div class="section-content">
                <div class="viewer-section">
                    <div class="viewer-card">
                        <div class="viewer-header">
                            <div class="viewer-title">
                                <span class="viewer-badge rank-1">🥇 #1</span>
                                {best_config}
                            </div>
                            <div class="viewer-controls">
                                <button class="viewer-btn" onclick="toggleAxes(1)" title="Toggle cell axes">📐 Axes</button>
                                <button class="viewer-btn" onclick="togglePBC(1)" title="Toggle periodic images">🔁 PBC</button>
                                <button class="viewer-btn" onclick="toggleSpin(1)" title="Toggle rotation">🔄 Spin</button>
                            </div>
                        </div>
                        <div class="mol-viewer" id="viewer-1"></div>
                        <div class="viewer-info">
                            <div class="viewer-info-item">
                                <span class="viewer-info-label">Energy</span>
                                <span class="viewer-info-value">{best_energy:.4f} eV</span>
                            </div>
                            <div class="viewer-info-item">
                                <span class="viewer-info-label">Site</span>
                                <span class="viewer-info-value">{best_site}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="viewer-card">
                        <div class="viewer-header">
                            <div class="viewer-title">
                                <span class="viewer-badge rank-2">🥈 #2</span>
                                {second_config}
                            </div>
                            <div class="viewer-controls">
                                <button class="viewer-btn" onclick="toggleAxes(2)" title="Toggle cell axes">📐 Axes</button>
                                <button class="viewer-btn" onclick="togglePBC(2)" title="Toggle periodic images">🔁 PBC</button>
                                <button class="viewer-btn" onclick="toggleSpin(2)" title="Toggle rotation">🔄 Spin</button>
                            </div>
                        </div>
                        <div class="mol-viewer" id="viewer-2"></div>
                        <div class="viewer-info">
                            <div class="viewer-info-item">
                                <span class="viewer-info-label">Energy</span>
                                <span class="viewer-info-value">{second_energy:.4f} eV</span>
                            </div>
                            <div class="viewer-info-item">
                                <span class="viewer-info-label">Site</span>
                                <span class="viewer-info-value">{second_site}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Results Table -->
        <div class="section animate-in" style="animation-delay: 0.5s">
            <div class="section-header">
                <div class="section-title">📋 All Results</div>
                <div class="toolbar">
                    <div class="search-box">
                        <span>🔍</span>
                        <input type="text" id="searchInput" placeholder="Search configurations..." oninput="filterTable()">
                    </div>
                    <div class="filter-chips">
                        <span class="chip active" onclick="filterByType('all')">All</span>
                        <span class="chip" onclick="filterByType('top')">Top</span>
                        <span class="chip" onclick="filterByType('bridge')">Bridge</span>
                        <span class="chip" onclick="filterByType('hollow')">Hollow</span>
                    </div>
                    <button class="btn btn-secondary" onclick="exportCSV()">📥 Export CSV</button>
                    <button class="btn btn-secondary" onclick="exportJSON()">📥 Export JSON</button>
                </div>
            </div>
            <div class="section-content">
                <div class="table-container">
                    <table id="resultsTable">
                        <thead>
                            <tr>
                                <th onclick="sortTable(0)">Rank <span class="sort-icon">↕</span></th>
                                <th onclick="sortTable(1)">Configuration <span class="sort-icon">↕</span></th>
                                <th onclick="sortTable(2)">Site Type <span class="sort-icon">↕</span></th>
                                <th onclick="sortTable(3)">E_ads (eV) <span class="sort-icon">↕</span></th>
                                <th>Relative</th>
                                <th onclick="sortTable(5)">Steps <span class="sort-icon">↕</span></th>
                                <th onclick="sortTable(6)">Status <span class="sort-icon">↕</span></th>
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
    
    <div class="footer">
        Generated by <a href="#">SurfScreen v0.1.0</a> — Enterprise Surface Adsorption Screening Platform<br>
        <small>Powered by MACE MLIP | {timestamp}</small>
    </div>
    
    <!-- Structure Modal -->
    <div class="modal-overlay" id="structureModal" onclick="closeModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title">
                    <span>🔬</span>
                    <span id="modalTitle">Structure Viewer</span>
                </div>
                <div class="viewer-controls">
                    <button class="viewer-btn" onclick="toggleModalAxes()" title="Toggle cell axes">📐 Axes</button>
                    <button class="viewer-btn" onclick="toggleModalPBC()" title="Toggle periodic images">🔁 PBC</button>
                    <select id="pbcRepeat" class="viewer-btn" onchange="updateModalPBC()" title="PBC repeat count">
                        <option value="1">1×1</option>
                        <option value="2">2×2</option>
                        <option value="3" selected>3×3</option>
                        <option value="5">5×5</option>
                    </select>
                    <button class="viewer-btn" onclick="toggleModalSpin()" title="Toggle rotation">🔄 Spin</button>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
            </div>
            <div class="modal-body">
                <div class="modal-viewer" id="modalViewer"></div>
                <div class="modal-info">
                    <div class="modal-info-item">
                        <div class="modal-info-value" id="modalEnergy">-</div>
                        <div class="modal-info-label">E_ads (eV)</div>
                    </div>
                    <div class="modal-info-item">
                        <div class="modal-info-value" id="modalSite">-</div>
                        <div class="modal-info-label">Site Type</div>
                    </div>
                    <div class="modal-info-item">
                        <div class="modal-info-value" id="modalSteps">-</div>
                        <div class="modal-info-label">Opt Steps</div>
                    </div>
                    <div class="modal-info-item">
                        <div class="modal-info-value" id="modalRank">-</div>
                        <div class="modal-info-label">Rank</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Data
        const resultsData = {results_json};
        
        // Theme Toggle
        function toggleTheme() {{
            const body = document.body;
            const btn = document.querySelector('.theme-toggle');
            if (body.getAttribute('data-theme') === 'light') {{
                body.removeAttribute('data-theme');
                btn.textContent = '🌙';
            }} else {{
                body.setAttribute('data-theme', 'light');
                btn.textContent = '☀️';
            }}
        }}
        
        // Energy Bar Chart
        Plotly.newPlot('energy-bar-chart', [{{
            x: resultsData.slice(0, 15).map(r => r.name),
            y: resultsData.slice(0, 15).map(r => r.e_ads),
            type: 'bar',
            marker: {{
                color: resultsData.slice(0, 15).map(r => r.e_ads),
                colorscale: [[0, '#06b6d4'], [0.5, '#8b5cf6'], [1, '#ec4899']],
                reversescale: true
            }},
            hovertemplate: '<b>%{{x}}</b><br>E_ads: %{{y:.4f}} eV<extra></extra>'
        }}], {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#9ca3af' }},
            xaxis: {{
                tickangle: -45,
                gridcolor: 'rgba(255,255,255,0.05)'
            }},
            yaxis: {{
                title: 'E_ads (eV)',
                gridcolor: 'rgba(255,255,255,0.05)'
            }},
            margin: {{ t: 20, b: 100, l: 60, r: 20 }}
        }}, {{responsive: true}});
        
        // Site Type Pie Chart
        const siteCounts = {{}};
        resultsData.forEach(r => {{
            siteCounts[r.site_type] = (siteCounts[r.site_type] || 0) + 1;
        }});
        
        Plotly.newPlot('site-pie-chart', [{{
            values: Object.values(siteCounts),
            labels: Object.keys(siteCounts),
            type: 'pie',
            hole: 0.5,
            marker: {{
                colors: ['#06b6d4', '#10b981', '#8b5cf6', '#ec4899', '#f59e0b']
            }},
            textinfo: 'label+percent',
            textposition: 'outside',
            hovertemplate: '<b>%{{label}}</b><br>Count: %{{value}}<extra></extra>'
        }}], {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#9ca3af' }},
            showlegend: false,
            margin: {{ t: 20, b: 20, l: 20, r: 20 }}
        }}, {{responsive: true}});
        
        // Energy Histogram
        Plotly.newPlot('energy-histogram', [{{
            x: resultsData.map(r => r.e_ads),
            type: 'histogram',
            nbinsx: 20,
            marker: {{
                color: '#8b5cf6',
                line: {{ color: '#a78bfa', width: 1 }}
            }},
            hovertemplate: 'Range: %{{x:.2f}} eV<br>Count: %{{y}}<extra></extra>'
        }}], {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#9ca3af' }},
            xaxis: {{
                title: 'E_ads (eV)',
                gridcolor: 'rgba(255,255,255,0.05)'
            }},
            yaxis: {{
                title: 'Count',
                gridcolor: 'rgba(255,255,255,0.05)'
            }},
            margin: {{ t: 20, b: 50, l: 60, r: 20 }}
        }}, {{responsive: true}});
        
        // 3D Viewers - State
        const viewers = {{}};
        const viewerState = {{
            1: {{ axes: false, pbc: false, spin: true }},
            2: {{ axes: false, pbc: false, spin: true }}
        }};
        
        // Cell parameters (from surface) - approximate for Cu(111) 3x3
        const cellParams = {cell_params};
        
        function initViewer(id, xyz, viewerId) {{
            if (!xyz) return;
            const viewer = $3Dmol.createViewer(id, {{
                backgroundColor: '#1a1a2e'
            }});
            viewers[viewerId] = {{ viewer, xyz, models: [] }};
            
            // Add main model
            viewer.addModel(xyz, 'xyz');
            viewer.setStyle({{}}, {{
                stick: {{ radius: 0.12, colorscheme: 'Jmol' }},
                sphere: {{ scale: 0.25, colorscheme: 'Jmol' }}
            }});
            
            viewer.zoomTo();
            viewer.render();
            viewer.spin('y', 0.5);
        }}
        
        function toggleAxes(viewerId) {{
            const state = viewerState[viewerId];
            const vdata = viewers[viewerId];
            if (!vdata) return;
            
            state.axes = !state.axes;
            const btn = event.target;
            btn.classList.toggle('active', state.axes);
            
            if (state.axes && cellParams) {{
                // Draw cell axes from origin
                const origin = [0, 0, cellParams.zmin];
                const a = cellParams.a;
                const b = cellParams.b;
                const c = cellParams.c || 10;
                
                // X axis (red)
                vdata.viewer.addArrow({{
                    start: {{ x: origin[0], y: origin[1], z: origin[2] }},
                    end: {{ x: origin[0] + a[0], y: origin[1] + a[1], z: origin[2] }},
                    radius: 0.1,
                    color: '#ff4444'
                }});
                // Y axis (green)
                vdata.viewer.addArrow({{
                    start: {{ x: origin[0], y: origin[1], z: origin[2] }},
                    end: {{ x: origin[0] + b[0], y: origin[1] + b[1], z: origin[2] }},
                    radius: 0.1,
                    color: '#44ff44'
                }});
                // Z axis (blue)
                vdata.viewer.addArrow({{
                    start: {{ x: origin[0], y: origin[1], z: origin[2] }},
                    end: {{ x: origin[0], y: origin[1], z: origin[2] + c }},
                    radius: 0.1,
                    color: '#4444ff'
                }});
                
                // Draw cell box outline
                const corners = [
                    origin,
                    [origin[0] + a[0], origin[1] + a[1], origin[2]],
                    [origin[0] + a[0] + b[0], origin[1] + a[1] + b[1], origin[2]],
                    [origin[0] + b[0], origin[1] + b[1], origin[2]]
                ];
                for (let i = 0; i < 4; i++) {{
                    const c1 = corners[i];
                    const c2 = corners[(i + 1) % 4];
                    vdata.viewer.addCylinder({{
                        start: {{ x: c1[0], y: c1[1], z: c1[2] }},
                        end: {{ x: c2[0], y: c2[1], z: c2[2] }},
                        radius: 0.03,
                        color: '#888888',
                        dashed: true
                    }});
                }}
            }} else {{
                // Remove shapes by re-rendering
                vdata.viewer.removeAllShapes();
            }}
            vdata.viewer.render();
        }}
        
        function togglePBC(viewerId) {{
            const state = viewerState[viewerId];
            const vdata = viewers[viewerId];
            if (!vdata || !cellParams) return;
            
            state.pbc = !state.pbc;
            const btn = event.target;
            btn.classList.toggle('active', state.pbc);
            
            // Clear and rebuild
            vdata.viewer.removeAllModels();
            vdata.viewer.removeAllShapes();
            
            if (state.pbc) {{
                // Add main + 8 periodic images (3x3 in xy)
                const a = cellParams.a;
                const b = cellParams.b;
                const offsets = [
                    [0, 0], [-1, 0], [1, 0], [0, -1], [0, 1],
                    [-1, -1], [-1, 1], [1, -1], [1, 1]
                ];
                
                offsets.forEach(([i, j]) => {{
                    const model = vdata.viewer.addModel(vdata.xyz, 'xyz');
                    // Translate
                    const dx = i * a[0] + j * b[0];
                    const dy = i * a[1] + j * b[1];
                    model.setStyle({{}}, {{
                        stick: {{ radius: 0.12, colorscheme: 'Jmol' }},
                        sphere: {{ scale: 0.25, colorscheme: 'Jmol' }}
                    }});
                    if (i !== 0 || j !== 0) {{
                        // Fade periodic images
                        model.setStyle({{}}, {{
                            stick: {{ radius: 0.10, colorscheme: 'Jmol', opacity: 0.4 }},
                            sphere: {{ scale: 0.20, colorscheme: 'Jmol', opacity: 0.4 }}
                        }});
                    }}
                }});
            }} else {{
                vdata.viewer.addModel(vdata.xyz, 'xyz');
                vdata.viewer.setStyle({{}}, {{
                    stick: {{ radius: 0.12, colorscheme: 'Jmol' }},
                    sphere: {{ scale: 0.25, colorscheme: 'Jmol' }}
                }});
            }}
            
            // Re-add axes if enabled
            if (state.axes) {{
                state.axes = false;
                toggleAxes(viewerId);
            }}
            
            vdata.viewer.zoomTo();
            vdata.viewer.render();
        }}
        
        function toggleSpin(viewerId) {{
            const state = viewerState[viewerId];
            const vdata = viewers[viewerId];
            if (!vdata) return;
            
            state.spin = !state.spin;
            const btn = event.target;
            btn.classList.toggle('active', state.spin);
            
            if (state.spin) {{
                vdata.viewer.spin('y', 0.5);
            }} else {{
                vdata.viewer.spin(false);
            }}
        }}
        
        initViewer('viewer-1', `{xyz_best}`, 1);
        initViewer('viewer-2', `{xyz_second}`, 2);
        
        // Modal viewer state
        let modalViewer = null;
        const modalState = {{ axes: false, pbc: false, spin: true }};
        let currentModalXyz = '';
        
        // All XYZ data (injected from Python)
        const allXyzData = {xyz_data_json};
        
        function openStructureModal(configName, rank) {{
            const data = resultsData.find(r => r.name === configName);
            if (!data) return;
            
            const xyz = allXyzData[configName];
            if (!xyz) {{
                alert('Structure file not found: ' + configName);
                return;
            }}
            
            currentModalXyz = xyz;
            
            // Update modal info
            document.getElementById('modalTitle').textContent = configName;
            document.getElementById('modalEnergy').textContent = data.e_ads.toFixed(4);
            document.getElementById('modalSite').textContent = data.site_type || 'unknown';
            document.getElementById('modalSteps').textContent = data.steps;
            document.getElementById('modalRank').textContent = '#' + rank;
            
            // Show modal
            document.getElementById('structureModal').classList.add('active');
            
            // Initialize modal viewer (delay for DOM update)
            setTimeout(() => {{
                if (modalViewer) {{
                    modalViewer.removeAllModels();
                    modalViewer.removeAllShapes();
                }} else {{
                    modalViewer = $3Dmol.createViewer('modalViewer', {{
                        backgroundColor: '#1a1a2e'
                    }});
                }}
                
                modalViewer.addModel(xyz.replace(/\\\\n/g, '\\n'), 'xyz');
                modalViewer.setStyle({{}}, {{
                    stick: {{ radius: 0.12, colorscheme: 'Jmol' }},
                    sphere: {{ scale: 0.25, colorscheme: 'Jmol' }}
                }});
                modalViewer.zoomTo();
                modalViewer.render();
                
                // Reset state
                modalState.axes = false;
                modalState.pbc = false;
                modalState.spin = true;
                modalViewer.spin('y', 0.5);
                
                // Update button states
                document.querySelectorAll('#structureModal .viewer-btn').forEach(btn => {{
                    btn.classList.remove('active');
                    if (btn.textContent.includes('Spin')) btn.classList.add('active');
                }});
            }}, 100);
        }}
        
        function closeModal(event) {{
            if (event && event.target !== document.getElementById('structureModal')) return;
            document.getElementById('structureModal').classList.remove('active');
            if (modalViewer) {{
                modalViewer.spin(false);
            }}
        }}
        
        function toggleModalAxes() {{
            modalState.axes = !modalState.axes;
            event.target.classList.toggle('active', modalState.axes);
            
            if (modalState.axes && cellParams) {{
                const origin = [0, 0, cellParams.zmin];
                const a = cellParams.a, b = cellParams.b, c = cellParams.c || 10;
                
                modalViewer.addArrow({{ start: {{x:origin[0],y:origin[1],z:origin[2]}}, end:{{x:origin[0]+a[0],y:origin[1]+a[1],z:origin[2]}}, radius:0.1, color:'#ff4444' }});
                modalViewer.addArrow({{ start: {{x:origin[0],y:origin[1],z:origin[2]}}, end:{{x:origin[0]+b[0],y:origin[1]+b[1],z:origin[2]}}, radius:0.1, color:'#44ff44' }});
                modalViewer.addArrow({{ start: {{x:origin[0],y:origin[1],z:origin[2]}}, end:{{x:origin[0],y:origin[1],z:origin[2]+c}}, radius:0.1, color:'#4444ff' }});
            }} else {{
                modalViewer.removeAllShapes();
            }}
            modalViewer.render();
        }}
        
        function toggleModalPBC() {{
            modalState.pbc = !modalState.pbc;
            event.target.classList.toggle('active', modalState.pbc);
            renderModalPBC();
        }}
        
        function updateModalPBC() {{
            if (modalState.pbc) {{
                renderModalPBC();
            }}
        }}
        
        function renderModalPBC() {{
            modalViewer.removeAllModels();
            modalViewer.removeAllShapes();
            
            const xyz = currentModalXyz.replace(/\\\\n/g, '\\n');
            const repeatCount = parseInt(document.getElementById('pbcRepeat').value) || 3;
            
            if (modalState.pbc && cellParams) {{
                const a = cellParams.a, b = cellParams.b;
                const half = Math.floor(repeatCount / 2);
                
                // Generate offsets based on repeat count
                const offsets = [];
                for (let i = -half; i <= half; i++) {{
                    for (let j = -half; j <= half; j++) {{
                        offsets.push([i, j]);
                    }}
                }}
                
                offsets.forEach(([i, j]) => {{
                    modalViewer.addModel(xyz, 'xyz');
                    const isCenter = (i === 0 && j === 0);
                    const style = isCenter ? 
                        {{ stick:{{radius:0.12,colorscheme:'Jmol'}}, sphere:{{scale:0.25,colorscheme:'Jmol'}} }} :
                        {{ stick:{{radius:0.10,colorscheme:'Jmol',opacity:0.4}}, sphere:{{scale:0.20,colorscheme:'Jmol',opacity:0.4}} }};
                    modalViewer.setStyle({{}}, style);
                }});
            }} else {{
                modalViewer.addModel(xyz, 'xyz');
                modalViewer.setStyle({{}}, {{ stick:{{radius:0.12,colorscheme:'Jmol'}}, sphere:{{scale:0.25,colorscheme:'Jmol'}} }});
            }}
            
            if (modalState.axes) {{ modalState.axes = false; toggleModalAxes(); }}
            modalViewer.zoomTo();
            modalViewer.render();
        }}
        
        function toggleModalSpin() {{
            modalState.spin = !modalState.spin;
            event.target.classList.toggle('active', modalState.spin);
            modalViewer.spin(modalState.spin ? 'y' : false, 0.5);
        }}
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
        
        // Table Filter
        function filterTable() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#resultsTable tbody tr');
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            }});
        }}
        
        function filterByType(type) {{
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            
            const rows = document.querySelectorAll('#resultsTable tbody tr');
            rows.forEach(row => {{
                if (type === 'all') {{
                    row.style.display = '';
                }} else {{
                    const siteType = row.querySelector('.badge')?.textContent.toLowerCase();
                    row.style.display = siteType === type ? '' : 'none';
                }}
            }});
        }}
        
        // Table Sort
        let sortDirection = {{}};
        function sortTable(col) {{
            const table = document.getElementById('resultsTable');
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            sortDirection[col] = !sortDirection[col];
            
            rows.sort((a, b) => {{
                let aVal = a.cells[col].textContent.trim();
                let bVal = b.cells[col].textContent.trim();
                
                if (!isNaN(parseFloat(aVal))) {{
                    aVal = parseFloat(aVal);
                    bVal = parseFloat(bVal);
                }}
                
                if (sortDirection[col]) {{
                    return aVal > bVal ? 1 : -1;
                }} else {{
                    return aVal < bVal ? 1 : -1;
                }}
            }});
            
            const tbody = table.querySelector('tbody');
            rows.forEach(row => tbody.appendChild(row));
        }}
        
        // Export
        function exportCSV() {{
            let csv = 'name,site_type,e_ads,steps,converged\\n';
            resultsData.forEach(r => {{
                csv += `${{r.name}},${{r.site_type}},${{r.e_ads}},${{r.steps}},${{r.converged}}\\n`;
            }});
            downloadFile(csv, 'results.csv', 'text/csv');
        }}
        
        function exportJSON() {{
            const json = JSON.stringify(resultsData, null, 2);
            downloadFile(json, 'results.json', 'application/json');
        }}
        
        function downloadFile(content, filename, type) {{
            const blob = new Blob([content], {{ type }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>
'''
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.results_csv = self.results_dir / "results.csv"
        
        if not self.results_csv.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_csv}")
        
        self.df = pd.read_csv(self.results_csv)
        self.df = self.df.sort_values("e_ads")
    
    def generate(self, output_path: str = "report.html") -> str:
        # 통계
        n_configs = len(self.df)
        best_row = self.df.iloc[0]
        best_energy = best_row["e_ads"]
        best_config = best_row["name"]
        avg_steps = self.df["steps"].mean()
        best_site = best_row.get("site_type", "unknown") if "site_type" in self.df.columns else "unknown"
        
        # Second best
        if len(self.df) > 1:
            second_row = self.df.iloc[1]
            second_config = second_row["name"]
            second_energy = second_row["e_ads"]
            second_site = second_row.get("site_type", "unknown") if "site_type" in self.df.columns else "unknown"
        else:
            second_config, second_energy, second_site = best_config, best_energy, best_site
        
        # 테이블 행
        table_rows = []
        min_e = self.df["e_ads"].min()
        max_e = self.df["e_ads"].max()
        e_range = max_e - min_e if max_e != min_e else 1
        
        for idx, (_, row) in enumerate(self.df.iterrows()):
            rel_e = row["e_ads"] - min_e
            bar_width = 100 - (rel_e / e_range * 100)
            
            site_type = row.get("site_type", "unknown") if "site_type" in self.df.columns else "unknown"
            
            # Rank badge
            rank = idx + 1
            if rank == 1:
                rank_html = '<span class="rank-badge gold">1</span>'
            elif rank == 2:
                rank_html = '<span class="rank-badge silver">2</span>'
            elif rank == 3:
                rank_html = '<span class="rank-badge bronze">3</span>'
            else:
                rank_html = str(rank)
            
            converged = "✅" if row.get("converged", True) else "⚠️"
            config_name = row["name"]
            
            table_rows.append(f'''
                <tr class="clickable" onclick="openStructureModal('{config_name}', {rank})">
                    <td>{rank_html}</td>
                    <td><strong>{config_name}</strong></td>
                    <td><span class="badge badge-{site_type}">{site_type}</span></td>
                    <td>{row["e_ads"]:.4f}</td>
                    <td>
                        <div class="energy-bar">
                            <div class="energy-bar-fill" style="width: {bar_width:.1f}%"></div>
                        </div>
                    </td>
                    <td>{row["steps"]}</td>
                    <td>{converged}</td>
                </tr>
            ''')
        
        # Results JSON
        results_json = self.df.to_dict(orient='records')
        
        # XYZ 파일
        xyz_best = self._read_xyz(best_config)
        xyz_second = self._read_xyz(second_config)
        
        # All XYZ data for modal viewer
        xyz_data = {}
        for config_name in self.df["name"]:
            xyz_data[config_name] = self._read_xyz(config_name)
        
        # Cell parameters (try to extract from best xyz)
        cell_params = self._get_cell_params(best_config)
        
        # HTML 생성
        html = self.HTML_TEMPLATE.format(
            title=self.results_dir.name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            n_configs=n_configs,
            best_energy=best_energy,
            best_site=best_site,
            avg_steps=avg_steps,
            best_config=best_config,
            second_config=second_config,
            second_energy=second_energy,
            second_site=second_site,
            table_rows="".join(table_rows),
            results_json=json.dumps(results_json),
            xyz_best=xyz_best,
            xyz_second=xyz_second,
            cell_params=json.dumps(cell_params),
            xyz_data_json=json.dumps(xyz_data)
        )
        
        output_path = Path(output_path)
        output_path.write_text(html, encoding="utf-8")
        
        return str(output_path)
    
    def _read_xyz(self, config_name: str) -> str:
        xyz_path = self.results_dir / f"{config_name}.xyz"
        if xyz_path.exists():
            return xyz_path.read_text().replace('\n', '\\n').replace("'", "\\'")
        return ""
    
    def _get_cell_params(self, config_name: str) -> dict:
        """XYZ 파일에서 셀 파라미터 추출 (또는 기본값 사용)"""
        xyz_path = self.results_dir / f"{config_name}.xyz"
        
        # 기본값 (Cu(111) 3x3 slab 근사치)
        default_params = {
            "a": [7.67, 0.0],      # a 벡터 (x, y)
            "b": [3.84, 6.65],     # b 벡터 (x, y)
            "c": 15.0,             # z 방향 높이
            "zmin": 0.0
        }
        
        if not xyz_path.exists():
            return default_params
        
        try:
            # XYZ 파일 파싱하여 z 범위 계산
            lines = xyz_path.read_text().strip().split('\n')
            if len(lines) < 3:
                return default_params
            
            z_coords = []
            x_coords = []
            y_coords = []
            
            for line in lines[2:]:  # 첫 2줄 스킵 (원자 수, 주석)
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        x_coords.append(float(parts[1]))
                        y_coords.append(float(parts[2]))
                        z_coords.append(float(parts[3]))
                    except ValueError:
                        continue
            
            if z_coords:
                zmin = min(z_coords)
                # 셀 크기 추정 (원자 위치 범위에서)
                x_range = max(x_coords) - min(x_coords) if x_coords else 7.67
                y_range = max(y_coords) - min(y_coords) if y_coords else 6.65
                
                return {
                    "a": [x_range * 1.1, 0.0],
                    "b": [0.0, y_range * 1.1],
                    "c": 15.0,
                    "zmin": zmin
                }
        except Exception:
            pass
        
        return default_params
