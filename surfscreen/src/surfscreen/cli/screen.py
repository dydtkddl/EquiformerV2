"""
SurfScreen CLI - Screen Commands

흡착 스크리닝 관련 명령어
"""

import os
import click
from pathlib import Path

from surfscreen.cli.utils import console, Table


# ============ Screen Command Group ============

@click.group(name="screen")
def screen_group():
    """Screening operations"""
    pass


@screen_group.command("run")
@click.option("--surface", "-s", required=True, help="Surface file")
@click.option("--molecules", "-m", required=True, help="Molecule file(s) or glob pattern")
@click.option("--engine", "-e", default="mace", help="Calculator engine")
@click.option("--model", default="medium", help="Model size (for MACE)")
@click.option("--device", "-d", default="cuda", help="Device (cuda, cpu)")
@click.option("--rotations", "-r", default="0,45,90,135", help="Rotation angles")
@click.option("--output-dir", "-o", default="screening_results", help="Output directory")
@click.option("--max-configs", default=50, help="Max configurations per molecule")
@click.option("--ncpus", default=None, type=int, help="Number of CPU threads")
@click.option("--fix-layers", default=2, type=int, help="Number of bottom layers to fix")
def screen_run(surface, molecules, engine, model, device, rotations, output_dir, max_configs, ncpus, fix_layers):
    """Run adsorption screening"""
    import glob
    
    from surfscreen.surface import SurfaceBuilder
    from surfscreen.molecule import MoleculeBuilder
    from surfscreen.adsorption import AdsorptionSystem
    from surfscreen.calculator import CalculatorFactory
    
    # CPU 스레드 설정
    total_cpus = os.cpu_count() or 1
    if ncpus is None:
        ncpus = max(1, int(total_cpus * 0.8))
    
    os.environ["OMP_NUM_THREADS"] = str(ncpus)
    os.environ["MKL_NUM_THREADS"] = str(ncpus)
    
    try:
        import torch
        torch.set_num_threads(ncpus)
    except ImportError:
        pass
    
    # 파일 로드
    surf = SurfaceBuilder.from_file(surface, fixed_layers=fix_layers)
    mol_files = glob.glob(molecules) if '*' in molecules else [molecules]
    rots = [float(x) for x in rotations.split(",")]
    
    console.print(f"\n[bold]🚀 Starting Screening[/bold]")
    console.print(f"  Surface: {surface}")
    console.print(f"  Molecules: {len(mol_files)} files")
    console.print(f"  Engine: {engine}")
    console.print(f"  CPUs: {ncpus}/{total_cpus}")
    
    calc = CalculatorFactory.create(engine, model=model, device=device)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    
    for mol_file in mol_files:
        mol = MoleculeBuilder.from_file(mol_file)
        console.print(f"\n[bold]Processing: {mol.name}[/bold]")
        
        system = AdsorptionSystem(surf, mol)
        configs = system.generate_configurations(rotations=rots, max_configs=max_configs)
        
        console.print(f"  Generated {len(configs)} configurations")
        
        mol_output = output_path / mol.name
        mol_output.mkdir(parents=True, exist_ok=True)
        
        results = system.optimize_all(calc, output_dir=str(mol_output), progress=True)
        all_results.extend(results)
        system.export_results(results, str(mol_output / "results.csv"))
    
    # 결과 정렬
    all_results.sort(key=lambda x: x.adsorption_energy)
    
    console.print(f"\n[bold]🏆 Top Results[/bold]")
    
    table = Table()
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Config", style="green")
    table.add_column("E_ads (eV)", justify="right")
    
    for i, r in enumerate(all_results[:10], 1):
        table.add_row(str(i), r.config_name, f"{r.adsorption_energy:.4f}")
    
    console.print(table)
    console.print(f"\n[green]✓[/green] Results saved to: {output_path}")


@screen_group.command("results")
@click.argument("results_file")
@click.option("--sort", "-s", default="e_ads", help="Sort by column")
@click.option("--top", "-n", default=10, help="Show top N results")
def screen_results(results_file, sort, top):
    """View screening results"""
    import pandas as pd
    
    df = pd.read_csv(results_file)
    df = df.sort_values(sort).head(top)
    
    table = Table(title="Screening Results")
    for col in df.columns:
        table.add_column(col)
    
    for _, row in df.iterrows():
        table.add_row(*[str(v) for v in row])
    
    console.print(table)


@screen_group.command("report")
@click.argument("results_dir")
@click.option("--output", "-o", default="screening_report.html", help="Output HTML file")
@click.option("--theme", type=click.Choice(["dark", "light"]), default="dark", help="Report theme")
@click.option("--top", "-n", default=20, help="Top N results to display")
def screen_report(results_dir, output, theme, top):
    """Generate interactive HTML report with 3D viewer and charts"""
    from surfscreen.report import ScreeningReportGenerator
    
    with console.status("[bold green]Generating interactive report..."):
        gen = ScreeningReportGenerator(results_dir, theme=theme, top_n=top)
        out_path = gen.generate(output)
    
    console.print(f"[green]✓[/green] Report generated: {out_path}")
    console.print("   Features:")
    console.print("   - Interactive 3D structure viewer (3Dmol.js)")
    console.print("   - Energy distribution & Boltzmann analysis (Plotly)")
    console.print("   - Theme toggle (Dark/Light)")
    console.print("   - CSV/JSON/XYZ downloads")
    console.print(f"[dim]Open in browser: file://{Path(out_path).absolute()}[/dim]")


@screen_group.command("multi")
@click.option("--surface-file", "-s", required=True, help="Surface file")
@click.option("--molecules", "-m", required=True, help="Molecule files glob pattern")
@click.option("--output", "-o", default="multi_screening", help="Output directory")
@click.option("--engine", "-e", default="mace", help="Calculator engine")
@click.option("--parallel", "-p", is_flag=True, help="Enable parallel processing")
def screen_multi(surface_file, molecules, output, engine, parallel):
    """Screen multiple molecules on a surface"""
    import glob
    
    from surfscreen.surface import SurfaceBuilder
    from surfscreen.molecule import MoleculeBuilder
    from surfscreen.adsorption import AdsorptionSystem
    from surfscreen.calculator import CalculatorFactory
    
    mol_files = glob.glob(molecules)
    if not mol_files:
        console.print(f"[red]No molecules found matching: {molecules}[/red]")
        return
    
    console.print(f"\n[bold]🔬 Multi-molecule Screening[/bold]")
    console.print(f"  Surface: {surface_file}")
    console.print(f"  Molecules: {len(mol_files)}")
    
    surf = SurfaceBuilder.from_file(surface_file)
    calc = CalculatorFactory.create(engine)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    
    for i, mol_file in enumerate(mol_files, 1):
        mol = MoleculeBuilder.from_file(mol_file)
        console.print(f"\n  [{i}/{len(mol_files)}] {mol.name}")
        
        system = AdsorptionSystem(surf, mol)
        configs = system.generate_configurations()
        results = system.optimize_all(calc, output_dir=str(output_path / mol.name))
        
        if results:
            best = min(results, key=lambda x: x.adsorption_energy)
            all_results.append({"molecule": mol.name, "E_ads": best.adsorption_energy})
            console.print(f"    Best E_ads: {best.adsorption_energy:.4f} eV")
    
    # 결과 저장
    import json
    with open(output_path / "summary.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    console.print(f"\n[green]✓[/green] Results saved to: {output_path}")


__all__ = ["screen_group"]
