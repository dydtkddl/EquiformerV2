"""
SurfScreen Validation Module

Provides scientific validation for computational chemistry calculations:
- Adsorption energy validation
- MD simulation physics validation
- Geometry and optimization validation
- Unit conversion utilities
- Reference data (experimental + DFT)
"""

from .physics import (
    ValidationStatus,
    ValidationResult,
    validate_adsorption_energy_formula,
    validate_adsorption_energy_range,
    validate_adsorption_vs_reference,
    validate_energy_conservation,
    validate_temperature_stability,
    validate_boltzmann_distribution,
    validate_bond_length,
    validate_minimum_distance,
    validate_force_convergence,
    validate_newton_equilibrium,
)

from .reference_data import (
    AdsorptionReference,
    MoleculeGeometry,
    MetalLattice,
    ADSORPTION_REFERENCES,
    MOLECULE_GEOMETRIES,
    METAL_LATTICES,
    PHYSICAL_CONSTANTS,
    VALIDATION_THRESHOLDS,
    get_adsorption_reference,
    get_molecule_geometry,
    get_metal_lattice,
)

from .units import (
    eV_to_kJ_mol,
    kJ_mol_to_eV,
    eV_to_kcal_mol,
    kcal_mol_to_eV,
    eV_to_Hartree,
    Hartree_to_eV,
    angstrom_to_bohr,
    bohr_to_angstrom,
    K_to_eV,
    eV_to_K,
    verify_all_conversions,
)

from .reporter import ValidationReporter


__all__ = [
    # Physics validation
    'ValidationStatus',
    'ValidationResult',
    'validate_adsorption_energy_formula',
    'validate_adsorption_energy_range',
    'validate_adsorption_vs_reference',
    'validate_energy_conservation',
    'validate_temperature_stability',
    'validate_boltzmann_distribution',
    'validate_bond_length',
    'validate_minimum_distance',
    'validate_force_convergence',
    'validate_newton_equilibrium',
    
    # Reference data
    'AdsorptionReference',
    'MoleculeGeometry',
    'MetalLattice',
    'ADSORPTION_REFERENCES',
    'MOLECULE_GEOMETRIES',
    'METAL_LATTICES',
    'PHYSICAL_CONSTANTS',
    'VALIDATION_THRESHOLDS',
    'get_adsorption_reference',
    'get_molecule_geometry',
    'get_metal_lattice',
    
    # Units
    'eV_to_kJ_mol',
    'kJ_mol_to_eV',
    'eV_to_kcal_mol',
    'kcal_mol_to_eV',
    'eV_to_Hartree',
    'Hartree_to_eV',
    'angstrom_to_bohr',
    'bohr_to_angstrom',
    'K_to_eV',
    'eV_to_K',
    'verify_all_conversions',
    
    # Reporter
    'ValidationReporter',
]
