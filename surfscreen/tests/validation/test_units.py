"""
Scientific Validation Tests: Unit Conversions

Tests for validating unit conversion accuracy:
- Energy: eV, kJ/mol, kcal/mol, Hartree
- Length: Å, Bohr, nm
- Time: fs, ps, atomic units
- Temperature-Energy: K, eV
"""

import pytest
import numpy as np

from surfscreen.validation import (
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

from surfscreen.validation.units import (
    EV_TO_KJ_MOL,
    EV_TO_KCAL_MOL,
    HARTREE_TO_EV,
    ANGSTROM_TO_BOHR,
    kB_eV_K,
)


class TestEnergyConversions:
    """Test energy unit conversions."""
    
    def test_ev_to_kj_mol(self):
        """Test eV to kJ/mol conversion."""
        # 1 eV = 96.485 kJ/mol
        result = eV_to_kJ_mol(1.0)
        assert np.isclose(result, 96.485, rtol=0.001)
    
    def test_kj_mol_to_ev(self):
        """Test kJ/mol to eV conversion."""
        result = kJ_mol_to_eV(96.485)
        assert np.isclose(result, 1.0, rtol=0.001)
    
    def test_ev_kj_mol_roundtrip(self):
        """Test eV <-> kJ/mol roundtrip."""
        original = 2.5
        result = kJ_mol_to_eV(eV_to_kJ_mol(original))
        assert np.isclose(result, original, rtol=1e-10)
    
    def test_ev_to_kcal_mol(self):
        """Test eV to kcal/mol conversion."""
        # 1 eV = 23.061 kcal/mol
        result = eV_to_kcal_mol(1.0)
        assert np.isclose(result, 23.061, rtol=0.001)
    
    def test_kcal_mol_to_ev(self):
        """Test kcal/mol to eV conversion."""
        result = kcal_mol_to_eV(23.061)
        assert np.isclose(result, 1.0, rtol=0.001)
    
    def test_ev_kcal_mol_roundtrip(self):
        """Test eV <-> kcal/mol roundtrip."""
        original = 0.5
        result = kcal_mol_to_eV(eV_to_kcal_mol(original))
        assert np.isclose(result, original, rtol=1e-10)
    
    def test_ev_to_hartree(self):
        """Test eV to Hartree conversion."""
        # 1 Hartree = 27.211 eV
        result = eV_to_Hartree(27.211)
        assert np.isclose(result, 1.0, rtol=0.001)
    
    def test_hartree_to_ev(self):
        """Test Hartree to eV conversion."""
        result = Hartree_to_eV(1.0)
        assert np.isclose(result, 27.211, rtol=0.001)
    
    def test_ev_hartree_roundtrip(self):
        """Test eV <-> Hartree roundtrip."""
        original = 13.6  # Hydrogen ionization energy
        result = Hartree_to_eV(eV_to_Hartree(original))
        assert np.isclose(result, original, rtol=1e-10)
    
    def test_array_conversion(self):
        """Test array conversion works."""
        energies = np.array([0.0, 1.0, 2.0, 3.0])
        kj = eV_to_kJ_mol(energies)
        ev_back = kJ_mol_to_eV(kj)
        
        assert np.allclose(ev_back, energies, rtol=1e-10)


class TestLengthConversions:
    """Test length unit conversions."""
    
    def test_angstrom_to_bohr(self):
        """Test Å to Bohr conversion."""
        # 1 Å = 1.8897 Bohr
        result = angstrom_to_bohr(1.0)
        assert np.isclose(result, 1.8897, rtol=0.001)
    
    def test_bohr_to_angstrom(self):
        """Test Bohr to Å conversion."""
        # 1 Bohr = 0.5292 Å
        result = bohr_to_angstrom(1.0)
        assert np.isclose(result, 0.5292, rtol=0.001)
    
    def test_angstrom_bohr_roundtrip(self):
        """Test Å <-> Bohr roundtrip."""
        original = 2.556  # Cu-Cu distance
        result = bohr_to_angstrom(angstrom_to_bohr(original))
        assert np.isclose(result, original, rtol=1e-10)
    
    def test_positions_conversion(self):
        """Test position array conversion."""
        positions_angstrom = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            [2.0, 0.0, 0.0],
        ])
        
        positions_bohr = angstrom_to_bohr(positions_angstrom)
        positions_back = bohr_to_angstrom(positions_bohr)
        
        assert np.allclose(positions_back, positions_angstrom, rtol=1e-10)


