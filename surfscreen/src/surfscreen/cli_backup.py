"""
SurfScreen CLI

Click 기반 명령행 인터페이스
"""

import os
from pathlib import Path

# CPU 스레드 기본값 설정 (라이브러리 import 전에!)
def _set_cpu_threads():
    """전역 CPU 스레드 제한 (80% 기본)"""
    if "SURFSCREEN_NCPUS" in os.environ:
        ncpus = os.environ["SURFSCREEN_NCPUS"]
    else:
        total = os.cpu_count() or 1
        ncpus = str(max(1, int(total * 0.8)))
    
    os.environ.setdefault("OMP_NUM_THREADS", ncpus)
    os.environ.setdefault("MKL_NUM_THREADS", ncpus)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", ncpus)
    os.environ.setdefault("NUMEXPR_NUM_THREADS", ncpus)
    
_set_cpu_threads()

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


# Verbose 레벨 설정을 위한 콜백
def _setup_verbose(ctx, param, value):
    """Verbose 레벨 설정 콜백"""
    from surfscreen.logging_utils import set_verbose
    set_verbose(value)
    return value


@click.group()
@click.version_option(version="0.3.0", prog_name="surfscreen")
@click.option(
    "--verbose", "-v",
    type=click.Choice(['0', '1', '2', '3', '4', 'silent', 'low', 'medium', 'high', 'debug'],
                      case_sensitive=False),
    default='2',
    callback=_setup_verbose,
    expose_value=False,
    is_eager=True,
    help="Verbosity level: 0=silent, 1=low, 2=medium, 3=high, 4=debug"
)
def main():
    """SurfScreen: Enterprise Surface Adsorption Screening Platform
    
    Use --verbose/-v to control output detail level:
      0/silent : Only errors
      1/low    : Main steps only  
      2/medium : Progress info (default)
      3/high   : Detailed calculations
      4/debug  : Full debugging output
    """
    pass


# ============ Molecule Commands ============

@main.group()
def molecule():
    """Molecule operations"""
    pass


@molecule.command("from-smiles")
@click.argument("smiles")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--name", "-n", default="", help="Molecule name")
@click.option("--optimize/--no-optimize", default=True, help="Optimize geometry")
@click.option("--conformers", "-c", default=1, help="Number of conformers")
def mol_from_smiles(smiles, output, name, optimize, conformers):
    """Create molecule from SMILES string"""
    from surfscreen.molecule import MoleculeBuilder
    
    with console.status("[bold green]Generating molecule..."):
        mol = MoleculeBuilder.from_smiles(
            smiles, 
            name=name,
            optimize=optimize, 
            n_conformers=conformers
        )
    
    if isinstance(mol, list):
        console.print(f"[green]✓[/green] Generated {len(mol)} conformers")
        for i, m in enumerate(mol):
            out_path = output or f"{m.name}.xyz"
            if conformers > 1:
                out_path = out_path.replace(".xyz", f"_conf{i}.xyz")
            m.save(out_path)
            console.print(f"  Saved: {out_path}")
    else:
        out_path = output or f"{mol.name}.xyz"
        mol.save(out_path)
        console.print(f"[green]✓[/green] Formula: {mol.formula}")
        console.print(f"[green]✓[/green] Atoms: {mol.n_atoms}")
        console.print(f"[green]✓[/green] Saved: {out_path}")


@molecule.command("from-pubchem")
@click.argument("query")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--by", type=click.Choice(["cid", "name", "formula"]), default="name")
def mol_from_pubchem(query, output, by):
    """Fetch molecule from PubChem database"""
    from surfscreen.molecule import MoleculeBuilder
    
    with console.status(f"[bold green]Fetching from PubChem ({by}: {query})..."):
        if by == "cid":
            mol = MoleculeBuilder.from_pubchem(cid=int(query))
        elif by == "name":
            mol = MoleculeBuilder.from_pubchem(name=query)
        else:
            mol = MoleculeBuilder.from_pubchem(formula=query)
    
    out_path = output or f"{query}.xyz"
    mol.save(out_path)
    
    console.print(f"[green]✓[/green] Formula: {mol.formula}")
    console.print(f"[green]✓[/green] Atoms: {mol.n_atoms}")
    console.print(f"[green]✓[/green] Saved: {out_path}")


@molecule.command("conformers")
@click.argument("input_file")
@click.option("--engine", "-e", type=click.Choice(["rdkit", "crest", "xtb"]), default="rdkit")
@click.option("--n-conformers", "-n", default=10)
@click.option("--energy-window", default=10.0, help="Energy window (kcal/mol)")
@click.option("--output-dir", "-o", default="conformers")
def mol_conformers(input_file, engine, n_conformers, energy_window, output_dir):
    """Generate conformers for a molecule"""
    from surfscreen.molecule import MoleculeBuilder, ConformerGenerator
    from pathlib import Path
    
    mol = MoleculeBuilder.from_file(input_file)
    
    with console.status(f"[bold green]Generating conformers with {engine}..."):
        gen = ConformerGenerator(engine=engine, energy_window=energy_window)
        conformers = gen.generate(mol, n_conformers=n_conformers)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[green]✓[/green] Generated {len(conformers)} conformers")
    for conf in conformers:
        out_path = output_dir / f"{conf.name}.xyz"
        conf.save(str(out_path))
    console.print(f"[green]✓[/green] Saved to: {output_dir}")


