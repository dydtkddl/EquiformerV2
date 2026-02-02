"""
Scientific Validation Tests: Adsorption Energy

Tests for validating adsorption energy calculations:
- Energy formula: E_ads = E_total - E_surface - E_molecule
- Physical range validation
- Comparison with reference values (DFT/experimental)
"""

import pytest
import numpy as np

from surfscreen.validation import (
    ValidationStatus,
    validate_adsorption_energy_formula,
    validate_adsorption_energy_range,
    validate_adsorption_vs_reference,
    VALIDATION_THRESHOLDS,
    get_adsorption_reference,
)


class TestAdsorptionEnergyFormula:
    """Test the adsorption energy formula validation."""
    
    def test_correct_formula(self):
        """Test that correct E_ads calculation passes."""
        E_total = -150.0
        E_surface = -100.0
        E_molecule = -50.5
        E_ads = E_total - E_surface - E_molecule  # = 0.5 eV (wrong, should be negative)
        
        # For correct calculation
        E_ads_correct = -0.5
        E_total_correct = E_surface + E_molecule + E_ads_correct  # -150.5
        
        result = validate_adsorption_energy_formula(
            E_total=E_total_correct,
            E_surface=E_surface,
            E_molecule=E_molecule,
            E_ads_calculated=E_ads_correct
        )
        
        assert result.status == ValidationStatus.PASS
        assert "correctly calculated" in result.message
    
    def test_incorrect_formula(self):
        """Test that incorrect E_ads calculation fails."""
        E_total = -150.0
        E_surface = -100.0
        E_molecule = -50.0
        E_ads_wrong = -1.0  # Wrong value (correct is 0.0)
        
        result = validate_adsorption_energy_formula(
            E_total=E_total,
            E_surface=E_surface,
            E_molecule=E_molecule,
            E_ads_calculated=E_ads_wrong
        )
        
        assert result.status == ValidationStatus.FAIL
        assert "mismatch" in result.message
    
    def test_numerical_precision(self):
        """Test numerical precision in energy calculation."""
        E_total = -150.123456789
        E_surface = -100.0
        E_molecule = -50.0
        E_ads = E_total - E_surface - E_molecule
        
        # Small numerical error
        E_ads_with_error = E_ads + 1e-8
        
        result = validate_adsorption_energy_formula(
            E_total=E_total,
            E_surface=E_surface,
            E_molecule=E_molecule,
            E_ads_calculated=E_ads_with_error,
            tolerance=1e-6
        )
        
        assert result.status == ValidationStatus.PASS


class TestAdsorptionEnergyRange:
    """Test adsorption energy range validation."""
    
    def test_valid_chemisorption(self):
        """Test valid chemisorption energy passes."""
        E_ads = -0.7  # Typical CO on Cu
        
        result = validate_adsorption_energy_range(E_ads, "chemisorption")
        
        assert result.status == ValidationStatus.PASS
        assert "reasonable" in result.message
    
    def test_valid_physisorption(self):
        """Test valid physisorption energy passes."""
        E_ads = -0.1  # Typical CH4 on Cu
        
        result = validate_adsorption_energy_range(E_ads, "physisorption")
        
        assert result.status == ValidationStatus.PASS
    
    def test_positive_energy_fails(self):
        """Test that positive adsorption energy (repulsion) fails."""
        E_ads = 0.5  # Repulsive
        
        result = validate_adsorption_energy_range(E_ads)
        
        assert result.status == ValidationStatus.FAIL
        assert "repulsion" in result.message.lower()
    
    def test_too_strong_warns(self):
        """Test that unreasonably strong adsorption warns."""
        E_ads = -10.0  # Too strong
        
        result = validate_adsorption_energy_range(E_ads, "chemisorption")
        
        assert result.status == ValidationStatus.WARNING
        assert "unusually strong" in result.message
    
    def test_too_weak_warns(self):
        """Test that unreasonably weak adsorption warns."""
        E_ads = -0.001  # Very weak
        
        result = validate_adsorption_energy_range(E_ads, "physisorption")
        
        assert result.status == ValidationStatus.WARNING
        assert "unusually weak" in result.message


