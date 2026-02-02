"""
Scientific Validation Tests: Geometry and Optimization

Tests for validating:
- Bond lengths and angles
- Minimum interatomic distances
- Force convergence
- Newton's equilibrium condition
"""

import pytest
import numpy as np

from surfscreen.validation import (
    ValidationStatus,
    validate_bond_length,
    validate_minimum_distance,
    validate_force_convergence,
    validate_newton_equilibrium,
    get_molecule_geometry,
    VALIDATION_THRESHOLDS,
)


class TestBondLengthValidation:
    """Test bond length validation."""
    
    def test_correct_co_bond(self):
        """Test correct C-O bond length passes."""
        # CO molecule: C at origin, O at 1.128 Å
        positions = np.array([
            [0.0, 0.0, 0.0],  # C
            [0.0, 0.0, 1.128]  # O
        ])
        
        ref = get_molecule_geometry('CO')
        expected = ref.bond_lengths['C-O']
        
        result = validate_bond_length(
            atoms_positions=positions,
            atom_indices=(0, 1),
            expected_length=expected
        )
        
        assert result.status == ValidationStatus.PASS
    
    def test_stretched_bond_fails(self):
        """Test stretched bond fails."""
        # CO molecule with stretched bond
        positions = np.array([
            [0.0, 0.0, 0.0],  # C
            [0.0, 0.0, 1.5]    # O (stretched from 1.128)
        ])
        
        result = validate_bond_length(
            atoms_positions=positions,
            atom_indices=(0, 1),
            expected_length=1.128,
            tolerance=0.05
        )
        
        assert result.status == ValidationStatus.FAIL
        assert "deviates" in result.message.lower()
    
    def test_h2o_bond_length(self):
        """Test H2O O-H bond length."""
        # H2O molecule
        positions = np.array([
            [0.0, 0.0, 0.0],     # O
            [0.757, 0.586, 0.0], # H1
            [-0.757, 0.586, 0.0] # H2
        ])
        
        ref = get_molecule_geometry('H2O')
        expected = ref.bond_lengths['O-H']
        
        result = validate_bond_length(
            atoms_positions=positions,
            atom_indices=(0, 1),
            expected_length=expected,
            tolerance=0.05
        )
        
        assert result.status == ValidationStatus.PASS
    
    def test_custom_tolerance(self):
        """Test custom tolerance for bond length."""
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.15]  # Slightly off from 1.128
        ])
        
        result_strict = validate_bond_length(
            atoms_positions=positions,
            atom_indices=(0, 1),
            expected_length=1.128,
            tolerance=0.01
        )
        
        result_loose = validate_bond_length(
            atoms_positions=positions,
            atom_indices=(0, 1),
            expected_length=1.128,
            tolerance=0.05
        )
        
        assert result_strict.status == ValidationStatus.FAIL
        assert result_loose.status == ValidationStatus.PASS


class TestMinimumDistanceValidation:
    """Test minimum interatomic distance validation."""
    
    def test_normal_structure(self):
        """Test normal structure passes."""
        # Cu atoms with proper spacing
        positions = np.array([
            [0.0, 0.0, 0.0],
            [2.556, 0.0, 0.0],
            [1.278, 2.213, 0.0],
        ])
        
        result = validate_minimum_distance(positions)
        
        assert result.status == ValidationStatus.PASS
        assert "Min distance" in result.message
    
    def test_overlapping_atoms_fails(self):
        """Test overlapping atoms fails."""
        # Two atoms very close together
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],  # Only 0.1 Å apart!
            [5.0, 0.0, 0.0],
        ])
        
        result = validate_minimum_distance(positions, min_distance=0.5)
        
        assert result.status == ValidationStatus.FAIL
        assert "too close" in result.message.lower()
    
    def test_h2_molecule(self):
        """Test H2 molecule bond length is valid."""
        # H2: H-H = 0.741 Å
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.741, 0.0, 0.0],
        ])
        
        result = validate_minimum_distance(positions, min_distance=0.5)
        
        assert result.status == ValidationStatus.PASS
    
    def test_finds_minimum_pair(self):
        """Test that the correct minimum pair is identified."""
        positions = np.array([
            [0.0, 0.0, 0.0],   # 0
            [5.0, 0.0, 0.0],   # 1 - far from 0
            [5.5, 0.0, 0.0],   # 2 - close to 1 (0.5 Å)
            [10.0, 0.0, 0.0],  # 3 - far from all
        ])
        
        result = validate_minimum_distance(positions, min_distance=0.4)
        
        assert result.status == ValidationStatus.PASS
        # Minimum should be between atoms 1 and 2
        assert "0.5" in result.message or "(1, 2)" in result.message