@molecule.command("analyze")
@click.argument("input_file")
def mol_analyze(input_file):
    """Analyze molecule structure"""
    from surfscreen.molecule import MoleculeBuilder
    from surfscreen.molecule.builder import MoleculeAnalyzer
    
    mol = MoleculeBuilder.from_file(input_file)
    
    console.print(f"\n[bold]🔍 Structure Analysis: {mol.name}[/bold]")
    console.print(f"  Formula: {mol.formula}")
    console.print(f"  Atoms: {mol.n_atoms}")
    
    # 작용기 분석
    groups = MoleculeAnalyzer.get_functional_groups(mol)
    if groups:
        console.print("\n  [bold]Functional Groups:[/bold]")
        for g in groups:
            console.print(f"    • {g.name} (atoms: {g.atoms})")
    
    # 흡착 중심
    centers = MoleculeAnalyzer.get_adsorption_centers(mol)
    if centers:
        console.print(f"\n  [bold]Adsorption Centers:[/bold]")
        for c in centers:
            symbol = mol.symbols[c]
            console.print(f"    • Atom {c} ({symbol})")
    
    # Footprint
    width, length = MoleculeAnalyzer.estimate_footprint(mol)
    console.print(f"\n  [bold]Estimated Footprint:[/bold] {width:.1f} × {length:.1f} Å")


# ============ Surface Commands ============

@main.group()
def surface():
    """Surface operations"""
    pass


@surface.command("create")
@click.argument("element")
@click.option("--miller", "-m", default="111", help="Miller index (e.g., 111, 100)")
@click.option("--layers", "-l", default=4, help="Number of layers")
@click.option("--supercell", "-s", default="3x3x1", help="Supercell (e.g., 3x3x1)")
@click.option("--vacuum", "-v", default=15.0, help="Vacuum thickness (Å)")
@click.option("--fix", "-f", default=2, help="Fixed bottom layers")
@click.option("--output", "-o", default=None, help="Output file path")
def surface_create(element, miller, layers, supercell, vacuum, fix, output):
    """Create surface slab from element"""
    from surfscreen.surface import SurfaceBuilder
    
    # Parse miller index
    miller_idx = tuple(int(x) for x in miller)
    
    # Parse supercell
    sc = tuple(int(x) for x in supercell.split("x"))
    
    with console.status(f"[bold green]Creating {element}({miller}) surface..."):
        surf = SurfaceBuilder.from_element(
            element,
            miller_index=miller_idx,
            layers=layers,
            supercell=sc,
            vacuum=vacuum,
            fixed_layers=fix
        )
    
    out_path = output or f"{surf.name}.extxyz"
    surf.save(out_path)
    
    console.print(f"[green]✓[/green] Surface: {surf.name}")
    console.print(f"[green]✓[/green] Atoms: {surf.n_atoms}")
    console.print(f"[green]✓[/green] Area: {surf.area:.1f} Ų")
    console.print(f"[green]✓[/green] Fixed atoms: {len(surf.fixed_atoms)}")
    console.print(f"[green]✓[/green] Saved: {out_path}")


@surface.command("sites")
@click.argument("input_file")
@click.option("--types", "-t", default="all", help="Site types (top, bridge, hollow, all)")
@click.option("--visualize", "-v", is_flag=True, help="Show visualization")
def surface_sites(input_file, types, visualize):
    """Detect adsorption sites on surface"""
    from surfscreen.surface import SurfaceBuilder, SiteDetector
    
    surf = SurfaceBuilder.from_file(input_file)
    detector = SiteDetector(surf)
    
    type_list = None if types == "all" else types.split(",")
    sites = detector.detect_all(types=type_list)
    
    console.print(f"\n[bold]📍 Detected Adsorption Sites[/bold]")
    
    # 유형별 카운트
    from collections import Counter
    counts = Counter(s.site_type.value for s in sites)
    
    table = Table()
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right")
    
    for site_type, count in counts.items():
        table.add_row(site_type, str(count))
    table.add_row("[bold]Total[/bold]", f"[bold]{len(sites)}[/bold]")
    
    console.print(table)
    
    if visualize:
        detector.visualize(sites)


# ============ Screen Commands ============

@main.group()
def screen():
    """Screening operations"""
    pass


