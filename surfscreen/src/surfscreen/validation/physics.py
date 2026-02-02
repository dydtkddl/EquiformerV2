"""
Physical validation functions for computational chemistry calculations.

Provides validation for:
- Adsorption energy calculations
- MD simulation physics
- Geometry optimization results
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .reference_data import (
    VALIDATION_THRESHOLDS,
    PHYSICAL_CONSTANTS,
    get_adsorption_reference,
    get_molecule_geometry,
)


class ValidationStatus(Enum):
    """Validation result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


@dataclass
class ValidationResult:
    """Single validation check result."""
    name: str
    status: ValidationStatus
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    tolerance: Optional[float] = None


# ============================================================================
# Adsorption Energy Validation
# ============================================================================

def validate_adsorption_energy_formula(
    E_total: float,
    E_surface: float,
    E_molecule: float,
    E_ads_calculated: float,
    tolerance: float = 1e-6
) -> ValidationResult:
    """
    Validate that E_ads = E_total - E_surface - E_molecule.
    
    Args:
        E_total: Total energy of adsorbed system (eV)
        E_surface: Energy of clean surface (eV)
        E_molecule: Energy of isolated molecule (eV)
        E_ads_calculated: Calculated adsorption energy (eV)
        tolerance: Numerical tolerance
        
    Returns:
        ValidationResult
    """
    expected = E_total - E_surface - E_molecule
    error = abs(expected - E_ads_calculated)
    
    if error < tolerance:
        return ValidationResult(
            name="Adsorption Energy Formula",
            status=ValidationStatus.PASS,
            message=f"E_ads = {E_ads_calculated:.6f} eV correctly calculated",
            expected=expected,
            actual=E_ads_calculated,
            tolerance=tolerance
        )
    else:
        return ValidationResult(
            name="Adsorption Energy Formula",
            status=ValidationStatus.FAIL,
            message=f"E_ads mismatch: expected {expected:.6f}, got {E_ads_calculated:.6f}",
            expected=expected,
            actual=E_ads_calculated,
            tolerance=tolerance
        )


def validate_adsorption_energy_range(
    E_ads: float,
    adsorption_type: str = "chemisorption"
) -> ValidationResult:
    """
    Validate that adsorption energy is in physically reasonable range.
    
    Args:
        E_ads: Adsorption energy in eV (should be negative)
        adsorption_type: 'chemisorption' or 'physisorption'
        
    Returns:
        ValidationResult
    """
    thresholds = VALIDATION_THRESHOLDS
    
    if adsorption_type == "chemisorption":
        min_val = thresholds['chemisorption_min']
        max_val = thresholds['chemisorption_max']
    else:
        min_val = thresholds['physisorption_min']
        max_val = thresholds['physisorption_max']
    
    if E_ads > 0:
        return ValidationResult(
            name="Adsorption Energy Range",
            status=ValidationStatus.FAIL,
            message=f"Positive E_ads ({E_ads:.3f} eV) indicates repulsion, not adsorption",
            expected=f"[{min_val}, {max_val}] eV",
            actual=E_ads
        )
    elif E_ads < min_val:
        return ValidationResult(
            name="Adsorption Energy Range",
            status=ValidationStatus.WARNING,
            message=f"E_ads = {E_ads:.3f} eV is unusually strong (< {min_val} eV)",
            expected=f"[{min_val}, {max_val}] eV",
            actual=E_ads
        )
    elif E_ads > max_val:
        return ValidationResult(
            name="Adsorption Energy Range",
            status=ValidationStatus.WARNING,
            message=f"E_ads = {E_ads:.3f} eV is unusually weak (> {max_val} eV)",
            expected=f"[{min_val}, {max_val}] eV",
            actual=E_ads
        )
    else:
        return ValidationResult(
            name="Adsorption Energy Range",
            status=ValidationStatus.PASS,
            message=f"E_ads = {E_ads:.3f} eV is in reasonable {adsorption_type} range",
            expected=f"[{min_val}, {max_val}] eV",
            actual=E_ads
        )


