"""
SurfScreen CLI - Analysis Commands

분석 관련 명령어 (MSD, RDF, 확산, 전도도, Boltzmann 등)
"""

import click
from pathlib import Path

from surfscreen.cli.utils import console, Table


# ============ Analysis Command Group ============

@click.group(name="analysis")
def analysis_group():
    """Analysis operations"""
    pass


@analysis_group.command("height")
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


@analysis_group.command("msd")
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


@analysis_group.command("diffusion")
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


@analysis_group.command("conductivity")
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


@analysis_group.command("rdf")
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
    create_rdf_plot(result.r.tolist(), result.g_r.tolist(), pair_tuple, output)
    console.print(f"\n[green]✓[/green] Plot saved: {output}")


@analysis_group.command("boltzmann")
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
    create_boltzmann_plot(result.names, result.probabilities, result.energies, temperature, output)
    console.print(f"\n[green]✓[/green] Plot saved: {output}")


@analysis_group.command("coverage")
@click.argument("structure")
@click.option("--n-surface", default=0, help="Number of surface atoms")
@click.option("--mol-area", default=50.0, help="Molecular footprint area (Ų)")
def analysis_coverage(structure, n_surface, mol_area):
    """Calculate surface coverage"""
    from ase.io import read
    from surfscreen.analysis import StructuralAnalyzer
    
    atoms = read(structure)
    analyzer = StructuralAnalyzer(atoms, n_surface_atoms=n_surface)
    
    coverage = analyzer.calculate_coverage(mol_area)
    
    console.print(f"\n[bold]📊 Coverage Analysis[/bold]\n")
    console.print(f"Surface area: {analyzer.surface_area:.1f} Ų")
    console.print(f"Molecular footprint: {mol_area:.1f} Ų")
    console.print(f"Coverage: {coverage*100:.1f}%")


@analysis_group.command("phonon")
@click.argument("structure")
@click.option("--engine", "-e", default="mace", help="Calculator engine")
@click.option("--delta", default=0.01, help="Displacement for finite differences (Å)")
def analysis_phonon(structure, engine, delta):
    """Calculate vibrational frequencies"""
    from ase.io import read
    from ase.vibrations import Vibrations
    from surfscreen.calculator import CalculatorFactory
    
    console.print(f"\n[bold]🎵 Phonon Analysis: {structure}[/bold]\n")
    
    atoms = read(structure)
    calc = CalculatorFactory.create(engine)
    atoms.calc = calc.calc
    
    with console.status("[bold green]Calculating frequencies..."):
        vib = Vibrations(atoms, delta=delta)
        vib.run()
        freqs = vib.get_frequencies()
        vib.clean()
    
    # Filter real frequencies
    real_freqs = [f.real for f in freqs if f.real > 0]
    console.print(f"Total modes: {len(freqs)}")
    console.print(f"Real modes: {len(real_freqs)}")
    console.print(f"Frequency range: {min(real_freqs):.1f} - {max(real_freqs):.1f} cm⁻¹")
    
    # ZPE
    zpe = sum(real_freqs) * 0.5 * 1.23984e-4  # cm⁻¹ → eV
    console.print(f"Zero-point energy: {zpe:.6f} eV")


@analysis_group.command("gibbs")
@click.argument("structure")
@click.option("--temperature", "-T", default=300.0, help="Temperature (K)")
@click.option("--engine", "-e", default="mace", help="Calculator engine")
def analysis_gibbs(structure, temperature, engine):
    """Calculate Gibbs free energy"""
    from ase.io import read
    from surfscreen.analysis import ThermodynamicAnalyzer
    from surfscreen.calculator import CalculatorFactory
    
    console.print(f"\n[bold]🔥 Gibbs Free Energy: {structure}[/bold]\n")
    
    atoms = read(structure)
    calc = CalculatorFactory.create(engine)
    atoms.calc = calc.calc
    
    analyzer = ThermodynamicAnalyzer()
    result = analyzer.calculate_free_energy(atoms, Path(structure).stem, temperature)
    
    console.print(f"Electronic energy: {result.E_electronic:.6f} eV")
    console.print(f"Zero-point energy: {result.E_zpe:.6f} eV")
    console.print(f"Thermal energy: {result.E_thermal:.6f} eV")
    console.print(f"Entropy (−TΔS): {-temperature * result.S_vib:.6f} eV")
    console.print(f"[bold]Gibbs free energy: {result.G:.6f} eV[/bold]")


__all__ = ["analysis_group"]
