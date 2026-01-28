"""
SurfScreen CLI

Click 기반 명령행 인터페이스
"""

import os

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


@click.group()
@click.version_option(version="0.1.0", prog_name="surfscreen")
def main():
    """SurfScreen: Enterprise Surface Adsorption Screening Platform"""
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
@click.option("--by", type=click.Choice(["cid", "name", "formula"]), default="cid")
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
    
    out_path = output or f"{surf.name}.xyz"
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
def screen_run(surface, molecules, engine, model, device, rotations, output_dir, max_configs, ncpus):
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
    surf = SurfaceBuilder.from_file(surface)
    
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


if __name__ == "__main__":
    main()