def validate_adsorption_vs_reference(
    E_ads: float,
    molecule: str,
    surface: str,
    tolerance: Optional[float] = None
) -> ValidationResult:
    """
    Compare calculated adsorption energy with reference value.
    
    Args:
        E_ads: Calculated adsorption energy (eV)
        molecule: Molecule name (e.g., 'CO')
        surface: Surface name (e.g., 'Cu(111)')
        tolerance: Relative tolerance (default from VALIDATION_THRESHOLDS)
        
    Returns:
        ValidationResult
    """
    ref = get_adsorption_reference(molecule, surface)
    
    if ref is None:
        return ValidationResult(
            name="Adsorption vs Reference",
            status=ValidationStatus.SKIPPED,
            message=f"No reference data for {molecule}/{surface}",
            actual=E_ads
        )
    
    if tolerance is None:
        tolerance = VALIDATION_THRESHOLDS['energy_relative_error']
    
    relative_error = abs((E_ads - ref.energy_eV) / ref.energy_eV)
    
    if relative_error <= tolerance:
        return ValidationResult(
            name="Adsorption vs Reference",
            status=ValidationStatus.PASS,
            message=f"{molecule}/{surface}: calc={E_ads:.3f} eV, ref={ref.energy_eV:.3f} eV ({ref.method}), error={relative_error*100:.1f}%",
            expected=ref.energy_eV,
            actual=E_ads,
            tolerance=tolerance
        )
    else:
        return ValidationResult(
            name="Adsorption vs Reference",
            status=ValidationStatus.WARNING,
            message=f"{molecule}/{surface}: calc={E_ads:.3f} eV differs from ref={ref.energy_eV:.3f} eV by {relative_error*100:.1f}% (tolerance: {tolerance*100:.1f}%)",
            expected=ref.energy_eV,
            actual=E_ads,
            tolerance=tolerance
        )


# ============================================================================
# MD Simulation Validation
# ============================================================================

def validate_energy_conservation(
    energies: np.ndarray,
    timestep_fs: float,
    n_atoms: int,
    threshold: Optional[float] = None
) -> ValidationResult:
    """
    Validate energy conservation in NVE MD simulation.
    
    Args:
        energies: Array of total energies (E_kinetic + E_potential) per step
        timestep_fs: MD timestep in femtoseconds
        n_atoms: Number of atoms
        threshold: Maximum allowed drift (eV/ps/atom)
        
    Returns:
        ValidationResult
    """
    if threshold is None:
        threshold = VALIDATION_THRESHOLDS['energy_drift_max']
    
    n_steps = len(energies)
    total_time_ps = n_steps * timestep_fs / 1000  # fs to ps
    
    # Linear fit to detect drift
    steps = np.arange(n_steps)
    coeffs = np.polyfit(steps, energies, 1)
    drift_per_step = coeffs[0]  # eV/step
    drift_per_ps = drift_per_step * 1000 / timestep_fs  # eV/ps
    drift_per_ps_per_atom = abs(drift_per_ps) / n_atoms
    
    if drift_per_ps_per_atom < threshold:
        return ValidationResult(
            name="Energy Conservation (NVE)",
            status=ValidationStatus.PASS,
            message=f"Energy drift = {drift_per_ps_per_atom:.2e} eV/ps/atom < threshold ({threshold:.2e})",
            expected=f"< {threshold} eV/ps/atom",
            actual=drift_per_ps_per_atom,
            tolerance=threshold
        )
    else:
        return ValidationResult(
            name="Energy Conservation (NVE)",
            status=ValidationStatus.FAIL,
            message=f"Energy drift = {drift_per_ps_per_atom:.2e} eV/ps/atom exceeds threshold ({threshold:.2e})",
            expected=f"< {threshold} eV/ps/atom",
            actual=drift_per_ps_per_atom,
            tolerance=threshold
        )


