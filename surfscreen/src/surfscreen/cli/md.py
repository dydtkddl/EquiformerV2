"""
SurfScreen CLI - MD Commands

분자 동역학 시뮬레이션 관련 명령어
"""

import click
from pathlib import Path

from surfscreen.cli.utils import console


# ============ MD Command Group ============

@click.group(name="md")
def md_group():
    """Molecular dynamics operations"""
    pass


@md_group.command("run")
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


@md_group.command("continue")
@click.argument("checkpoint_dir")
@click.option("--steps", "-n", default=10000, help="Additional steps")
def md_continue(checkpoint_dir, steps):
    """Continue MD from checkpoint"""
    from surfscreen.md import MDEngine
    
    console.print(f"\n[bold]🔄 Continuing MD from {checkpoint_dir}[/bold]\n")
    
    md_engine = MDEngine.continue_from_checkpoint(checkpoint_dir, steps)
    summary = md_engine.run()
    
    console.print("\n[bold green]✓ MD continued![/bold green]")


@md_group.command("status")
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


@md_group.command("report")
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


__all__ = ["md_group"]