@screen.command("run")
@click.option("--surface", "-s", required=True, help="Surface file")
@click.option("--molecules", "-m", required=True, help="Molecule file(s) or glob pattern")
@click.option("--engine", "-e", default="mace", help="Calculator engine")
@click.option("--model", default="medium", help="Model size (for MACE)")
@click.option("--device", "-d", default="cuda", help="Device (cuda, cpu)")
@click.option("--rotations", "-r", default="0,45,90,135", help="Rotation angles")
@click.option("--output-dir", "-o", default="screening_results", help="Output directory")
@click.option("--max-configs", default=50, help="Max configurations per molecule")
@click.option("--ncpus", default=None, type=int, help="Number of CPU threads (default: 80%% of total)")
@click.option("--fix-layers", default=2, type=int, help="Number of bottom layers to fix (default: 2)")
def screen_run(surface, molecules, engine, model, device, rotations, output_dir, max_configs, ncpus, fix_layers):
    """Run adsorption screening"""
    import os
    from pathlib import Path
    import glob
    
    # CPU 스레드 제한 설정
    total_cpus = os.cpu_count() or 1
    if ncpus is None:
        ncpus = max(1, int(total_cpus * 0.8))  # 기본: 전체의 80%
    
    # 환경변수로 스레드 제한
    os.environ["OMP_NUM_THREADS"] = str(ncpus)
    os.environ["MKL_NUM_THREADS"] = str(ncpus)
    os.environ["OPENBLAS_NUM_THREADS"] = str(ncpus)
    os.environ["NUMEXPR_NUM_THREADS"] = str(ncpus)
    
    # PyTorch 스레드 제한
    try:
        import torch
        torch.set_num_threads(ncpus)
    except ImportError:
        pass
    
    from surfscreen.surface import SurfaceBuilder
    from surfscreen.molecule import MoleculeBuilder
    from surfscreen.adsorption import AdsorptionSystem
    from surfscreen.calculator import CalculatorFactory
    
    # 파일 로드
    surf = SurfaceBuilder.from_file(surface, fixed_layers=fix_layers)
    
    # 분자 파일 목록
    mol_files = glob.glob(molecules) if '*' in molecules else [molecules]
    
    # 회전 각도
    rots = [float(x) for x in rotations.split(",")]
    
    # Calculator 생성
    console.print(f"\n[bold]🚀 Starting Screening[/bold]")
    console.print(f"  Surface: {surface}")
    console.print(f"  Molecules: {len(mol_files)} files")
    console.print(f"  Engine: {engine}")
    console.print(f"  CPUs: {ncpus}/{total_cpus}")
    
    calc = CalculatorFactory.create(engine, model=model, device=device)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    
    for mol_file in mol_files:
        mol = MoleculeBuilder.from_file(mol_file)
        console.print(f"\n[bold]Processing: {mol.name}[/bold]")
        
        system = AdsorptionSystem(surf, mol)
        configs = system.generate_configurations(
            rotations=rots,
            max_configs=max_configs
        )
        
        console.print(f"  Generated {len(configs)} configurations")
        
        mol_output = output_dir / mol.name
        mol_output.mkdir(parents=True, exist_ok=True)
        
        results = system.optimize_all(
            calc,
            output_dir=str(mol_output),
            progress=True
        )
        
        all_results.extend(results)
        
        # 결과 저장
        system.export_results(results, str(mol_output / "results.csv"))
    
    # 전체 결과 정렬
    all_results.sort(key=lambda x: x.adsorption_energy)
    
    console.print(f"\n[bold]🏆 Top Results[/bold]")
    
    table = Table()
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Config", style="green")
    table.add_column("E_ads (eV)", justify="right")
    
    for i, r in enumerate(all_results[:10], 1):
        table.add_row(str(i), r.config_name, f"{r.adsorption_energy:.4f}")
    
    console.print(table)
    console.print(f"\n[green]✓[/green] Results saved to: {output_dir}")


@screen.command("results")
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


@screen.command("report")
@click.argument("results_dir")
@click.option("--output", "-o", default="report.html", help="Output HTML file")
def screen_report(results_dir, output):
    """Generate interactive HTML report"""
    from pathlib import Path
    from surfscreen.report import ReportGenerator
    
    with console.status("[bold green]Generating report..."):
        gen = ReportGenerator(results_dir)
        out_path = gen.generate(output)
    
    console.print(f"[green]✓[/green] Report generated: {out_path}")
    console.print(f"[dim]Open in browser: file://{Path(out_path).absolute()}[/dim]")


# ============ Config Commands ============

@main.group()
def config():
    """Configuration operations"""
    pass


@config.command("show")
def config_show():
    """Show current configuration"""
    from surfscreen.calculator import CalculatorFactory
    
    console.print("\n[bold]SurfScreen Configuration[/bold]")
    console.print(f"\nAvailable engines: {CalculatorFactory.available()}")
    
    from surfscreen.surface.builder import SurfaceBuilder
    console.print(f"Available elements: {SurfaceBuilder.available_elements()}")


# ============ Adsorb Commands ============

@main.group()
def adsorb():
    """Adsorption configuration operations"""
    pass


@adsorb.command("generate")
@click.option("--surface", "-s", required=True, help="Surface structure file")
@click.option("--molecule", "-m", required=True, help="Molecule structure file")
@click.option("--rotations", "-r", default="0,45,90,135", help="Rotation angles (degrees)")
@click.option("--heights", "-H", default="2.0", help="Adsorption heights (Å)")
@click.option("--max-configs", default=100, help="Maximum configurations")
@click.option("--output", "-o", default="configs", help="Output directory")
def adsorb_generate(surface, molecule, rotations, heights, max_configs, output):
    """Generate adsorption configurations"""
    from ase.io import read
    from surfscreen.surface.builder import Surface
    from surfscreen.adsorption.generator import AdsorptionGenerator
    
    console.print("\n[bold]🎯 Generating adsorption configurations[/bold]\n")
    
    # Load structures
    surf_atoms = read(surface)
    mol_atoms = read(molecule)
    
    surf = Surface(atoms=surf_atoms, name=Path(surface).stem)
    
    # Parse options
    rot_list = [float(r) for r in rotations.split(",")]
    height_list = [float(h) for h in heights.split(",")]
    
    # Generate
    generator = AdsorptionGenerator(surf, mol_atoms)
    configs = generator.generate_configurations(
        rotations=rot_list,
        heights=height_list,
        max_configs=max_configs
    )
    
    # Filter overlapping
    valid_configs = generator.filter_overlapping(min_distance=1.5)
    
    console.print(f"Generated: {len(configs)} configurations")
    console.print(f"Valid (no overlap): {len(valid_configs)} configurations")
    
    # Save
    saved = generator.save_configs(output)
    console.print(f"\n[green]✓[/green] Saved to: {output}/")
    
    # Generate preview
    preview_path = generator.visualize_html(f"{output}/preview.html")
    console.print(f"[green]✓[/green] Preview: {preview_path}")