def validate_temperature_stability(
    temperatures: np.ndarray,
    target_temperature: float,
    tolerance: Optional[float] = None
) -> ValidationResult:
    """
    Validate temperature stability in NVT MD simulation.
    
    Args:
        temperatures: Array of instantaneous temperatures (K)
        target_temperature: Target temperature (K)
        tolerance: Maximum allowed deviation (K)
        
    Returns:
        ValidationResult
    """
    if tolerance is None:
        tolerance = VALIDATION_THRESHOLDS['temperature_tolerance']
    
    mean_temp = np.mean(temperatures)
    std_temp = np.std(temperatures)
    deviation = abs(mean_temp - target_temperature)
    
    if deviation <= tolerance:
        return ValidationResult(
            name="Temperature Stability (NVT)",
            status=ValidationStatus.PASS,
            message=f"Mean T = {mean_temp:.1f} ± {std_temp:.1f} K (target: {target_temperature} K, deviation: {deviation:.1f} K)",
            expected=target_temperature,
            actual=mean_temp,
            tolerance=tolerance
        )
    else:
        return ValidationResult(
            name="Temperature Stability (NVT)",
            status=ValidationStatus.WARNING,
            message=f"Mean T = {mean_temp:.1f} K deviates from target {target_temperature} K by {deviation:.1f} K",
            expected=target_temperature,
            actual=mean_temp,
            tolerance=tolerance
        )


def validate_boltzmann_distribution(
    kinetic_energies: np.ndarray,
    temperature: float,
    n_atoms: int
) -> ValidationResult:
    """
    Validate that kinetic energy follows Boltzmann distribution.
    
    <KE> = 3/2 * N * kB * T for 3D system
    
    Args:
        kinetic_energies: Array of total kinetic energies (eV)
        temperature: Target temperature (K)
        n_atoms: Number of atoms
        
    Returns:
        ValidationResult
    """
    kB = PHYSICAL_CONSTANTS['kB_eV_K']
    expected_ke = 1.5 * n_atoms * kB * temperature
    
    mean_ke = np.mean(kinetic_energies)
    relative_error = abs((mean_ke - expected_ke) / expected_ke)
    
    # Allow 10% tolerance for finite sampling
    tolerance = 0.10
    
    if relative_error <= tolerance:
        return ValidationResult(
            name="Boltzmann Distribution",
            status=ValidationStatus.PASS,
            message=f"<KE> = {mean_ke:.4f} eV, expected = {expected_ke:.4f} eV (error: {relative_error*100:.1f}%)",
            expected=expected_ke,
            actual=mean_ke,
            tolerance=tolerance
        )
    else:
        return ValidationResult(
            name="Boltzmann Distribution",
            status=ValidationStatus.WARNING,
            message=f"<KE> = {mean_ke:.4f} eV differs from expected {expected_ke:.4f} eV by {relative_error*100:.1f}%",
            expected=expected_ke,
            actual=mean_ke,
            tolerance=tolerance
        )


# ============================================================================
# Geometry Validation
# ============================================================================

def validate_bond_length(
    atoms_positions: np.ndarray,
    atom_indices: Tuple[int, int],
    expected_length: float,
    tolerance: Optional[float] = None
) -> ValidationResult:
    """
    Validate bond length between two atoms.
    
    Args:
        atoms_positions: Nx3 array of atomic positions (Å)
        atom_indices: Tuple of (atom1_idx, atom2_idx)
        expected_length: Expected bond length (Å)
        tolerance: Maximum allowed deviation (Å)
        
    Returns:
        ValidationResult
    """
    if tolerance is None:
        tolerance = VALIDATION_THRESHOLDS['bond_length_tolerance']
    
    i, j = atom_indices
    distance = np.linalg.norm(atoms_positions[i] - atoms_positions[j])
    deviation = abs(distance - expected_length)
    
    if deviation <= tolerance:
        return ValidationResult(
            name=f"Bond Length ({i}-{j})",
            status=ValidationStatus.PASS,
            message=f"Bond length = {distance:.3f} Å (expected: {expected_length:.3f} Å)",
            expected=expected_length,
            actual=distance,
            tolerance=tolerance
        )
    else:
        return ValidationResult(
            name=f"Bond Length ({i}-{j})",
            status=ValidationStatus.FAIL,
            message=f"Bond length = {distance:.3f} Å deviates from expected {expected_length:.3f} Å by {deviation:.3f} Å",
            expected=expected_length,
            actual=distance,
            tolerance=tolerance
        )


