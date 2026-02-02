"""
End-to-End Integration Test: Complete Screening Workflow

Tests the full screening workflow from structure loading to report generation.
This test validates that all components work together correctly.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import json

# Mark all tests in this module
pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestScreeningWorkflow:
    """Test complete screening workflow."""
    
    @pytest.fixture
    def work_dir(self, tmp_path):
        """Create temporary working directory."""
        return tmp_path
    
    @pytest.fixture
    def cu111_surface(self, work_dir):
        """Create Cu(111) surface file."""
        xyz_content = """12
Cu(111) 2x2 surface, 3 layers
Cu    0.000000    0.000000    0.000000
Cu    2.556000    0.000000    0.000000
Cu    1.278000    2.213000    0.000000
Cu    3.834000    2.213000    0.000000
Cu    0.852000    0.492000    2.087000
Cu    3.408000    0.492000    2.087000
Cu    2.130000    2.705000    2.087000
Cu    4.686000    2.705000    2.087000
Cu    1.704000    0.984000    4.174000
Cu    4.260000    0.984000    4.174000
Cu    2.982000    3.197000    4.174000
Cu    5.538000    3.197000    4.174000
"""
        surface_path = work_dir / "cu111.xyz"
        surface_path.write_text(xyz_content)
        return surface_path
    
    @pytest.fixture
    def co_molecule(self, work_dir):
        """Create CO molecule file."""
        xyz_content = """2
CO molecule
C    0.000000    0.000000    0.000000
O    0.000000    0.000000    1.128000
"""
        mol_path = work_dir / "co.xyz"
        mol_path.write_text(xyz_content)
        return mol_path
    
    @pytest.mark.requires_ase
    def test_structure_loading(self, cu111_surface, co_molecule):
        """Test that structures can be loaded correctly."""
        from ase.io import read
        
        # Load surface
        surface = read(str(cu111_surface))
        assert len(surface) == 12
        assert all(s == 'Cu' for s in surface.get_chemical_symbols())
        
        # Load molecule
        molecule = read(str(co_molecule))
        assert len(molecule) == 2
        assert set(molecule.get_chemical_symbols()) == {'C', 'O'}
    
    @pytest.mark.requires_ase
    def test_adsorption_energy_calculation(self, cu111_surface, co_molecule):
        """Test adsorption energy calculation with EMT (fast calculator)."""
        from ase.io import read
        from ase.calculators.emt import EMT
        
        # Load structures
        surface = read(str(cu111_surface))
        molecule = read(str(co_molecule))
        
        # Calculate isolated energies
        surface.calc = EMT()
        E_surface = surface.get_potential_energy()
        
        molecule.calc = EMT()
        E_molecule = molecule.get_potential_energy()
        
        # Create adsorbed system
        adsorbed = surface.copy()
        mol_copy = molecule.copy()
        # Place molecule above surface
        mol_copy.translate([2.5, 2.5, 6.0])
        adsorbed += mol_copy
        adsorbed.calc = EMT()
        E_total = adsorbed.get_potential_energy()
        
        # Calculate adsorption energy
        E_ads = E_total - E_surface - E_molecule
        
        # Validate: EMT gives qualitative results only
        # For this test, just verify the calculation runs
        assert isinstance(E_ads, float)
        assert not np.isnan(E_ads)
    
    @pytest.mark.requires_ase
    def test_geometry_optimization(self, co_molecule, work_dir):
        """Test geometry optimization."""
        from ase.io import read
        from ase.calculators.emt import EMT
        from ase.optimize import BFGS
        
        molecule = read(str(co_molecule))
        molecule.calc = EMT()
        
        # Optimize
        traj_path = work_dir / "opt.traj"
        opt = BFGS(molecule, trajectory=str(traj_path))
        opt.run(fmax=0.1, steps=50)
        
        # Check convergence
        forces = molecule.get_forces()
        fmax = np.max(np.linalg.norm(forces, axis=1))
        
        # Should have converged or at least reduced forces
        assert fmax < 1.0  # Reasonable force after optimization


class TestMDWorkflow:
    """Test complete MD simulation workflow."""
    
    @pytest.fixture
    def simple_system(self, tmp_path):
        """Create simple system for MD test."""
        xyz_content = """4