class TestForceConvergence:
    """Test force convergence validation."""
    
    def test_converged_forces(self):
        """Test converged forces pass."""
        # Small forces
        forces = np.array([
            [0.01, -0.01, 0.005],
            [-0.01, 0.01, -0.005],
            [0.0, 0.0, 0.0],
        ])
        
        result = validate_force_convergence(forces, fmax_threshold=0.05)
        
        assert result.status == ValidationStatus.PASS
        assert "fmax" in result.message.lower()
    
    def test_unconverged_forces_fails(self):
        """Test unconverged forces fail."""
        # Large forces
        forces = np.array([
            [0.5, 0.0, 0.0],
            [-0.5, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ])
        
        result = validate_force_convergence(forces, fmax_threshold=0.05)
        
        assert result.status == ValidationStatus.FAIL
        assert ">" in result.message
    
    def test_default_threshold(self):
        """Test default force threshold."""
        default_fmax = VALIDATION_THRESHOLDS['fmax_default']
        
        # Just under threshold
        forces = np.array([
            [default_fmax * 0.9, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ])
        
        result = validate_force_convergence(forces)
        
        assert result.status == ValidationStatus.PASS
    
    def test_3d_force_magnitude(self):
        """Test that 3D force magnitude is correctly calculated."""
        # Force vector with components that give known magnitude
        # |F| = sqrt(0.03^2 + 0.04^2 + 0.0^2) = 0.05
        forces = np.array([
            [0.03, 0.04, 0.0],
        ])
        
        result = validate_force_convergence(forces, fmax_threshold=0.05)
        
        assert result.status == ValidationStatus.PASS


class TestNewtonEquilibrium:
    """Test Newton's first law (ΣF = 0 at equilibrium)."""
    
    def test_balanced_forces(self):
        """Test balanced forces pass."""
        # Forces that sum to zero
        forces = np.array([
            [1.0, 0.0, 0.0],
            [-0.5, 0.5, 0.0],
            [-0.5, -0.5, 0.0],
        ])
        
        result = validate_newton_equilibrium(forces)
        
        assert result.status == ValidationStatus.PASS
        assert "≈ 0" in result.message
    
    def test_unbalanced_forces_warns(self):
        """Test unbalanced forces warn."""
        # Forces that don't sum to zero
        forces = np.array([
            [1.0, 0.0, 0.0],
            [0.5, 0.0, 0.0],
        ])
        
        result = validate_newton_equilibrium(forces, tolerance=1e-6)
        
        assert result.status == ValidationStatus.WARNING
    
    def test_numerical_zero(self):
        """Test numerical near-zero is accepted."""
        # Forces that almost sum to zero (numerical precision)
        forces = np.array([
            [1.0, 0.0, 0.0],
            [-1.0 + 1e-10, 0.0, 0.0],
        ])
        
        result = validate_newton_equilibrium(forces, tolerance=1e-6)
        
        assert result.status == ValidationStatus.PASS


class TestMoleculeGeometries:
    """Test reference molecule geometries."""
    
    def test_co_geometry(self):
        """Test CO geometry reference."""
        ref = get_molecule_geometry('CO')
        
        assert ref is not None
        assert 'C-O' in ref.bond_lengths
        assert 1.1 < ref.bond_lengths['C-O'] < 1.2
    
    def test_h2o_geometry(self):
        """Test H2O geometry reference."""
        ref = get_molecule_geometry('H2O')
        
        assert ref is not None
        assert 'O-H' in ref.bond_lengths
        assert 'H-O-H' in ref.bond_angles
        assert 0.9 < ref.bond_lengths['O-H'] < 1.0
        assert 100 < ref.bond_angles['H-O-H'] < 110
    
    def test_ch4_tetrahedral(self):
        """Test CH4 tetrahedral geometry."""
        ref = get_molecule_geometry('CH4')
        
        assert ref is not None
        assert 'C-H' in ref.bond_lengths
        assert 'H-C-H' in ref.bond_angles
        # Tetrahedral angle ~ 109.5°
        assert 108 < ref.bond_angles['H-C-H'] < 111
    
    def test_unknown_molecule(self):
        """Test unknown molecule returns None."""
        ref = get_molecule_geometry('UnknownMolecule123')
        
        assert ref is None
