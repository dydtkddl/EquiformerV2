"""
Physical constants and unit conversion utilities.

Provides accurate unit conversions for:
- Energy (eV, kJ/mol, kcal/mol, Hartree)
- Length (Å, Bohr, nm)
- Time (fs, ps, atomic units)
- Temperature/Energy (K, eV)
"""

import numpy as np
from typing import Union

Number = Union[int, float, np.ndarray]


# ============================================================================
# Physical Constants (CODATA 2018)
# ============================================================================

# Boltzmann constant
kB_eV_K = 8.617333262e-5      # eV/K
kB_J_K = 1.380649e-23         # J/K
kB_kJ_mol_K = 8.314462618e-3  # kJ/(mol·K)

# Avogadro's number
AVOGADRO = 6.02214076e23  # 1/mol

# Planck constant
PLANCK_J_s = 6.62607015e-34   # J·s
PLANCK_eV_s = 4.135667696e-15 # eV·s
HBAR_eV_s = 6.582119569e-16   # ℏ in eV·s

# Elementary charge
ELEMENTARY_CHARGE = 1.602176634e-19  # C

# Atomic mass unit
AMU_KG = 1.66053906660e-27  # kg

# Speed of light
SPEED_OF_LIGHT = 299792458  # m/s


# ============================================================================
# Energy Conversion Factors
# ============================================================================

# eV conversions
EV_TO_J = 1.602176634e-19
EV_TO_KJ_MOL = 96.48530749
EV_TO_KCAL_MOL = 23.0605419
EV_TO_HARTREE = 0.03674932218
EV_TO_CM1 = 8065.544  # wavenumber

# Hartree conversions
HARTREE_TO_EV = 27.211386245988
HARTREE_TO_KJ_MOL = 2625.4996394799
HARTREE_TO_KCAL_MOL = 627.5094740631

# kJ/mol conversions
KJ_MOL_TO_EV = 1.0 / EV_TO_KJ_MOL
KJ_MOL_TO_KCAL_MOL = 0.239005736

# kcal/mol conversions
KCAL_MOL_TO_EV = 1.0 / EV_TO_KCAL_MOL
KCAL_MOL_TO_KJ_MOL = 4.184


# ============================================================================
# Length Conversion Factors
# ============================================================================

ANGSTROM_TO_BOHR = 1.8897259886
BOHR_TO_ANGSTROM = 0.529177210903
ANGSTROM_TO_NM = 0.1
NM_TO_ANGSTROM = 10.0
ANGSTROM_TO_M = 1e-10
M_TO_ANGSTROM = 1e10


# ============================================================================
# Time Conversion Factors
# ============================================================================

FS_TO_S = 1e-15
S_TO_FS = 1e15
PS_TO_S = 1e-12
S_TO_PS = 1e12
FS_TO_PS = 1e-3
PS_TO_FS = 1e3

# Atomic time unit (ℏ/Hartree)
AU_TIME_TO_FS = 0.02418884254
FS_TO_AU_TIME = 1.0 / AU_TIME_TO_FS


# ============================================================================
# Energy Conversion Functions
# ============================================================================

def eV_to_kJ_mol(energy: Number) -> Number:
    """Convert energy from eV to kJ/mol."""
    return energy * EV_TO_KJ_MOL


def kJ_mol_to_eV(energy: Number) -> Number:
    """Convert energy from kJ/mol to eV."""
    return energy * KJ_MOL_TO_EV


def eV_to_kcal_mol(energy: Number) -> Number:
    """Convert energy from eV to kcal/mol."""
    return energy * EV_TO_KCAL_MOL


def kcal_mol_to_eV(energy: Number) -> Number:
    """Convert energy from kcal/mol to eV."""
    return energy * KCAL_MOL_TO_EV


def eV_to_Hartree(energy: Number) -> Number:
    """Convert energy from eV to Hartree."""
    return energy * EV_TO_HARTREE


def Hartree_to_eV(energy: Number) -> Number:
    """Convert energy from Hartree to eV."""
    return energy * HARTREE_TO_EV


def eV_to_J(energy: Number) -> Number:
    """Convert energy from eV to Joules."""
    return energy * EV_TO_J


def J_to_eV(energy: Number) -> Number:
    """Convert energy from Joules to eV."""
    return energy / EV_TO_J


