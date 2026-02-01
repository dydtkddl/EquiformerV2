"""
SurfScreen CLI - Export Commands

결과 내보내기 관련 명령어 (CSV, JSON, Excel, ZIP)
"""

import click
from pathlib import Path

from surfscreen.cli.utils import console


# ============ Export Command Group ============

@click.group(name="export")
def export_group():
    """Export results to various formats"""
    pass


@export_group.command("csv")
@click.argument("results_dir")
@click.option("--output", "-o", default="results.csv", help="Output file")
def export_csv(results_dir, output):
    """Export results to CSV"""
    from surfscreen.export import ExportManager
    
    manager = ExportManager(results_dir)
    manager.to_csv(output)
    console.print(f"[green]✓[/green] Exported to: {output}")


@export_group.command("json")
@click.argument("results_dir")
@click.option("--output", "-o", default="results_export.json", help="Output file")
def export_json(results_dir, output):
    """Export results to JSON"""
    from surfscreen.export import ExportManager
    
    manager = ExportManager(results_dir)
    manager.to_json(output)
    console.print(f"[green]✓[/green] Exported to: {output}")


@export_group.command("excel")
@click.argument("results_dir")
@click.option("--output", "-o", default="results.xlsx", help="Output file")
def export_excel(results_dir, output):
    """Export results to Excel (requires pandas, openpyxl)"""
    from surfscreen.export import ExportManager
    
    manager = ExportManager(results_dir)
    manager.to_excel(output)
    console.print(f"[green]✓[/green] Exported to: {output}")


@export_group.command("zip")
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


# ============ Plot Command Group ============

@click.group(name="plot")
def plot_group():
    """Visualization and plotting"""
    pass


@plot_group.command("energy-dist")
@click.argument("results_dir")
@click.option("--output", "-o", default="energy_distribution.html", help="Output file")
def plot_energy_dist(results_dir, output):
    """Plot energy distribution histogram"""
    import json
    from surfscreen.visualization import create_energy_distribution_plot
    
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


@plot_group.command("correlation")
@click.argument("results_dir")
@click.option("--x", "x_prop", default="height", help="X-axis property")
@click.option("--y", "y_prop", default="e_ads", help="Y-axis property")
@click.option("--output", "-o", default="correlation.html", help="Output file")
def plot_correlation(results_dir, x_prop, y_prop, output):
    """Plot correlation between properties"""
    console.print(f"[yellow]Correlation plot: {x_prop} vs {y_prop}[/yellow]")
    console.print("[dim]Requires structural analysis data[/dim]")


__all__ = ["export_group", "plot_group"]
