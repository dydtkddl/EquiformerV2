"""
Scientific Validation Tests: MD Simulation Physics

Tests for validating MD simulation physics:
- Energy conservation (NVE)
- Temperature stability (NVT)
- Boltzmann distribution verification
"""

import pytest
import numpy as np

from surfscreen.validation import (
    ValidationStatus,
    validate_energy_conservation,
    validate_temperature_stability,
    validate_boltzmann_distribution,
    PHYSICAL_CONSTANTS,
)


class TestEnergyConservation:
    """Test energy conservation validation for NVE MD."""
    
    def test_perfect_conservation(self):
        """Test that perfectly conserved energy passes."""
        n_steps = 1000
        n_atoms = 50
        timestep_fs = 1.0
        
        # Perfect energy conservation (slight random fluctuation)
        base_energy = -500.0
        energies = np.full(n_steps, base_energy)
        
        result = validate_energy_conservation(
            energies=energies,
            timestep_fs=timestep_fs,
            n_atoms=n_atoms
        )
        
        assert result.status == ValidationStatus.PASS
        assert "drift" in result.message.lower()
    
    def test_small_drift_passes(self):
        """Test that small energy drift passes."""
        n_steps = 1000
        n_atoms = 50
        timestep_fs = 1.0
        
        # Small linear drift: 0.0001 eV/step = 0.0001 * 1000 / 1 * 1000 / 50 
        # = 0.001 eV/ps/atom (barely passing)
        base_energy = -500.0
        drift_per_step = 1e-5  # Very small
        energies = base_energy + np.arange(n_steps) * drift_per_step
        
        result = validate_energy_conservation(
            energies=energies,
            timestep_fs=timestep_fs,
            n_atoms=n_atoms,
            threshold=0.001
        )
        
        assert result.status == ValidationStatus.PASS
    
    def test_large_drift_fails(self):
        """Test that large energy drift fails."""
        n_steps = 1000
        n_atoms = 50
        timestep_fs = 1.0
        
        # Large drift
        base_energy = -500.0
        drift_per_step = 0.01  # 1 eV over 1000 steps
        energies = base_energy + np.arange(n_steps) * drift_per_step
        
        result = validate_energy_conservation(
            energies=energies,
            timestep_fs=timestep_fs,
            n_atoms=n_atoms,
            threshold=0.001
        )
        
        assert result.status == ValidationStatus.FAIL
        assert "exceeds" in result.message.lower()
    
    def test_random_fluctuation(self):
        """Test that random fluctuation around mean passes."""
        n_steps = 1000
        n_atoms = 50
        timestep_fs = 1.0
        
        np.random.seed(42)
        base_energy = -500.0
        fluctuation = 0.01  # Small random fluctuation
        energies = base_energy + np.random.normal(0, fluctuation, n_steps)
        
        result = validate_energy_conservation(
            energies=energies,
            timestep_fs=timestep_fs,
            n_atoms=n_atoms
        )
        
        # Random fluctuation should not cause significant drift
        assert result.status == ValidationStatus.PASS


class TestTemperatureStability:
    """Test temperature stability validation for NVT MD."""
    
    def test_stable_temperature(self):
        """Test that stable temperature passes."""
        n_steps = 1000
        target_temp = 300.0
        
        np.random.seed(42)
        # Temperature fluctuating around target
        temperatures = target_temp + np.random.normal(0, 5, n_steps)
        
        result = validate_temperature_stability(
            temperatures=temperatures,
            target_temperature=target_temp
        )
        
        assert result.status == ValidationStatus.PASS
        assert "300" in result.message or "target" in result.message.lower()
    
    def test_temperature_offset_warns(self):
        """Test that temperature offset triggers warning."""
        n_steps = 1000
        target_temp = 300.0
        
        # Temperature offset by 20K
        temperatures = np.full(n_steps, target_temp + 20)
        
        result = validate_temperature_stability(
            temperatures=temperatures,
            target_temperature=target_temp,
            tolerance=10.0
        )
        
        assert result.status == ValidationStatus.WARNING
        assert "deviates" in result.message.lower()
    
    def test_custom_tolerance(self):
        """Test custom temperature tolerance."""
        n_steps = 1000
        target_temp = 300.0
        
        temperatures = np.full(n_steps, target_temp + 5)
        
        result_strict = validate_temperature_stability(
            temperatures=temperatures,
            target_temperature=target_temp,
            tolerance=3.0
        )
        
        result_loose = validate_temperature_stability(
            temperatures=temperatures,
            target_temperature=target_temp,
            tolerance=10.0
        )
        
        assert result_strict.status == ValidationStatus.WARNING
        assert result_loose.status == ValidationStatus.PASS
    
    def test_high_temperature(self):
        """Test high temperature simulation."""
        n_steps = 500
        target_temp = 1000.0  # High temperature
        
        np.random.seed(42)
        temperatures = target_temp + np.random.normal(0, 15, n_steps)
        
        result = validate_temperature_stability(
            temperatures=temperatures,
            target_temperature=target_temp,
            tolerance=30.0  # Higher tolerance for high T
        )
        
        assert result.status == ValidationStatus.PASS