@adsorb.command("visualize")
@click.argument("configs_dir")
@click.option("--output", "-o", default="configs_preview.html", help="Output HTML file")
def adsorb_visualize(configs_dir, output):
    """Visualize adsorption configurations"""
    from ase.io import read
    from surfscreen.surface.builder import Surface
    from surfscreen.adsorption.generator import AdsorptionGenerator, AdsorptionConfig
    import json
    
    configs_path = Path(configs_dir)
    
    # Load metadata
    meta_path = configs_path / "configs_metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            metadata = json.load(f)
    else:
        metadata = {"configs": []}
    
    console.print(f"\n[bold]🔍 Loading configurations from {configs_dir}[/bold]\n")
    
    # Load structures
    xyz_files = list(configs_path.glob("*.xyz")) + list(configs_path.glob("*.extxyz"))
    console.print(f"Found {len(xyz_files)} configuration files")
    
    # Generate HTML preview
    from surfscreen.visualization import create_energy_distribution_plot
    
    console.print(f"[green]✓[/green] Preview generation not yet implemented for existing configs")


# ============ MD Commands ============

@main.group()
def md():
    """Molecular dynamics operations"""
    pass


@md.command("run")
@click.argument("structure")
@click.option("--ensemble", default="nvt", type=click.Choice(["nvt", "npt", "nve"]))
@click.option("--temperature", "-T", default=300.0, help="Temperature (K)")
@click.option("--pressure", "-P", default=1.0, help="Pressure (bar, NPT only)")
@click.option("--timestep", default=1.0, help="Timestep (fs)")
@click.option("--steps", "-n", default=10000, help="Number of steps")
@click.option("--thermostat", default="langevin", type=click.Choice(["langevin", "berendsen"]))
@click.option("--engine", default="mace", type=click.Choice(["mace", "xtb"]))
@click.option("--model", default="medium", help="MACE model size")
@click.option("--device", default="cuda", type=click.Choice(["cuda", "cpu"]))
@click.option("--force-xtb", is_flag=True, help="Force xTB with PBC (may fail)")
@click.option("--output", "-o", default="md_output", help="Output directory")
def md_run(structure, ensemble, temperature, pressure, timestep, steps, 
           thermostat, engine, model, device, force_xtb, output):
    """Run molecular dynamics simulation"""
    from ase.io import read
    from surfscreen.md import MDEngine, MDConfig
    
    console.print("\n[bold]🚀 Molecular Dynamics Simulation[/bold]\n")
    console.print(f"Structure: {structure}")
    console.print(f"Ensemble: {ensemble.upper()}")
    console.print(f"Temperature: {temperature} K")
    console.print(f"Steps: {steps}")
    console.print(f"Engine: {engine}")
    console.print()
    
    # Load structure
    atoms = read(structure)
    
    # Configure
    config = MDConfig(
        ensemble=ensemble,
        temperature=temperature,
        pressure=pressure,
        timestep=timestep,
        steps=steps,
        thermostat=thermostat,
        engine=engine,
        model=model,
        device=device,
        force_xtb=force_xtb
    )
    
    # Run
    md_engine = MDEngine(atoms, config, output)
    summary = md_engine.run()
    
    console.print("\n[bold green]✓ MD completed![/bold green]")


@md.command("continue")
@click.argument("checkpoint_dir")
@click.option("--steps", "-n", default=10000, help="Additional steps")
def md_continue(checkpoint_dir, steps):
    """Continue MD from checkpoint"""
    from surfscreen.md import MDEngine
    
    console.print(f"\n[bold]🔄 Continuing MD from {checkpoint_dir}[/bold]\n")
    
    md_engine = MDEngine.continue_from_checkpoint(checkpoint_dir, steps)
    summary = md_engine.run()
    
    console.print("\n[bold green]✓ MD continued![/bold green]")


@md.command("status")
@click.argument("output_dir")
def md_status(output_dir):
    """Check MD simulation status"""
    import json
    
    output_path = Path(output_dir)
    
    console.print(f"\n[bold]📊 MD Status: {output_dir}[/bold]\n")
    
    # Check for summary
    summary_path = output_path / "summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
        
        console.print(f"Total steps: {summary.get('total_steps', 'N/A')}")
        console.print(f"Total time: {summary.get('total_time_fs', 'N/A')} fs")
        console.print(f"Avg temperature: {summary.get('avg_temperature_K', 'N/A'):.1f} K")
        console.print(f"Wall time: {summary.get('wall_time_s', 'N/A'):.1f} s")
    else:
        # Check for checkpoint
        checkpoint_path = output_path / "checkpoint_state.json"
        if checkpoint_path.exists():
            with open(checkpoint_path) as f:
                state = json.load(f)
            console.print(f"[yellow]In progress...[/yellow]")
            console.print(f"Current step: {state.get('step', 'N/A')}")
        else:
            console.print("[red]No MD data found[/red]")


@md.command("report")
@click.argument("output_dir")
@click.option("--output", "-o", default=None, help="Output HTML file")
def md_report(output_dir, output):
    """Generate interactive MD report with trajectory playback"""
    from surfscreen.md.md_report import MDReportGenerator
    
    console.print(f"\n[bold]📊 Generating MD Report: {output_dir}[/bold]\n")
    
    out_path = output or f"{Path(output_dir).name}_report.html"
    
    gen = MDReportGenerator(output_dir)
    gen.generate(out_path)
    
    console.print(f"\n[bold green]✓ Report generated: {out_path}[/bold green]")
    console.print("   - Interactive trajectory playback (3Dmol.js)")
    console.print("   - Energy/Temperature plots (Plotly)")
    console.print("   - Download links for OVITO/VMD/ASE")


# ============ Analysis Commands ============

@main.group()
def analysis():
    """Analysis operations"""
    pass


