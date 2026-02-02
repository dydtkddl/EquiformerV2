"""
Reference data for scientific validation.

Contains experimental and DFT reference values for:
- Adsorption energies on metal surfaces
- Molecular geometries
- Metal lattice parameters
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class AdsorptionReference:
    """Reference adsorption energy data."""
    molecule: str
    surface: str
    site: str
    energy_eV: float
    energy_error: float  # uncertainty
    method: str  # 'DFT-PBE', 'DFT-BEEF-vdW', 'experiment'
    reference: str  # citation


@dataclass
class MoleculeGeometry:
    """Reference molecular geometry."""
    name: str
    atoms: List[str]
    bond_lengths: Dict[str, float]  # e.g., {'C-O': 1.128}
    bond_angles: Dict[str, float]  # e.g., {'H-O-H': 104.5}
    reference: str


@dataclass
class MetalLattice:
    """Reference metal lattice parameters."""
    metal: str
    structure: str  # 'fcc', 'bcc', 'hcp'
    lattice_constant: float  # Å
    nearest_neighbor: float  # Å
    reference: str


# ============================================================================
# Adsorption Energy References
# ============================================================================

ADSORPTION_REFERENCES: List[AdsorptionReference] = [
    # CO on metals
    AdsorptionReference(
        molecule='CO', surface='Cu(111)', site='top',
        energy_eV=-0.57, energy_error=0.1,
        method='experiment',
        reference='Hammer et al., Surf. Sci. 343, 211 (1995)'
    ),
    AdsorptionReference(
        molecule='CO', surface='Cu(111)', site='top',
        energy_eV=-0.67, energy_error=0.05,
        method='DFT-BEEF-vdW',
        reference='Wellendorff et al., Phys. Rev. B 85, 235149 (2012)'
    ),
    AdsorptionReference(
        molecule='CO', surface='Pt(111)', site='top',
        energy_eV=-1.55, energy_error=0.1,
        method='experiment',
        reference='Yeo et al., J. Chem. Phys. 106, 392 (1997)'
    ),
    AdsorptionReference(
        molecule='CO', surface='Ni(111)', site='hollow',
        energy_eV=-1.35, energy_error=0.1,
        method='experiment',
        reference='Stuckless et al., J. Chem. Phys. 99, 2202 (1993)'
    ),
    
    # H2O on metals
    AdsorptionReference(
        molecule='H2O', surface='Cu(111)', site='top',
        energy_eV=-0.35, energy_error=0.1,
        method='DFT-PBE-D3',
        reference='Michaelides et al., Phys. Rev. Lett. 90, 216102 (2003)'
    ),
    AdsorptionReference(
        molecule='H2O', surface='Pt(111)', site='top',
        energy_eV=-0.44, energy_error=0.1,
        method='DFT-optB88-vdW',
        reference='Carrasco et al., Nat. Mater. 11, 667 (2012)'
    ),
    
    # CH4 on metals (physisorption)
    AdsorptionReference(
        molecule='CH4', surface='Cu(111)', site='hollow',
        energy_eV=-0.12, energy_error=0.03,
        method='DFT-vdW-DF2',
        reference='Lee et al., Phys. Rev. B 82, 081101 (2010)'
    ),
    
    # O2 on metals
    AdsorptionReference(
        molecule='O2', surface='Pt(111)', site='bridge',
        energy_eV=-0.5, energy_error=0.15,
        method='experiment',
        reference='Campbell et al., Surf. Sci. 157, 43 (1985)'
    ),
    
    # NH3 on metals
    AdsorptionReference(
        molecule='NH3', surface='Cu(111)', site='top',
        energy_eV=-0.45, energy_error=0.1,
        method='DFT-PBE-D3',
        reference='Honkala et al., J. Chem. Phys. 115, 2297 (2001)'
    ),
]


# ============================================================================
# Molecular Geometry References
# ============================================================================

MOLECULE_GEOMETRIES: Dict[str, MoleculeGeometry] = {
    'CO': MoleculeGeometry(
        name='Carbon Monoxide',
        atoms=['C', 'O'],
        bond_lengths={'C-O': 1.128},
        bond_angles={},
        reference='NIST Computational Chemistry Comparison (CCCBDB)'
    ),
    'H2O': MoleculeGeometry(
        name='Water',
        atoms=['O', 'H', 'H'],
        bond_lengths={'O-H': 0.958},
        bond_angles={'H-O-H': 104.5},
        reference='NIST CCCBDB'
    ),
    'CH4': MoleculeGeometry(
        name='Methane',
        atoms=['C', 'H', 'H', 'H', 'H'],
        bond_lengths={'C-H': 1.087},
        bond_angles={'H-C-H': 109.5},
        reference='NIST CCCBDB'
    ),
    'NH3': MoleculeGeometry(
        name='Ammonia',
        atoms=['N', 'H', 'H', 'H'],
        bond_lengths={'N-H': 1.012},
        bond_angles={'H-N-H': 106.7},
        reference='NIST CCCBDB'
    ),
    'O2': MoleculeGeometry(
        name='Oxygen',
        atoms=['O', 'O'],
        bond_lengths={'O-O': 1.208},
        bond_angles={},
        reference='NIST CCCBDB'
    ),
    'N2': MoleculeGeometry(
        name='Nitrogen',
        atoms=['N', 'N'],
        bond_lengths={'N-N': 1.098},
        bond_angles={},
        reference='NIST CCCBDB'
    ),
    'CO2': MoleculeGeometry(
        name='Carbon Dioxide',
        atoms=['C', 'O', 'O'],
        bond_lengths={'C-O': 1.160},
        bond_angles={'O-C-O': 180.0},
        reference='NIST CCCBDB'
    ),
    'H2': MoleculeGeometry(
        name='Hydrogen',
        atoms=['H', 'H'],
        bond_lengths={'H-H': 0.741},
        bond_angles={},
        reference='NIST CCCBDB'
    ),
}


# ============================================================================
# Metal Lattice References
# ============================================================================

METAL_LATTICES: Dict[str, MetalLattice] = {
    'Cu': MetalLattice(
        metal='Copper',
        structure='fcc',
        lattice_constant=3.615,
        nearest_neighbor=2.556,
        reference='Kittel, Introduction to Solid State Physics'
    ),
    'Pt': MetalLattice(
        metal='Platinum',
        structure='fcc',
        lattice_constant=3.924,
        nearest_neighbor=2.775,
        reference='Kittel'
    ),
    'Ni': MetalLattice(
        metal='Nickel',
        structure='fcc',
        lattice_constant=3.524,
        nearest_neighbor=2.492,
        reference='Kittel'
    ),
    'Au': MetalLattice(
        metal='Gold',
        structure='fcc',
        lattice_constant=4.078,
        nearest_neighbor=2.884,
        reference='Kittel'
    ),
    'Ag': MetalLattice(
        metal='Silver',
        structure='fcc',
        lattice_constant=4.085,
        nearest_neighbor=2.889,
        reference='Kittel'
    ),
    'Pd': MetalLattice(
        metal='Palladium',
        structure='fcc',
        lattice_constant=3.891,
        nearest_neighbor=2.751,
        reference='Kittel'
    ),
    'Fe': MetalLattice(
        metal='Iron',
        structure='bcc',
        lattice_constant=2.867,
        nearest_neighbor=2.482,
        reference='Kittel'
    ),
}


# ============================================================================
# Physical Constants
# ============================================================================

PHYSICAL_CONSTANTS = {
    'kB_eV_K': 8.617333262e-5,  # Boltzmann constant in eV/K
    'kB_J_K': 1.380649e-23,     # Boltzmann constant in J/K
    'eV_to_kJ_mol': 96.485,     # eV to kJ/mol
    'eV_to_kcal_mol': 23.061,   # eV to kcal/mol
    'Hartree_to_eV': 27.211386, # Hartree to eV
    'Bohr_to_Angstrom': 0.529177, # Bohr to Å
    'amu_to_kg': 1.66054e-27,  # atomic mass unit to kg
    'fs_to_s': 1e-15,          # femtosecond to second
}


# ============================================================================
# Validation Thresholds
# ============================================================================

VALIDATION_THRESHOLDS = {
    # Adsorption energy
    'chemisorption_min': -5.0,  # eV
    'chemisorption_max': -0.3,  # eV
    'physisorption_min': -0.3,  # eV
    'physisorption_max': -0.01, # eV
    'energy_relative_error': 0.20,  # 20% tolerance vs reference
    
    # MD simulation
    'energy_drift_max': 0.001,  # eV/ps/atom (NVE)
    'temperature_tolerance': 10.0,  # K (NVT)
    'pressure_tolerance': 0.1,  # bar (NPT)
    
    # Optimization
    'fmax_default': 0.05,  # eV/Å
    'energy_convergence': 1e-6,  # eV
    'structure_rmsd': 1e-4,  # Å
    
    # Geometry
    'bond_length_tolerance': 0.05,  # Å
    'bond_angle_tolerance': 5.0,  # degrees
    'min_interatomic_distance': 0.5,  # Å
}


def get_adsorption_reference(molecule: str, surface: str) -> Optional[AdsorptionReference]:
    """Get reference adsorption energy for molecule/surface pair."""
    for ref in ADSORPTION_REFERENCES:
        if ref.molecule == molecule and ref.surface == surface:
            return ref
    return None


def get_molecule_geometry(molecule: str) -> Optional[MoleculeGeometry]:
    """Get reference geometry for a molecule."""
    return MOLECULE_GEOMETRIES.get(molecule)


def get_metal_lattice(metal: str) -> Optional[MetalLattice]:
    """Get reference lattice parameters for a metal."""
    return METAL_LATTICES.get(metal)
