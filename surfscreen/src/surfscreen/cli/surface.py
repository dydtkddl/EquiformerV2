"""
SurfScreen CLI - Surface Commands

표면 생성/관리 관련 명령어
"""

import click
from pathlib import Path

from surfscreen.cli.utils import console, Table


# ============ Surface Command Group ============

@click.group(name="surface")
def surface_group():
    """Surface operations"""
    pass


@surface_group.command("create")
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


@surface_group.command("sites")
@click.argument("input_file")
@click.option("--types", "-t", default="all", help="Site types (top, bridge, hollow, all)")
@click.option("--visualize", "-v", is_flag=True, help="Show visualization")
def surface_sites(input_file, types, visualize):
    """Detect adsorption sites on surface"""
    from surfscreen.surface import SurfaceBuilder
    from surfscreen.surface.sites import SiteDetector
    from collections import Counter
    
    surf = SurfaceBuilder.from_file(input_file)
    detector = SiteDetector(surf)
    
    type_list = None if types == "all" else types.split(",")
    sites = detector.detect_all(types=type_list)
    
    console.print(f"\n[bold]📍 Detected Adsorption Sites[/bold]")
    
    # 유형별 카운트
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


@surface_group.command("from-mp")
@click.argument("material_id")
@click.option("--miller", "-m", default="111", help="Miller index")
@click.option("--layers", "-l", default=4, help="Number of layers")
@click.option("--vacuum", "-v", default=15.0, help="Vacuum thickness (Å)")
@click.option("--output", "-o", default=None, help="Output file")
def surface_from_mp(material_id, miller, layers, vacuum, output):
    """Create surface from Materials Project structure"""
    from surfscreen.surface import SurfaceBuilder
    from surfscreen.integrations.mp_client import MPClient
    
    miller_idx = tuple(int(x) for x in miller)
    
    with console.status(f"[bold green]Fetching {material_id} from Materials Project..."):
        client = MPClient()
        structure = client.get_structure(material_id)
        
        surf = SurfaceBuilder.from_pymatgen_structure(
            structure,
            miller_index=miller_idx,
            layers=layers,
            vacuum=vacuum
        )
    
    out_path = output or f"{material_id}_{miller}.extxyz"
    surf.save(out_path)
    
    console.print(f"[green]✓[/green] Surface: {surf.name}")
    console.print(f"[green]✓[/green] Atoms: {surf.n_atoms}")
    console.print(f"[green]✓[/green] Saved: {out_path}")


@surface_group.command("search-mp")
@click.argument("formula")
@click.option("--limit", "-l", default=10, help="Max results")
def surface_search_mp(formula, limit):
    """Search materials in Materials Project"""
    from surfscreen.integrations.mp_client import MPClient
    
    with console.status(f"[bold green]Searching for {formula}..."):
        client = MPClient()
        results = client.search(formula, limit=limit)
    
    if not results:
        console.print(f"[yellow]No results found for: {formula}[/yellow]")
        return
    
    console.print(f"\n[bold]📦 Materials Project Results: {formula}[/bold]\n")
    
    table = Table()
    table.add_column("ID", style="cyan")
    table.add_column("Formula")
    table.add_column("Space Group")
    table.add_column("E above hull (eV/atom)", justify="right")
    
    for mat in results:
        table.add_row(
            mat.material_id,
            mat.formula_pretty,
            mat.symmetry.symbol if mat.symmetry else "N/A",
            f"{mat.energy_above_hull:.4f}" if mat.energy_above_hull else "N/A"
        )
    
    console.print(table)


__all__ = ["surface_group"]