@analysis.command("height")
@click.argument("structure")
@click.option("--n-surface", default=0, help="Number of surface atoms (0 = auto)")
def analysis_height(structure, n_surface):
    """Calculate adsorption height"""
    from ase.io import read
    from surfscreen.analysis import StructuralAnalyzer
    
    atoms = read(structure)
    analyzer = StructuralAnalyzer(atoms, n_surface_atoms=n_surface)
    
    height = analyzer.calculate_adsorption_height()
    min_dist = analyzer.calculate_min_distance()
    tilt = analyzer.calculate_tilt_angle()
    site = analyzer.classify_site_type()
    
    console.print(f"\n[bold]📏 Structural Analysis: {structure}[/bold]\n")
    console.print(f"Adsorption height: {height:.3f} Å")
    console.print(f"Minimum distance: {min_dist:.3f} Å")
    console.print(f"Tilt angle: {tilt:.1f}°")
    console.print(f"Site type: {site}")


@analysis.command("msd")
@click.argument("trajectory")
@click.option("--species", "-s", required=True, help="Atom species (e.g., Li)")
@click.option("--timestep", default=1.0, help="Timestep (fs)")
@click.option("--output", "-o", default="msd_plot.html", help="Output plot")
def analysis_msd(trajectory, species, timestep, output):
    """Calculate Mean Square Displacement"""
    from surfscreen.analysis import DynamicsAnalyzer
    from surfscreen.visualization import create_msd_plot
    
    console.print(f"\n[bold]📈 MSD Analysis: {species}[/bold]\n")
    
    analyzer = DynamicsAnalyzer(trajectory, timestep=timestep)
    msd_result = analyzer.calculate_msd(species)
    
    console.print(f"Frames analyzed: {len(msd_result.time)}")
    console.print(f"Final MSD: {msd_result.msd[-1]:.3f} Å²")
    
    # Calculate diffusion
    diffusion = analyzer.calculate_diffusion(species)
    console.print(f"\nDiffusion coefficient: {diffusion.D:.2e} cm²/s")
    console.print(f"R² = {diffusion.r_squared:.4f}")
    
    # Create plot
    create_msd_plot(
        msd_result.time.tolist(),
        msd_result.msd.tolist(),
        species,
        diffusion.to_dict(),
        output
    )
    console.print(f"\n[green]✓[/green] Plot saved: {output}")


@analysis.command("diffusion")
@click.argument("trajectory")
@click.option("--species", "-s", required=True, help="Atom species")
@click.option("--timestep", default=1.0, help="Timestep (fs)")
@click.option("--fit-start", default=0.2, help="Fit start (fraction)")
@click.option("--fit-end", default=0.8, help="Fit end (fraction)")
def analysis_diffusion(trajectory, species, timestep, fit_start, fit_end):
    """Calculate diffusion coefficient"""
    from surfscreen.analysis import DynamicsAnalyzer
    
    console.print(f"\n[bold]🔬 Diffusion Analysis: {species}[/bold]\n")
    
    analyzer = DynamicsAnalyzer(trajectory, timestep=timestep)
    result = analyzer.calculate_diffusion(species, fit_start=fit_start, fit_end=fit_end)
    
    console.print(f"Diffusion coefficient: {result.D:.4e} cm²/s")
    console.print(f"Error: ±{result.D_error:.4e} cm²/s")
    console.print(f"D_x: {result.D_x:.4e} cm²/s")
    console.print(f"D_y: {result.D_y:.4e} cm²/s")
    console.print(f"D_z: {result.D_z:.4e} cm²/s")
    console.print(f"R² = {result.r_squared:.4f}")


@analysis.command("conductivity")
@click.argument("trajectory")
@click.option("--species", "-s", required=True, help="Ion species")
@click.option("--charge", "-z", required=True, type=int, help="Ion charge")
@click.option("--temperature", "-T", required=True, type=float, help="Temperature (K)")
@click.option("--timestep", default=1.0, help="Timestep (fs)")
def analysis_conductivity(trajectory, species, charge, temperature, timestep):
    """Calculate ionic conductivity"""
    from surfscreen.analysis import DynamicsAnalyzer
    
    console.print(f"\n[bold]⚡ Conductivity Analysis: {species}[/bold]\n")
    
    analyzer = DynamicsAnalyzer(trajectory, timestep=timestep)
    result = analyzer.calculate_conductivity(species, charge, temperature)
    
    console.print(f"Ionic conductivity: {result.sigma:.4e} S/cm")
    console.print(f"Error: ±{result.sigma_error:.4e} S/cm")
    console.print(f"Temperature: {result.temperature} K")
    console.print(f"Number of carriers: {result.n_carriers}")
    console.print(f"Volume: {result.volume:.1f} ų")


@analysis.command("rdf")
@click.argument("trajectory")
@click.option("--pair", "-p", required=True, help="Atom pair (e.g., Li-O)")
@click.option("--rmax", default=10.0, help="Maximum distance (Å)")
@click.option("--timestep", default=1.0, help="Timestep (fs)")
@click.option("--output", "-o", default="rdf_plot.html", help="Output plot")
def analysis_rdf(trajectory, pair, rmax, timestep, output):
    """Calculate Radial Distribution Function"""
    from surfscreen.analysis import DynamicsAnalyzer
    from surfscreen.visualization import create_rdf_plot
    
    pair_tuple = tuple(pair.split("-"))
    
    console.print(f"\n[bold]🔵 RDF Analysis: {pair}[/bold]\n")
    
    analyzer = DynamicsAnalyzer(trajectory, timestep=timestep)
    result = analyzer.calculate_rdf(pair_tuple, r_max=rmax)
    
    console.print(f"First peak: r = {result.first_peak_r:.3f} Å, g(r) = {result.first_peak_g:.2f}")
    console.print(f"Coordination number: {result.coordination_number:.2f}")
    
    # Create plot
    create_rdf_plot(
        result.r.tolist(),
        result.g_r.tolist(),
        pair_tuple,
        output
    )
    console.print(f"\n[green]✓[/green] Plot saved: {output}")