def validate_minimum_distance(
    positions: np.ndarray,
    min_distance: Optional[float] = None
) -> ValidationResult:
    """
    Validate that no atoms are too close (unphysical overlap).
    
    Args:
        positions: Nx3 array of atomic positions (Å)
        min_distance: Minimum allowed interatomic distance (Å)
        
    Returns:
        ValidationResult
    """
    if min_distance is None:
        min_distance = VALIDATION_THRESHOLDS['min_interatomic_distance']
    
    n_atoms = len(positions)
    min_found = float('inf')
    min_pair = (0, 0)
    
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            dist = np.linalg.norm(positions[i] - positions[j])
            if dist < min_found:
                min_found = dist
                min_pair = (i, j)
    
    if min_found >= min_distance:
        return ValidationResult(
            name="Minimum Interatomic Distance",
            status=ValidationStatus.PASS,
            message=f"Min distance = {min_found:.3f} Å (atoms {min_pair}) >= threshold ({min_distance} Å)",
            expected=f">= {min_distance} Å",
            actual=min_found
        )
    else:
        return ValidationResult(
            name="Minimum Interatomic Distance",
            status=ValidationStatus.FAIL,
            message=f"Atoms {min_pair} are too close: {min_found:.3f} Å < {min_distance} Å",
            expected=f">= {min_distance} Å",
            actual=min_found
        )


def validate_force_convergence(
    forces: np.ndarray,
    fmax_threshold: Optional[float] = None
) -> ValidationResult:
    """
    Validate that maximum force is below threshold.
    
    Args:
        forces: Nx3 array of forces (eV/Å)
        fmax_threshold: Maximum allowed force magnitude
        
    Returns:
        ValidationResult
    """
    if fmax_threshold is None:
        fmax_threshold = VALIDATION_THRESHOLDS['fmax_default']
    
    force_magnitudes = np.linalg.norm(forces, axis=1)
    fmax = np.max(force_magnitudes)
    
    if fmax <= fmax_threshold:
        return ValidationResult(
            name="Force Convergence",
            status=ValidationStatus.PASS,
            message=f"fmax = {fmax:.4f} eV/Å <= threshold ({fmax_threshold} eV/Å)",
            expected=f"<= {fmax_threshold} eV/Å",
            actual=fmax,
            tolerance=fmax_threshold
        )
    else:
        return ValidationResult(
            name="Force Convergence",
            status=ValidationStatus.FAIL,
            message=f"fmax = {fmax:.4f} eV/Å > threshold ({fmax_threshold} eV/Å)",
            expected=f"<= {fmax_threshold} eV/Å",
            actual=fmax,
            tolerance=fmax_threshold
        )


def validate_newton_equilibrium(
    forces: np.ndarray,
    tolerance: float = 1e-6
) -> ValidationResult:
    """
    Validate Newton's first law: sum of forces ≈ 0 at equilibrium.
    
    Args:
        forces: Nx3 array of forces (eV/Å)
        tolerance: Maximum allowed total force magnitude
        
    Returns:
        ValidationResult
    """
    total_force = np.sum(forces, axis=0)
    total_magnitude = np.linalg.norm(total_force)
    
    if total_magnitude <= tolerance:
        return ValidationResult(
            name="Newton Equilibrium (ΣF = 0)",
            status=ValidationStatus.PASS,
            message=f"Sum of forces = {total_magnitude:.2e} eV/Å ≈ 0",
            expected=0.0,
            actual=total_magnitude,
            tolerance=tolerance
        )
    else:
        return ValidationResult(
            name="Newton Equilibrium (ΣF = 0)",
            status=ValidationStatus.WARNING,
            message=f"Sum of forces = {total_magnitude:.2e} eV/Å (expected ~0)",
            expected=0.0,
            actual=total_magnitude,
            tolerance=tolerance
        )
