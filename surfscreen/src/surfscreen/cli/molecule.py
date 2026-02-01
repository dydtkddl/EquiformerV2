"""
SurfScreen CLI - Molecule Commands

분자 생성/관리 관련 명령어
"""

import click
from pathlib import Path

from surfscreen.cli.utils import console


# ============ Molecule Command Group ============

@click.group(name="molecule")
def molecule_group():
    """Molecule operations"""
    pass


@molecule_group.command("from-smiles")
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


@molecule_group.command("from-pubchem")
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


@molecule_group.command("conformers")
@click.argument("input_file")
@click.option("--engine", "-e", type=click.Choice(["rdkit", "crest", "xtb"]), default="rdkit")
@click.option("--n-conformers", "-n", default=10)
@click.option("--energy-window", default=10.0, help="Energy window (kcal/mol)")
@click.option("--output-dir", "-o", default="conformers")
def mol_conformers(input_file, engine, n_conformers, energy_window, output_dir):
    """Generate conformers for a molecule"""
    from surfscreen.molecule import MoleculeBuilder, ConformerGenerator
    
    mol = MoleculeBuilder.from_file(input_file)
    
    with console.status(f"[bold green]Generating conformers with {engine}..."):
        gen = ConformerGenerator(engine=engine, energy_window=energy_window)
        conformers = gen.generate(mol, n_conformers=n_conformers)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[green]✓[/green] Generated {len(conformers)} conformers")
    for conf in conformers:
        out_file = output_path / f"{conf.name}.xyz"
        conf.save(str(out_file))
    console.print(f"[green]✓[/green] Saved to: {output_path}")


@molecule_group.command("analyze")
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


__all__ = ["molecule_group"]