@analysis.command("boltzmann")
@click.argument("results_dir")
@click.option("--temperature", "-T", default=300.0, help="Temperature (K)")
@click.option("--output", "-o", default="boltzmann_plot.html", help="Output plot")
def analysis_boltzmann(results_dir, temperature, output):
    """Calculate Boltzmann distribution"""
    from surfscreen.analysis import ThermodynamicAnalyzer
    from surfscreen.visualization import create_boltzmann_plot
    
    console.print(f"\n[bold]🎲 Boltzmann Analysis (T = {temperature} K)[/bold]\n")
    
    analyzer = ThermodynamicAnalyzer()
    analyzer.load_from_directory(results_dir)
    
    result = analyzer.calculate_boltzmann(temperature)
    
    # Top 5
    sorted_idx = sorted(range(len(result.probabilities)), 
                        key=lambda i: result.probabilities[i], reverse=True)
    
    console.print("Top 5 configurations:")
    for rank, idx in enumerate(sorted_idx[:5], 1):
        console.print(f"  {rank}. {result.names[idx]}: {result.probabilities[idx]*100:.1f}%")
    
    # Create plot
    create_boltzmann_plot(
        result.names,
        result.probabilities,
        result.energies,
        temperature,
        output
    )
    console.print(f"\n[green]✓[/green] Plot saved: {output}")


# ============ Plot Commands ============

@main.group()
def plot():
    """Visualization and plotting"""
    pass


@plot.command("energy-dist")
@click.argument("results_dir")
@click.option("--output", "-o", default="energy_distribution.html", help="Output file")
def plot_energy_dist(results_dir, output):
    """Plot energy distribution histogram"""
    import json
    from surfscreen.visualization import create_energy_distribution_plot
    
    # Load results
    results_path = Path(results_dir) / "results.json"
    if results_path.exists():
        with open(results_path) as f:
            data = json.load(f)
        
        energies = [r.get("adsorption_energy", r.get("energy", 0)) 
                    for r in data.get("results", [])]
        names = [r.get("name", "") for r in data.get("results", [])]
    else:
        console.print("[red]results.json not found[/red]")
        return
    
    create_energy_distribution_plot(energies, names, output)
    console.print(f"[green]✓[/green] Plot saved: {output}")


@plot.command("correlation")
@click.argument("results_dir")
@click.option("--x", "x_prop", default="height", help="X-axis property")
@click.option("--y", "y_prop", default="e_ads", help="Y-axis property")
@click.option("--output", "-o", default="correlation.html", help="Output file")
def plot_correlation(results_dir, x_prop, y_prop, output):
    """Plot correlation between properties"""
    console.print(f"[yellow]Correlation plot: {x_prop} vs {y_prop}[/yellow]")
    console.print("[dim]Requires structural analysis data[/dim]")


# ============ Export Commands ============

@main.group()
def export():
    """Export results to various formats"""
    pass


@export.command("csv")
@click.argument("results_dir")
@click.option("--output", "-o", default="results.csv", help="Output file")
def export_csv(results_dir, output):
    """Export results to CSV"""
    from surfscreen.export import ExportManager
    
    manager = ExportManager(results_dir)
    manager.to_csv(output)
    console.print(f"[green]✓[/green] Exported to: {output}")


@export.command("json")
@click.argument("results_dir")
@click.option("--output", "-o", default="results_export.json", help="Output file")
def export_json(results_dir, output):
    """Export results to JSON"""
    from surfscreen.export import ExportManager
    
    manager = ExportManager(results_dir)
    manager.to_json(output)
    console.print(f"[green]✓[/green] Exported to: {output}")


@export.command("excel")
@click.argument("results_dir")
@click.option("--output", "-o", default="results.xlsx", help="Output file")
def export_excel(results_dir, output):
    """Export results to Excel (requires pandas, openpyxl)"""
    from surfscreen.export import ExportManager
    
    manager = ExportManager(results_dir)
    manager.to_excel(output)
    console.print(f"[green]✓[/green] Exported to: {output}")


@export.command("zip")
@click.argument("results_dir")
@click.option("--output", "-o", default="results.zip", help="Output file")
@click.option("--structures/--no-structures", default=True, help="Include structure files")
@click.option("--trajectories/--no-trajectories", default=True, help="Include trajectory files")
def export_zip(results_dir, output, structures, trajectories):
    """Export all results as ZIP archive"""
    from surfscreen.export import ExportManager, ExportConfig
    
    config = ExportConfig(
        include_structures=structures,
        include_trajectories=trajectories
    )
    manager = ExportManager(results_dir, config)
    manager.to_zip(output)
    console.print(f"[green]✓[/green] Exported to: {output}")


# ============ Template Commands ============

@main.group()
def template():
    """Workflow template management"""
    pass


@template.command("list")
def template_list():
    """List available templates"""
    from surfscreen.templates import TemplateEngine
    
    engine = TemplateEngine()
    templates = engine.list_templates()
    
    if not templates:
        console.print("[yellow]No templates found. Run 'surfscreen template install-defaults' first.[/yellow]")
        return
        
    table = Table(title="Available Templates")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Version")
    
    for t in templates:
        table.add_row(t["name"], t["description"], t["version"])
        
    console.print(table)


@template.command("install-defaults")
def template_install_defaults():
    """Install default workflow templates"""
    from surfscreen.templates import install_default_templates
    
    console.print("[bold]Installing default templates...[/bold]")
    install_default_templates()
    console.print("[green]✓[/green] Default templates installed")