def kJ_mol_to_kcal_mol(energy: Number) -> Number:
    """Convert energy from kJ/mol to kcal/mol."""
    return energy * KJ_MOL_TO_KCAL_MOL


def kcal_mol_to_kJ_mol(energy: Number) -> Number:
    """Convert energy from kcal/mol to kJ/mol."""
    return energy * KCAL_MOL_TO_KJ_MOL


# ============================================================================
# Length Conversion Functions
# ============================================================================

def angstrom_to_bohr(length: Number) -> Number:
    """Convert length from Ångström to Bohr."""
    return length * ANGSTROM_TO_BOHR


def bohr_to_angstrom(length: Number) -> Number:
    """Convert length from Bohr to Ångström."""
    return length * BOHR_TO_ANGSTROM


def angstrom_to_nm(length: Number) -> Number:
    """Convert length from Ångström to nanometers."""
    return length * ANGSTROM_TO_NM


def nm_to_angstrom(length: Number) -> Number:
    """Convert length from nanometers to Ångström."""
    return length * NM_TO_ANGSTROM


# ============================================================================
# Time Conversion Functions
# ============================================================================

def fs_to_ps(time: Number) -> Number:
    """Convert time from femtoseconds to picoseconds."""
    return time * FS_TO_PS


def ps_to_fs(time: Number) -> Number:
    """Convert time from picoseconds to femtoseconds."""
    return time * PS_TO_FS


def fs_to_au(time: Number) -> Number:
    """Convert time from femtoseconds to atomic time units."""
    return time * FS_TO_AU_TIME


def au_to_fs(time: Number) -> Number:
    """Convert time from atomic time units to femtoseconds."""
    return time * AU_TIME_TO_FS


# ============================================================================
# Temperature-Energy Conversion Functions
# ============================================================================

def K_to_eV(temperature: Number) -> Number:
    """Convert temperature from Kelvin to thermal energy in eV."""
    return temperature * kB_eV_K


def eV_to_K(energy: Number) -> Number:
    """Convert thermal energy from eV to temperature in Kelvin."""
    return energy / kB_eV_K


def K_to_kJ_mol(temperature: Number) -> Number:
    """Convert temperature from Kelvin to thermal energy in kJ/mol."""
    return temperature * kB_kJ_mol_K


# ============================================================================
# Validation Functions
# ============================================================================

def validate_unit_conversion_roundtrip(
    value: float,
    forward_func,
    backward_func,
    tolerance: float = 1e-10
) -> bool:
    """
    Validate that forward and backward conversion are consistent.
    
    Args:
        value: Original value to convert
        forward_func: Function to convert forward
        backward_func: Function to convert backward
        tolerance: Maximum allowed relative error
        
    Returns:
        True if roundtrip conversion is accurate within tolerance
    """
    converted = forward_func(value)
    recovered = backward_func(converted)
    
    if value == 0:
        return abs(recovered) < tolerance
    
    relative_error = abs((recovered - value) / value)
    return relative_error < tolerance


def verify_all_conversions() -> dict:
    """
    Verify all unit conversions for consistency.
    
    Returns:
        Dictionary with conversion name and pass/fail status
    """
    test_value = 1.0
    results = {}
    
    # Energy conversions
    conversions = [
        ('eV <-> kJ/mol', eV_to_kJ_mol, kJ_mol_to_eV),
        ('eV <-> kcal/mol', eV_to_kcal_mol, kcal_mol_to_eV),
        ('eV <-> Hartree', eV_to_Hartree, Hartree_to_eV),
        ('eV <-> J', eV_to_J, J_to_eV),
        ('kJ/mol <-> kcal/mol', kJ_mol_to_kcal_mol, kcal_mol_to_kJ_mol),
        
        # Length conversions
        ('Å <-> Bohr', angstrom_to_bohr, bohr_to_angstrom),
        ('Å <-> nm', angstrom_to_nm, nm_to_angstrom),
        
        # Time conversions
        ('fs <-> ps', fs_to_ps, ps_to_fs),
        ('fs <-> au', fs_to_au, au_to_fs),
        
        # Temperature-Energy
        ('K <-> eV', K_to_eV, eV_to_K),
    ]
    
    for name, forward, backward in conversions:
        results[name] = validate_unit_conversion_roundtrip(
            test_value, forward, backward
        )
    
    return results