class TestBoltzmannDistribution:
    """Test Boltzmann distribution validation."""
    
    def test_correct_distribution(self):
        """Test that correct KE distribution passes."""
        n_atoms = 50
        temperature = 300.0
        kB = PHYSICAL_CONSTANTS['kB_eV_K']
        
        expected_ke = 1.5 * n_atoms * kB * temperature
        
        # Kinetic energies fluctuating around expected value
        np.random.seed(42)
        n_samples = 1000
        kinetic_energies = expected_ke + np.random.normal(0, expected_ke * 0.02, n_samples)
        
        result = validate_boltzmann_distribution(
            kinetic_energies=kinetic_energies,
            temperature=temperature,
            n_atoms=n_atoms
        )
        
        assert result.status == ValidationStatus.PASS
        assert "expected" in result.message.lower()
    
    def test_wrong_temperature_warns(self):
        """Test that wrong temperature distribution warns."""
        n_atoms = 50
        temperature = 300.0
        kB = PHYSICAL_CONSTANTS['kB_eV_K']
        
        # KE corresponding to different temperature (600K instead of 300K)
        wrong_ke = 1.5 * n_atoms * kB * 600.0
        kinetic_energies = np.full(1000, wrong_ke)
        
        result = validate_boltzmann_distribution(
            kinetic_energies=kinetic_energies,
            temperature=temperature,
            n_atoms=n_atoms
        )
        
        assert result.status == ValidationStatus.WARNING
        assert "differs" in result.message.lower()
    
    def test_thermodynamic_relation(self):
        """Test thermodynamic relation: KE = 3/2 N kB T."""
        kB = PHYSICAL_CONSTANTS['kB_eV_K']
        
        temperatures = [100, 300, 500, 1000]
        n_atoms_list = [10, 50, 100]
        
        for T in temperatures:
            for N in n_atoms_list:
                expected_ke = 1.5 * N * kB * T
                
                # Verify formula
                ke_per_atom = expected_ke / N
                ke_per_dof = ke_per_atom / 3  # 3 degrees of freedom per atom
                
                assert np.isclose(ke_per_dof, 0.5 * kB * T, rtol=1e-10)


class TestPhysicalConstants:
    """Test physical constants are correct."""
    
    def test_boltzmann_constant(self):
        """Test Boltzmann constant value."""
        kB = PHYSICAL_CONSTANTS['kB_eV_K']
        
        # CODATA 2018 value
        assert np.isclose(kB, 8.617333262e-5, rtol=1e-6)
    
    def test_room_temperature_energy(self):
        """Test thermal energy at room temperature."""
        kB = PHYSICAL_CONSTANTS['kB_eV_K']
        T = 300  # Room temperature in K
        
        thermal_energy = kB * T
        
        # ~25.8 meV at 300K
        assert np.isclose(thermal_energy, 0.0259, rtol=0.01)
    
    def test_ev_to_kj_mol(self):
        """Test eV to kJ/mol conversion."""
        factor = PHYSICAL_CONSTANTS['eV_to_kJ_mol']
        
        # 1 eV = 96.485 kJ/mol
        assert np.isclose(factor, 96.485, rtol=0.001)


class TestMDTimescales:
    """Test MD simulation timescales are reasonable."""
    
    def test_typical_timestep(self):
        """Test typical timestep requirements."""
        # H vibration period ~ 10 fs
        # Timestep should be < 1 fs for accurate H dynamics
        typical_timestep = 1.0  # fs
        h_period = 10.0  # fs (approximate)
        
        # Should have multiple steps per H vibration
        steps_per_period = h_period / typical_timestep
        assert steps_per_period >= 10
    
    def test_equilibration_time(self):
        """Test equilibration time estimation."""
        # Typical equilibration: 1-10 ps
        # With 1 fs timestep: 1000-10000 steps
        timestep = 1.0  # fs
        min_eq_time = 1.0  # ps
        max_eq_time = 10.0  # ps
        
        min_steps = min_eq_time * 1000 / timestep
        max_steps = max_eq_time * 1000 / timestep
        
        assert min_steps == 1000
        assert max_steps == 10000