@template.command("run")
@click.argument("template_name")
@click.option("--var", "-v", multiple=True, help="Variable override (key=value)")
@click.option("--dry-run", is_flag=True, help="Show commands without executing")
@click.option("--output-dir", "-o", default=".", help="Working directory")
def template_run(template_name, var, dry_run, output_dir):
    """Run a workflow template"""
    from surfscreen.templates import TemplateEngine
    
    variables = {}
    for v in var:
        if "=" in v:
            key, value = v.split("=", 1)
            variables[key] = value
            
    engine = TemplateEngine()
    result = engine.run_template(template_name, variables, dry_run=dry_run, output_dir=output_dir)
    
    if result["success"]:
        console.print("[green]✓[/green] Template completed successfully")
    else:
        console.print("[red]✗[/red] Template failed")


# ============ Coverage Analysis ============

@analysis.command("coverage")
@click.argument("structure")
@click.option("--n-surface", default=0, help="Number of surface atoms (0=auto)")
@click.option("--mol-area", default=10.0, help="Molecular footprint area (Å²)")
def analysis_coverage(structure, n_surface, mol_area):
    """Calculate surface coverage"""
    from ase.io import read
    from surfscreen.analysis import CoverageAnalyzer
    
    atoms = read(structure)
    analyzer = CoverageAnalyzer(atoms, n_surface)
    result = analyzer.calculate_coverage(mol_area)
    
    console.print(f"\n[bold]Coverage Analysis: {structure}[/bold]")
    console.print(f"Surface area: {result.surface_area:.2f} Å²")
    console.print(f"Adsorbates: {result.n_adsorbates}")
    console.print(f"Coverage (abs): {result.coverage_abs:.4f} mol/Å²")
    console.print(f"Coverage (ML): {result.coverage_ml:.2%}")


# ============ Phonon Analysis ============

@analysis.command("phonon")
@click.argument("structure")
@click.option("--engine", default="mace", type=click.Choice(["mace", "xtb"]))
@click.option("--delta", default=0.01, help="Displacement (Å)")
def analysis_phonon(structure, engine, delta):
    """Calculate vibrational frequencies"""
    from ase.io import read
    from surfscreen.analysis import PhononAnalyzer
    
    console.print(f"\n[bold]Phonon Analysis: {structure}[/bold]")
    
    atoms = read(structure)
    
    # Calculator setup
    if engine == "mace":
        from mace.calculators import mace_mp
        calc = mace_mp(model="medium", device="cpu", default_dtype="float64")
    else:
        from xtb.ase.calculator import XTB
        calc = XTB(method="GFN2-xTB")
        
    analyzer = PhononAnalyzer(atoms, calc, delta)
    result = analyzer.calculate_vibrations()
    
    console.print(f"Frequencies: {len(result.frequencies_cm1)} modes")
    console.print(f"ZPE: {result.zpe:.4f} eV")
    console.print(f"Imaginary modes: {result.n_imaginary}")
    
    if len(result.frequencies_cm1) > 0:
        console.print(f"Min freq: {result.frequencies_cm1.min():.1f} cm⁻¹")
        console.print(f"Max freq: {result.frequencies_cm1.max():.1f} cm⁻¹")


@analysis.command("gibbs")
@click.argument("structure")
@click.option("--temperature", "-T", default=298.15, help="Temperature (K)")
@click.option("--engine", default="mace", type=click.Choice(["mace", "xtb"]))
def analysis_gibbs(structure, temperature, engine):
    """Calculate Gibbs free energy"""
    from ase.io import read
    from surfscreen.analysis import PhononAnalyzer
    
    console.print(f"\n[bold]Gibbs Free Energy: {structure}[/bold]")
    
    atoms = read(structure)
    
    if engine == "mace":
        from mace.calculators import mace_mp
        calc = mace_mp(model="medium", device="cpu", default_dtype="float64")
    else:
        from xtb.ase.calculator import XTB
        calc = XTB(method="GFN2-xTB")
        
    analyzer = PhononAnalyzer(atoms, calc)
    result = analyzer.calculate_thermodynamics(temperature)
    
    console.print(f"Temperature: {temperature} K")
    console.print(f"E_pot: {result.E_pot:.4f} eV")
    console.print(f"ZPE: {result.ZPE:.4f} eV")
    console.print(f"H: {result.H:.4f} eV")
    console.print(f"G: {result.G:.4f} eV")


# ============ Materials Project ============

@surface.command("from-mp")
@click.argument("material_id")
@click.option("--miller", default="111", help="Miller indices")
@click.option("--layers", default=4, help="Number of layers")
@click.option("--vacuum", default=15.0, help="Vacuum (Å)")
@click.option("--output", "-o", required=True, help="Output file")
def surface_from_mp(material_id, miller, layers, vacuum, output):
    """Create surface from Materials Project structure"""
    from surfscreen.integrations import MPIntegration
    from ase.io import write
    
    console.print(f"\n[bold]Creating surface from MP: {material_id}[/bold]")
    
    miller_tuple = tuple(int(x) for x in miller)
    
    try:
        mp = MPIntegration()
        slab = mp.create_surface(material_id, miller_tuple, layers, vacuum)
        write(output, slab, format="extxyz")
        console.print(f"[green]✓[/green] Surface saved: {output}")
        console.print(f"  Atoms: {len(slab)}")
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@surface.command("search-mp")
@click.argument("formula")
@click.option("--limit", default=10, help="Max results")
def surface_search_mp(formula, limit):
    """Search materials in Materials Project"""
    from surfscreen.integrations import MPIntegration
    
    console.print(f"\n[bold]Searching MP: {formula}[/bold]")
    
    try:
        mp = MPIntegration()
        results = mp.search_materials(formula=formula, max_results=limit)
        
        table = Table(title=f"Materials Project: {formula}")
        table.add_column("ID")
        table.add_column("Formula")
        table.add_column("Spacegroup")
        table.add_column("E_hull (eV)")
        
        for r in results:
            table.add_row(
                r["material_id"],
                r["formula"],
                str(r["spacegroup"] or ""),
                f"{r['energy_above_hull']:.3f}" if r['energy_above_hull'] else ""
            )
            
        console.print(table)
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ============ Checkpoint Commands ============