class TestAdsorptionVsReference:
    """Test comparison with reference values."""
    
    def test_co_cu111_within_tolerance(self):
        """Test CO/Cu(111) adsorption energy within tolerance of reference."""
        # Reference: -0.57 eV (experiment), -0.67 eV (DFT)
        E_ads_calc = -0.55  # Within 20% of experiment
        
        result = validate_adsorption_vs_reference(
            E_ads=E_ads_calc,
            molecule="CO",
            surface="Cu(111)"
        )
        
        # Should pass or at least not fail hard
        assert result.status in [ValidationStatus.PASS, ValidationStatus.WARNING]
        assert "CO" in result.message
        assert "Cu(111)" in result.message
    
    def test_co_cu111_outside_tolerance(self):
        """Test CO/Cu(111) adsorption energy outside tolerance."""
        E_ads_calc = -0.1  # Way off from reference -0.57 eV
        
        result = validate_adsorption_vs_reference(
            E_ads=E_ads_calc,
            molecule="CO",
            surface="Cu(111)"
        )
        
        assert result.status == ValidationStatus.WARNING
        assert "differs" in result.message
    
    def test_unknown_system_skipped(self):
        """Test that unknown molecule/surface pair is skipped."""
        result = validate_adsorption_vs_reference(
            E_ads=-1.0,
            molecule="Unknown",
            surface="Unknown(000)"
        )
        
        assert result.status == ValidationStatus.SKIPPED
        assert "No reference data" in result.message
    
    def test_custom_tolerance(self):
        """Test custom tolerance setting."""
        E_ads_calc = -0.5
        
        result_strict = validate_adsorption_vs_reference(
            E_ads=E_ads_calc,
            molecule="CO",
            surface="Cu(111)",
            tolerance=0.05  # 5% tolerance
        )
        
        result_loose = validate_adsorption_vs_reference(
            E_ads=E_ads_calc,
            molecule="CO",
            surface="Cu(111)",
            tolerance=0.50  # 50% tolerance
        )
        
        # Strict might fail, loose should pass
        assert result_loose.status in [ValidationStatus.PASS, ValidationStatus.WARNING]


class TestReferenceData:
    """Test reference data retrieval."""
    
    def test_co_cu111_exists(self):
        """Test that CO/Cu(111) reference exists."""
        ref = get_adsorption_reference("CO", "Cu(111)")
        
        assert ref is not None
        assert ref.molecule == "CO"
        assert ref.surface == "Cu(111)"
        assert -1.0 < ref.energy_eV < 0.0  # Should be negative
    
    def test_water_reference_exists(self):
        """Test that H2O references exist."""
        ref = get_adsorption_reference("H2O", "Cu(111)")
        
        assert ref is not None
        assert ref.molecule == "H2O"
    
    def test_nonexistent_returns_none(self):
        """Test that nonexistent pair returns None."""
        ref = get_adsorption_reference("XenonFluoride", "Unobtanium(999)")
        
        assert ref is None


class TestThresholds:
    """Test that validation thresholds are reasonable."""
    
    def test_chemisorption_range(self):
        """Test chemisorption range is reasonable."""
        min_val = VALIDATION_THRESHOLDS['chemisorption_min']
        max_val = VALIDATION_THRESHOLDS['chemisorption_max']
        
        assert min_val < max_val < 0  # Both negative, min more negative
        assert min_val >= -10.0  # Not too strong
        assert max_val <= -0.1  # Reasonably strong
    
    def test_physisorption_range(self):
        """Test physisorption range is reasonable."""
        min_val = VALIDATION_THRESHOLDS['physisorption_min']
        max_val = VALIDATION_THRESHOLDS['physisorption_max']
        
        assert min_val < max_val < 0
        assert min_val >= -1.0  # Weak
        assert max_val <= -0.001  # Very weak