class TestTemperatureEnergyConversions:
    """Test temperature-energy conversions."""
    
    def test_room_temperature(self):
        """Test thermal energy at room temperature (300K)."""
        T = 300.0
        energy = K_to_eV(T)
        
        # kT at 300K ~ 0.0258 eV (25.8 meV)
        assert np.isclose(energy, 0.0258, rtol=0.01)
    
    def test_ev_to_temperature(self):
        """Test energy to temperature conversion."""
        energy = 0.0258  # eV
        T = eV_to_K(energy)
        
        assert np.isclose(T, 300, rtol=0.01)
    
    def test_k_ev_roundtrip(self):
        """Test K <-> eV roundtrip."""
        original = 500.0
        result = eV_to_K(K_to_eV(original))
        assert np.isclose(result, original, rtol=1e-10)
    
    def test_boltzmann_constant(self):
        """Test Boltzmann constant value."""
        # kB = 8.617e-5 eV/K
        assert np.isclose(kB_eV_K, 8.617e-5, rtol=0.001)


class TestConversionFactors:
    """Test conversion factor values are correct."""
    
    def test_ev_kj_mol_factor(self):
        """Test eV to kJ/mol factor."""
        # CODATA value: 96.48530749 kJ/mol per eV
        assert np.isclose(EV_TO_KJ_MOL, 96.485, rtol=0.001)
    
    def test_ev_kcal_mol_factor(self):
        """Test eV to kcal/mol factor."""
        # 23.0605 kcal/mol per eV
        assert np.isclose(EV_TO_KCAL_MOL, 23.061, rtol=0.001)
    
    def test_hartree_ev_factor(self):
        """Test Hartree to eV factor."""
        # CODATA value: 27.211386 eV per Hartree
        assert np.isclose(HARTREE_TO_EV, 27.211, rtol=0.001)
    
    def test_angstrom_bohr_factor(self):
        """Test Å to Bohr factor."""
        # 1.8897259886 Bohr per Å
        assert np.isclose(ANGSTROM_TO_BOHR, 1.8897, rtol=0.001)
    
    def test_kj_kcal_consistency(self):
        """Test kJ/mol and kcal/mol are consistent."""
        # 1 cal = 4.184 J exactly
        # eV -> kJ/mol / eV -> kcal/mol should = 4.184
        ratio = EV_TO_KJ_MOL / EV_TO_KCAL_MOL
        assert np.isclose(ratio, 4.184, rtol=0.001)


class TestVerifyAllConversions:
    """Test the comprehensive conversion verification."""
    
    def test_all_conversions_pass(self):
        """Test that all standard conversions pass verification."""
        results = verify_all_conversions()
        
        for name, passed in results.items():
            assert passed, f"Conversion {name} failed roundtrip verification"
    
    def test_conversion_count(self):
        """Test that we verify a reasonable number of conversions."""
        results = verify_all_conversions()
        
        # Should have at least 8 conversions
        assert len(results) >= 8


class TestChemicallyRelevantValues:
    """Test conversions with chemically relevant values."""
    
    def test_co_adsorption_energy(self):
        """Test CO adsorption energy conversion."""
        E_ads_eV = -0.57  # CO on Cu(111)
        
        E_ads_kJ = eV_to_kJ_mol(E_ads_eV)
        E_ads_kcal = eV_to_kcal_mol(E_ads_eV)
        
        # Should be around -55 kJ/mol, -13 kcal/mol
        assert -60 < E_ads_kJ < -50
        assert -15 < E_ads_kcal < -10
    
    def test_hydrogen_bond(self):
        """Test hydrogen bond energy conversion."""
        E_hbond_kJ = -20.0  # Typical H-bond in kJ/mol
        
        E_hbond_eV = kJ_mol_to_eV(E_hbond_kJ)
        
        # Should be around -0.2 eV
        assert -0.25 < E_hbond_eV < -0.15
    
    def test_activation_energy(self):
        """Test activation energy conversion."""
        Ea_kcal = 10.0  # Typical activation energy in kcal/mol
        
        Ea_eV = kcal_mol_to_eV(Ea_kcal)
        
        # Should be around 0.43 eV
        assert 0.4 < Ea_eV < 0.5
    
    def test_bond_length(self):
        """Test bond length conversion."""
        r_CO_angstrom = 1.128  # C-O bond in Å
        
        r_CO_bohr = angstrom_to_bohr(r_CO_angstrom)
        
        # Should be around 2.13 Bohr
        assert 2.0 < r_CO_bohr < 2.3