Cu cluster
Cu    0.000000    0.000000    0.000000
Cu    2.556000    0.000000    0.000000
Cu    1.278000    2.213000    0.000000
Cu    0.852000    0.738000    2.087000
"""
        path = tmp_path / "cu_cluster.xyz"
        path.write_text(xyz_content)
        return path
    
    @pytest.mark.requires_ase
    def test_md_nvt_simulation(self, simple_system, tmp_path):
        """Test NVT MD simulation."""
        from ase.io import read
        from ase.calculators.emt import EMT
        from ase.md.langevin import Langevin
        from ase import units
        
        atoms = read(str(simple_system))
        atoms.calc = EMT()
        
        # Set up Langevin thermostat
        temperature_K = 300
        dyn = Langevin(
            atoms,
            timestep=1.0 * units.fs,
            temperature_K=temperature_K,
            friction=0.01
        )
        
        # Track energies
        energies = []
        temperatures = []
        
        def record():
            energies.append(atoms.get_potential_energy())
            temperatures.append(atoms.get_temperature())
        
        dyn.attach(record, interval=10)
        
        # Run short simulation
        dyn.run(steps=100)
        
        # Validate
        assert len(energies) > 5
        assert len(temperatures) > 5
        
        # Temperature should fluctuate around target
        mean_temp = np.mean(temperatures[2:])  # Skip initial equilibration
        # Allow large tolerance for short simulation
        assert 50 < mean_temp < 600
    
    @pytest.mark.requires_ase
    def test_energy_conservation_nve(self, simple_system, tmp_path):
        """Test energy conservation in NVE simulation."""
        from ase.io import read
        from ase.calculators.emt import EMT
        from ase.md.verlet import VelocityVerlet
        from ase import units
        from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
        
        atoms = read(str(simple_system))
        atoms.calc = EMT()
        
        # Initialize velocities
        MaxwellBoltzmannDistribution(atoms, temperature_K=300)
        
        # Run NVE
        dyn = VelocityVerlet(atoms, timestep=0.5 * units.fs)
        
        total_energies = []
        
        def record():
            ke = atoms.get_kinetic_energy()
            pe = atoms.get_potential_energy()
            total_energies.append(ke + pe)
        
        dyn.attach(record, interval=5)
        dyn.run(steps=100)
        
        # Check energy conservation
        total_energies = np.array(total_energies)
        energy_std = np.std(total_energies)
        energy_mean = np.mean(total_energies)
        
        # Relative fluctuation should be small
        relative_fluctuation = energy_std / abs(energy_mean)
        assert relative_fluctuation < 0.1  # 10% is acceptable for short run


class TestValidationIntegration:
    """Test validation module integration."""
    
    def test_adsorption_validation_workflow(self):
        """Test complete adsorption energy validation workflow."""
        from surfscreen.validation import (
            ValidationReporter,
            validate_adsorption_energy_formula,
            validate_adsorption_energy_range,
            validate_adsorption_vs_reference,
        )
        
        # Simulated calculation results
        E_total = -150.57
        E_surface = -100.0
        E_molecule = -50.0
        E_ads = E_total - E_surface - E_molecule  # -0.57 eV
        
        # Create reporter
        reporter = ValidationReporter("CO/Cu(111) Adsorption Validation")
        
        # Run validations
        reporter.add_result(validate_adsorption_energy_formula(
            E_total, E_surface, E_molecule, E_ads
        ))
        reporter.add_result(validate_adsorption_energy_range(
            E_ads, "chemisorption"
        ))
        reporter.add_result(validate_adsorption_vs_reference(
            E_ads, "CO", "Cu(111)"
        ))
        
        # Check results
        summary = reporter.get_summary()
        assert summary['FAIL'] == 0
        assert reporter.is_valid()
        
        # Generate reports
        json_report = reporter.to_json()
        assert "CO/Cu(111)" in json_report
        
        md_report = reporter.to_markdown()
        assert "## Summary" in md_report
    
    def test_md_validation_workflow(self):
        """Test complete MD validation workflow."""
        from surfscreen.validation import (
            ValidationReporter,
            validate_energy_conservation,
            validate_temperature_stability,
            validate_boltzmann_distribution,
            PHYSICAL_CONSTANTS,
        )
        
        # Simulated MD results
        n_steps = 1000
        n_atoms = 50
        timestep_fs = 1.0
        target_temp = 300.0
        kB = PHYSICAL_CONSTANTS['kB_eV_K']
        
        np.random.seed(42)
        
        # Generate realistic-looking data
        base_energy = -500.0
        energies = base_energy + np.random.normal(0, 0.01, n_steps)
        temperatures = target_temp + np.random.normal(0, 5, n_steps)
        expected_ke = 1.5 * n_atoms * kB * target_temp
        kinetic_energies = expected_ke + np.random.normal(0, expected_ke * 0.02, n_steps)
        
        # Create reporter
        reporter = ValidationReporter("NVT MD Validation")
        
        # Run validations
        reporter.add_result(validate_energy_conservation(
            energies, timestep_fs, n_atoms
        ))
        reporter.add_result(validate_temperature_stability(
            temperatures, target_temp
        ))
        reporter.add_result(validate_boltzmann_distribution(
            kinetic_energies, target_temp, n_atoms
        ))
        
        # Check results
        assert reporter.is_valid()
        
        # Generate HTML report
        html_report = reporter.to_html()
        assert "<html>" in html_report
        assert "NVT MD Validation" in html_report


class TestReportGeneration:
    """Test report generation with validation results."""
    
    def test_validation_report_export(self, tmp_path):
        """Test exporting validation reports to files."""
        from surfscreen.validation import (
            ValidationReporter,
            validate_adsorption_energy_range,
            validate_force_convergence,
        )
        
        reporter = ValidationReporter("Test Validation Report")
        
        # Add some results
        reporter.add_result(validate_adsorption_energy_range(-0.5, "chemisorption"))
        reporter.add_result(validate_force_convergence(
            np.array([[0.01, 0.01, 0.01], [-0.01, -0.01, -0.01]])
        ))
        
        # Export to files
        json_path = tmp_path / "report.json"
        md_path = tmp_path / "report.md"
        html_path = tmp_path / "report.html"
        
        reporter.to_json(json_path)
        reporter.to_markdown(md_path)
        reporter.to_html(html_path)
        
        # Verify files created
        assert json_path.exists()
        assert md_path.exists()
        assert html_path.exists()
        
        # Verify content
        json_content = json.loads(json_path.read_text())
        assert json_content['is_valid'] == True
        assert json_content['summary']['PASS'] == 2