@main.group()
def checkpoint():
    """Checkpoint and resume management"""
    pass


@checkpoint.command("status")
@click.argument("checkpoint_dir")
def checkpoint_status(checkpoint_dir):
    """Show checkpoint status"""
    from surfscreen.checkpoint import CheckpointManager
    
    try:
        manager = CheckpointManager(checkpoint_dir)
        manager.print_status()
    except FileNotFoundError:
        console.print(f"[red]No checkpoint found in: {checkpoint_dir}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@checkpoint.command("reset-failed")
@click.argument("checkpoint_dir")
@click.option("--confirm", is_flag=True, help="Skip confirmation")
def checkpoint_reset_failed(checkpoint_dir, confirm):
    """Reset failed tasks to pending"""
    from surfscreen.checkpoint import CheckpointManager
    
    manager = CheckpointManager(checkpoint_dir)
    failed = manager.get_failed_tasks()
    
    if not failed:
        console.print("[yellow]No failed tasks to reset[/yellow]")
        return
        
    console.print(f"Failed tasks: {len(failed)}")
    for task_id in failed[:10]:
        error = manager.state.tasks[task_id].get("error", "")
        console.print(f"  - {task_id}: {error[:50]}...")
        
    if len(failed) > 10:
        console.print(f"  ... and {len(failed) - 10} more")
        
    if not confirm:
        if not click.confirm("Reset all failed tasks to pending?"):
            return
            
    manager.reset_failed_tasks()
    console.print(f"[green]✓[/green] Reset {len(failed)} tasks to pending")


@checkpoint.command("list-pending")
@click.argument("checkpoint_dir")
@click.option("--limit", default=20, help="Max items to show")
def checkpoint_list_pending(checkpoint_dir, limit):
    """List pending tasks"""
    from surfscreen.checkpoint import CheckpointManager
    
    manager = CheckpointManager(checkpoint_dir)
    pending = manager.get_pending_tasks()
    
    console.print(f"\n[bold]Pending Tasks: {len(pending)}[/bold]")
    
    for task_id in pending[:limit]:
        console.print(f"  ⏳ {task_id}")
        
    if len(pending) > limit:
        console.print(f"  ... and {len(pending) - limit} more")


@checkpoint.command("clean")
@click.argument("checkpoint_dir")
@click.option("--force", is_flag=True, help="Skip confirmation")
def checkpoint_clean(checkpoint_dir, force):
    """Delete checkpoint and start fresh"""
    from pathlib import Path
    
    cp_path = Path(checkpoint_dir) / "checkpoint.json"
    
    if not cp_path.exists():
        console.print(f"[yellow]No checkpoint found[/yellow]")
        return
        
    if not force:
        if not click.confirm(f"Delete checkpoint at {cp_path}?"):
            return
            
    cp_path.unlink()
    console.print(f"[green]✓[/green] Checkpoint deleted")


# ============ Multi-molecule Screening ============

@screen.command("multi")
@click.option("-s", "--surface", "surface_file", required=True, help="Surface structure")
@click.option("-m", "--molecules", multiple=True, required=True, help="Molecule files (can repeat)")
@click.option("-o", "--output", required=True, help="Output directory")
@click.option("--engine", default="mace", type=click.Choice(["mace", "xtb"]))
@click.option("--parallel", default=1, help="Parallel workers per molecule")
def screen_multi(surface_file, molecules, output, engine, parallel):
    """Screen multiple molecules on a surface"""
    from pathlib import Path
    import subprocess
    
    console.print(f"\n[bold]Multi-molecule Screening[/bold]")
    console.print(f"Surface: {surface_file}")
    console.print(f"Molecules: {len(molecules)}")
    console.print(f"Engine: {engine}")
    
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    for i, mol_file in enumerate(molecules, 1):
        mol_name = Path(mol_file).stem
        mol_output = output_dir / mol_name
        
        console.print(f"\n[{i}/{len(molecules)}] Processing: {mol_name}")
        
        cmd = [
            "surfscreen", "screen", "run",
            "-s", surface_file,
            "-m", mol_file,
            "-o", str(mol_output),
            "--engine", engine,
            "-n", str(parallel)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if result.returncode == 0:
                console.print(f"  [green]✓[/green] {mol_name} completed")
                results.append({"molecule": mol_name, "status": "success"})
            else:
                console.print(f"  [red]✗[/red] {mol_name} failed")
                results.append({"molecule": mol_name, "status": "failed", "error": result.stderr[:200]})
        except subprocess.TimeoutExpired:
            console.print(f"  [yellow]⏰[/yellow] {mol_name} timeout")
            results.append({"molecule": mol_name, "status": "timeout"})
        except Exception as e:
            console.print(f"  [red]✗[/red] {mol_name} error: {e}")
            results.append({"molecule": mol_name, "status": "error", "error": str(e)})
    
    # Summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Summary[/bold]")
    success = sum(1 for r in results if r["status"] == "success")
    console.print(f"Success: {success}/{len(molecules)}")
    
    # Save results
    import json
    with open(output_dir / "multi_results.json", "w") as f:
        json.dump(results, f, indent=2)
    console.print(f"\n[green]✓[/green] Results saved: {output_dir}/multi_results.json")


if __name__ == "__main__":
    main()


