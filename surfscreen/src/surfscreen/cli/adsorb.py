"""
SurfScreen CLI - Adsorption & Config Commands

흡착 구성 생성/시각화 및 설정 관련 명령어
"""

import click
from pathlib import Path

from surfscreen.cli.utils import console


# ============ Config Command Group ============

@click.group(name="config")
def config_group():
    """Configuration operations"""
    pass


@config_group.command("show")
def config_show():
    """Show current configuration"""
    from surfscreen.calculator import CalculatorFactory
    from surfscreen.surface.builder import SurfaceBuilder
    
    console.print("\n[bold]SurfScreen Configuration[/bold]")
    console.print(f"\nAvailable engines: {CalculatorFactory.available()}")
    console.print(f"Available elements: {SurfaceBuilder.available_elements()}")


# ============ Adsorb Command Group ============

@click.group(name="adsorb")
def adsorb_group():
    """Adsorption configuration operations"""
    pass


@adsorb_group.command("generate")
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


@adsorb_group.command("visualize")
@click.argument("configs_dir")
@click.option("--output", "-o", default="configs_preview.html", help="Output HTML file")
def adsorb_visualize(configs_dir, output):
    """Visualize adsorption configurations"""
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
    console.print(f"[green]✓[/green] Preview generation not yet implemented for existing configs")


__all__ = ["config_group", "adsorb_group"]
