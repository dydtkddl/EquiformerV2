"""
Visualization Module

플롯 및 시각화 도구
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import json


def create_energy_distribution_plot(energies: List[float],
                                     names: List[str] = None,
                                     output_path: str = "energy_distribution.html",
                                     title: str = "Adsorption Energy Distribution") -> str:
    """에너지 분포 히스토그램 (Plotly HTML)"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 20px; }}
        #plot {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; }}
        .stats {{ 
            display: flex; 
            justify-content: center; 
            gap: 40px; 
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        .stat {{ 
            text-align: center;
            background: rgba(255,255,255,0.1);
            padding: 15px 25px;
            border-radius: 10px;
        }}
        .stat-value {{ font-size: 24px; color: #00ff88; }}
        .stat-label {{ font-size: 12px; color: #aaa; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {title}</h1>
        <div id="plot"></div>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(energies)}</div>
                <div class="stat-label">Configurations</div>
            </div>
            <div class="stat">
                <div class="stat-value">{min(energies):.3f} eV</div>
                <div class="stat-label">Minimum</div>
            </div>
            <div class="stat">
                <div class="stat-value">{max(energies):.3f} eV</div>
                <div class="stat-label">Maximum</div>
            </div>
            <div class="stat">
                <div class="stat-value">{np.mean(energies):.3f} eV</div>
                <div class="stat-label">Mean</div>
            </div>
        </div>
    </div>
    
    <script>
        const energies = {json.dumps(energies)};
        const names = {json.dumps(names or [])};
        
        const trace = {{
            x: energies,
            type: 'histogram',
            nbinsx: 30,
            marker: {{
                color: 'rgba(0, 255, 136, 0.7)',
                line: {{ color: 'rgba(0, 255, 136, 1)', width: 1 }}
            }},
            hovertemplate: 'Energy: %{{x:.3f}} eV<br>Count: %{{y}}<extra></extra>'
        }};
        
        const layout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#fff' }},
            xaxis: {{
                title: 'Adsorption Energy (eV)',
                gridcolor: 'rgba(255,255,255,0.1)',
                zerolinecolor: 'rgba(255,255,255,0.2)'
            }},
            yaxis: {{
                title: 'Count',
                gridcolor: 'rgba(255,255,255,0.1)',
                zerolinecolor: 'rgba(255,255,255,0.2)'
            }},
            margin: {{ t: 30, r: 30, b: 60, l: 60 }}
        }};
        
        Plotly.newPlot('plot', [trace], layout, {{responsive: true}});
    </script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return output_path


def create_msd_plot(time: List[float],
                    msd: List[float],
                    species: str,
                    diffusion_fit: Optional[Dict] = None,
                    output_path: str = "msd_plot.html") -> str:
    """MSD 플롯"""
    
    fit_line_js = ""
    if diffusion_fit:
        # D = slope / 6, so slope = 6*D
        D = diffusion_fit.get("D_cm2_s", 0) / 0.1  # cm²/s -> Å²/fs
        slope = 6 * D
        fit_start = diffusion_fit.get("fit_start", time[0])
        fit_end = diffusion_fit.get("fit_end", time[-1])
        
        fit_line_js = f"""
        const fitTrace = {{
            x: [{fit_start}, {fit_end}],
            y: [{slope * fit_start}, {slope * fit_end}],
            mode: 'lines',
            name: 'Linear Fit (D = {diffusion_fit.get("D_cm2_s", 0):.2e} cm²/s)',
            line: {{ color: 'red', dash: 'dash', width: 2 }}
        }};
        data.push(fitTrace);
        """
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>MSD Plot - {species}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; }}
        #plot {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Mean Square Displacement - {species}</h1>
        <div id="plot"></div>
    </div>
    
    <script>
        const time = {json.dumps(time)};
        const msd = {json.dumps(msd)};
        
        const data = [{{
            x: time,
            y: msd,
            mode: 'lines',
            name: 'MSD',
            line: {{ color: '#00ff88', width: 2 }}
        }}];
        
        {fit_line_js}
        
        const layout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#fff' }},
            xaxis: {{
                title: 'Time (fs)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            yaxis: {{
                title: 'MSD (Å²)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            legend: {{ x: 0.02, y: 0.98 }},
            margin: {{ t: 30, r: 30, b: 60, l: 60 }}
        }};
        
        Plotly.newPlot('plot', data, layout, {{responsive: true}});
    </script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return output_path


def create_rdf_plot(r: List[float],
                    g_r: List[float],
                    pair: Tuple[str, str],
                    output_path: str = "rdf_plot.html") -> str:
    """RDF 플롯"""
    
    pair_str = f"{pair[0]}-{pair[1]}"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>RDF - {pair_str}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; }}
        #plot {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔵 Radial Distribution Function - {pair_str}</h1>
        <div id="plot"></div>
    </div>
    
    <script>
        const r = {json.dumps(r)};
        const g_r = {json.dumps(g_r)};
        
        const trace = {{
            x: r,
            y: g_r,
            mode: 'lines',
            fill: 'tozeroy',
            fillcolor: 'rgba(0, 255, 136, 0.2)',
            line: {{ color: '#00ff88', width: 2 }}
        }};
        
        const layout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#fff' }},
            xaxis: {{
                title: 'r (Å)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            yaxis: {{
                title: 'g(r)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            shapes: [{{
                type: 'line',
                x0: 0, x1: Math.max(...r),
                y0: 1, y1: 1,
                line: {{ color: 'rgba(255,255,255,0.5)', width: 1, dash: 'dash' }}
            }}],
            margin: {{ t: 30, r: 30, b: 60, l: 60 }}
        }};
        
        Plotly.newPlot('plot', [trace], layout, {{responsive: true}});
    </script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return output_path


def create_correlation_plot(x_data: List[float],
                             y_data: List[float],
                             x_label: str,
                             y_label: str,
                             names: List[str] = None,
                             output_path: str = "correlation_plot.html") -> str:
    """상관관계 플롯"""
    
    # 선형 회귀
    from scipy import stats
    slope, intercept, r_value, _, _ = stats.linregress(x_data, y_data)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Correlation: {x_label} vs {y_label}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; }}
        #plot {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; }}
        .r2 {{ text-align: center; font-size: 18px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {x_label} vs {y_label}</h1>
        <div id="plot"></div>
        <div class="r2">R² = {r_value**2:.4f}</div>
    </div>
    
    <script>
        const x = {json.dumps(x_data)};
        const y = {json.dumps(y_data)};
        const names = {json.dumps(names or [])};
        
        const scatter = {{
            x: x,
            y: y,
            mode: 'markers',
            type: 'scatter',
            text: names,
            marker: {{
                size: 10,
                color: '#00ff88',
                line: {{ color: '#fff', width: 1 }}
            }},
            hovertemplate: names.length ? '%{{text}}<br>{x_label}: %{{x:.3f}}<br>{y_label}: %{{y:.3f}}<extra></extra>' : '{x_label}: %{{x:.3f}}<br>{y_label}: %{{y:.3f}}<extra></extra>'
        }};
        
        const fitLine = {{
            x: [Math.min(...x), Math.max(...x)],
            y: [{intercept} + {slope} * Math.min(...x), {intercept} + {slope} * Math.max(...x)],
            mode: 'lines',
            line: {{ color: 'red', dash: 'dash' }},
            name: 'Linear Fit'
        }};
        
        const layout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#fff' }},
            xaxis: {{
                title: '{x_label}',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            yaxis: {{
                title: '{y_label}',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            showlegend: false,
            margin: {{ t: 30, r: 30, b: 60, l: 60 }}
        }};
        
        Plotly.newPlot('plot', [scatter, fitLine], layout, {{responsive: true}});
    </script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return output_path


def create_boltzmann_plot(names: List[str],
                           probabilities: List[float],
                           energies: List[float],
                           temperature: float,
                           output_path: str = "boltzmann_plot.html") -> str:
    """Boltzmann 분포 플롯"""
    
    # 확률순 정렬
    sorted_indices = np.argsort(probabilities)[::-1]
    sorted_names = [names[i] for i in sorted_indices]
    sorted_probs = [probabilities[i] for i in sorted_indices]
    sorted_energies = [energies[i] for i in sorted_indices]
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Boltzmann Distribution</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; }}
        .subtitle {{ text-align: center; color: #aaa; margin-bottom: 20px; }}
        #plot {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎲 Boltzmann Distribution</h1>
        <div class="subtitle">T = {temperature} K</div>
        <div id="plot"></div>
    </div>
    
    <script>
        const names = {json.dumps(sorted_names[:20])};  // Top 20
        const probs = {json.dumps(sorted_probs[:20])};
        const energies = {json.dumps(sorted_energies[:20])};
        
        const trace = {{
            y: names,
            x: probs.map(p => p * 100),
            type: 'bar',
            orientation: 'h',
            marker: {{
                color: probs.map(p => `rgba(0, 255, 136, ${{0.3 + p * 0.7}})`),
                line: {{ color: '#00ff88', width: 1 }}
            }},
            text: probs.map((p, i) => `${{(p*100).toFixed(1)}}% (E=${{energies[i].toFixed(3)}} eV)`),
            textposition: 'outside',
            hovertemplate: '%{{y}}<br>Probability: %{{x:.1f}}%<extra></extra>'
        }};
        
        const layout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#fff', size: 10 }},
            xaxis: {{
                title: 'Probability (%)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            yaxis: {{
                autorange: 'reversed'
            }},
            margin: {{ t: 30, r: 150, b: 60, l: 150 }}
        }};
        
        Plotly.newPlot('plot', [trace], layout, {{responsive: true}});
    </script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return output_path


def create_arrhenius_plot(temperatures: List[float],
                           diffusion_coefficients: List[float],
                           species: str,
                           output_path: str = "arrhenius_plot.html") -> str:
    """Arrhenius 플롯 (ln(D) vs 1/T)"""
    
    inv_T = [1000 / T for T in temperatures]  # 1000/K
    ln_D = [np.log(D) if D > 0 else float('nan') for D in diffusion_coefficients]
    
    # 선형 피팅
    valid_idx = [i for i, d in enumerate(ln_D) if not np.isnan(d)]
    if len(valid_idx) >= 2:
        inv_T_valid = [inv_T[i] for i in valid_idx]
        ln_D_valid = [ln_D[i] for i in valid_idx]
        
        from scipy import stats
        slope, intercept, r_value, _, _ = stats.linregress(inv_T_valid, ln_D_valid)
        
        # 활성화 에너지: Ea = -slope * kB
        kB_eV = 8.617333262e-5  # eV/K
        Ea = -slope * kB_eV * 1000  # eV (1000은 1000/K 단위 보정)
    else:
        slope, intercept, r_value, Ea = 0, 0, 0, 0
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Arrhenius Plot - {species}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            margin: 0;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; }}
        #plot {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; }}
        .ea {{ text-align: center; font-size: 18px; margin-top: 10px; color: #00ff88; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 Arrhenius Plot - {species}</h1>
        <div id="plot"></div>
        <div class="ea">Activation Energy: {Ea:.3f} eV (R² = {r_value**2:.4f})</div>
    </div>
    
    <script>
        const invT = {json.dumps(inv_T)};
        const lnD = {json.dumps(ln_D)};
        const temps = {json.dumps(temperatures)};
        
        const scatter = {{
            x: invT,
            y: lnD,
            mode: 'markers',
            text: temps.map(t => t + ' K'),
            marker: {{
                size: 12,
                color: '#00ff88',
                line: {{ color: '#fff', width: 1 }}
            }},
            hovertemplate: 'T = %{{text}}<br>1000/T = %{{x:.3f}}<br>ln(D) = %{{y:.3f}}<extra></extra>'
        }};
        
        const fitLine = {{
            x: [Math.min(...invT), Math.max(...invT)],
            y: [{intercept} + {slope} * Math.min(...invT), {intercept} + {slope} * Math.max(...invT)],
            mode: 'lines',
            line: {{ color: 'red', dash: 'dash' }},
            name: 'Linear Fit'
        }};
        
        const layout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#fff' }},
            xaxis: {{
                title: '1000/T (1/K)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            yaxis: {{
                title: 'ln(D) (D in cm²/s)',
                gridcolor: 'rgba(255,255,255,0.1)'
            }},
            showlegend: false,
            margin: {{ t: 30, r: 30, b: 60, l: 60 }}
        }};
        
        Plotly.newPlot('plot', [scatter, fitLine], layout, {{responsive: true}});
    </script>
</body>
</html>"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return output_path
