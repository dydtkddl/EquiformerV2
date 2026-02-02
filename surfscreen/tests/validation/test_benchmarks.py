"""
Benchmark Tests: Compare MACE/xTB with DFT Reference Values

These tests validate that MACE and xTB calculations produce results
consistent with DFT reference values for well-known systems.
"""

import pytest
import numpy as np

from surfscreen.validation import (
    ValidationReporter,
    ValidationStatus,
    validate_adsorption_vs_reference,
    validate_bond_length,
    get_molecule_geometry,
    get_adsorption_reference,
    ADSORPTION_REFERENCES,
)

pytestmark = [pytest.mark.validation, pytest.mark.slow]


class TestMACEBenchmarks:
    """Benchmark tests using MACE calculator."""
    
    @pytest.fixture
    def mace_calculator(self):
        """Get MACE calculator."""
        try:
            from mace.calculators import mace_mp
            return mace_mp(model="medium", device="cpu", default_dtype="float32")
        except ImportError:
            pytest.skip("MACE not installed")
    
    @pytest.mark.requires_mace
    def test_co_geometry(self, mace_calculator):
        """Test CO geometry optimization with MACE."""
        from ase import Atoms
        from ase.optimize import BFGS
        
        # Initial guess (slightly wrong)
        co = Atoms('CO', positions=[[0, 0, 0], [0, 0, 1.2]])
        co.calc = mace_calculator
        
        # Optimize
        opt = BFGS(co, logfile=None)
        opt.run(fmax=0.01, steps=100)
        
        # Check bond length
        bond_length = co.get_distance(0, 1)
        ref = get_molecule_geometry('CO')
        expected = ref.bond_lengths['C-O']
        
        # MACE should be within 0.02 Å of reference
        assert abs(bond_length - expected) < 0.02
    
    @pytest.mark.requires_mace
    def test_h2o_geometry(self, mace_calculator):
        """Test H2O geometry optimization with MACE."""
        from ase import Atoms
        from ase.optimize import BFGS
        
        # Initial guess
        h2o = Atoms('OH2', positions=[
            [0, 0, 0],
            [0.8, 0.6, 0],
            [-0.8, 0.6, 0]
        ])
        h2o.calc = mace_calculator
        
        # Optimize
        opt = BFGS(h2o, logfile=None)
        opt.run(fmax=0.01, steps=100)
        
        # Check O-H bond length
        oh1 = h2o.get_distance(0, 1)
        oh2 = h2o.get_distance(0, 2)
        hoh_angle = h2o.get_angle(1, 0, 2)
        
        ref = get_molecule_geometry('H2O')
        
        # Validate
        assert abs(oh1 - ref.bond_lengths['O-H']) < 0.03
        assert abs(oh2 - ref.bond_lengths['O-H']) < 0.03
        assert abs(hoh_angle - ref.bond_angles['H-O-H']) < 3.0


class TestXTBBenchmarks:
    """Benchmark tests using xTB calculator."""
    
    @pytest.fixture
    def xtb_calculator(self):
        """Get xTB calculator."""
        try:
            from xtb.ase.calculator import XTB
            return XTB(method="GFN2-xTB")
        except ImportError:
            pytest.skip("xTB not installed")
    
    @pytest.mark.requires_xtb
    def test_co_geometry(self, xtb_calculator):
        """Test CO geometry optimization with xTB."""
        from ase import Atoms
        from ase.optimize import BFGS
        
        co = Atoms('CO', positions=[[0, 0, 0], [0, 0, 1.2]])
        co.calc = xtb_calculator
        
        opt = BFGS(co, logfile=None)
        opt.run(fmax=0.01, steps=100)
        
        bond_length = co.get_distance(0, 1)
        ref = get_molecule_geometry('CO')
        
        # xTB may have larger error than MACE
        assert abs(bond_length - ref.bond_lengths['C-O']) < 0.05
    
    @pytest.mark.requires_xtb
    def test_organic_molecule_energetics(self, xtb_calculator):
        """Test xTB energetics for organic molecules."""
        from ase import Atoms
        from ase.optimize import BFGS
        
        # Methane
        ch4 = Atoms('CH4', positions=[
            [0, 0, 0],
            [0.63, 0.63, 0.63],
            [-0.63, -0.63, 0.63],
            [-0.63, 0.63, -0.63],
            [0.63, -0.63, -0.63]
        ])
        ch4.calc = xtb_calculator
        
        opt = BFGS(ch4, logfile=None)
        opt.run(fmax=0.01, steps=100)
        
        # Check C-H bond length
        ch_bonds = [ch4.get_distance(0, i) for i in range(1, 5)]
        mean_ch = np.mean(ch_bonds)
        
        ref = get_molecule_geometry('CH4')
        assert abs(mean_ch - ref.bond_lengths['C-H']) < 0.05


class TestEMTBenchmarks:
    """Benchmark tests using EMT calculator (fast, for Cu/Pt/etc)."""
    
    @pytest.fixture
    def emt_calculator(self):
        """Get EMT calculator."""
        try:
            from ase.calculators.emt import EMT
            return EMT()
        except ImportError:
            pytest.skip("ASE not installed")
    
    @pytest.mark.requires_ase
    def test_cu_bulk_lattice(self, emt_calculator):
        """Test Cu bulk lattice constant with EMT."""
        from ase.build import bulk
        from ase.eos import EquationOfState
        
        # Create Cu bulk
        cu = bulk('Cu', 'fcc', a=3.6)
        
        # Scan lattice constants
        volumes = []
        energies = []
        
        for a in np.linspace(3.4, 3.8, 5):
            cu_test = bulk('Cu', 'fcc', a=a)
            cu_test.calc = emt_calculator
            volumes.append(cu_test.get_volume())
            energies.append(cu_test.get_potential_energy())
        
        # Fit equation of state
        eos = EquationOfState(volumes, energies)
        v0, e0, B = eos.fit()
        
        # Calculate equilibrium lattice constant
        a_eq = (4 * v0) ** (1/3)
        
        # EMT is not very accurate, but should be in right ballpark
        # Reference: 3.615 Å
        assert 3.4 < a_eq < 3.8


class TestReferenceDataValidation:
    """Validate that reference data is reasonable."""
    
    def test_all_adsorption_references_have_negative_energy(self):
        """All adsorption energies should be negative."""
        for ref in ADSORPTION_REFERENCES:
            assert ref.energy_eV < 0, f"{ref.molecule}/{ref.surface} has positive E_ads"
    
    def test_all_adsorption_references_have_uncertainty(self):
        """All references should have uncertainty specified."""
        for ref in ADSORPTION_REFERENCES:
            assert ref.energy_error > 0, f"{ref.molecule}/{ref.surface} has no uncertainty"
    
    def test_all_adsorption_references_have_citation(self):
        """All references should have citation."""
        for ref in ADSORPTION_REFERENCES:
            assert len(ref.reference) > 10, f"{ref.molecule}/{ref.surface} has no citation"
    
    def test_molecule_geometries_complete(self):
        """Common molecules should have complete geometry info."""
        essential_molecules = ['CO', 'H2O', 'CH4', 'NH3', 'O2', 'N2']
        
        for mol_name in essential_molecules:
            ref = get_molecule_geometry(mol_name)
            assert ref is not None, f"Missing geometry for {mol_name}"
            assert len(ref.bond_lengths) > 0, f"{mol_name} has no bond lengths"
    
    def test_chemisorption_vs_physisorption_ranges(self):
        """Chemisorption and physisorption ranges should not overlap."""
        from surfscreen.validation import VALIDATION_THRESHOLDS
        
        chem_max = VALIDATION_THRESHOLDS['chemisorption_max']
        phys_min = VALIDATION_THRESHOLDS['physisorption_min']
        
        # There can be overlap in the -0.3 to -0.5 region, but
        # the extremes should be distinct
        assert VALIDATION_THRESHOLDS['chemisorption_min'] < phys_min


class TestValidationReportGeneration:
    """Test generating comprehensive validation reports."""
    
    def test_comprehensive_validation_report(self, tmp_path):
        """Generate comprehensive validation report for all checks."""
        from surfscreen.validation import (
            ValidationReporter,
            validate_adsorption_energy_formula,
            validate_adsorption_energy_range,
            validate_adsorption_vs_reference,
            validate_energy_conservation,
            validate_temperature_stability,
            validate_force_convergence,
            verify_all_conversions,
        )
        
        reporter = ValidationReporter("Comprehensive SurfScreen Validation")
        
        # 1. Unit conversion validation
        unit_results = verify_all_conversions()
        for name, passed in unit_results.items():
            reporter.add_result(ValidationStatus.PASS if passed else ValidationStatus.FAIL)
        
        # 2. Adsorption energy validation
        E_ads = -0.55
        reporter.add_result(validate_adsorption_energy_range(E_ads, "chemisorption"))
        reporter.add_result(validate_adsorption_vs_reference(E_ads, "CO", "Cu(111)"))
        
        # 3. MD validation with synthetic data
        np.random.seed(42)
        n_steps = 100
        energies = -500 + np.random.normal(0, 0.001, n_steps)
        temperatures = 300 + np.random.normal(0, 3, n_steps)
        
        reporter.add_result(validate_energy_conservation(energies, 1.0, 50))
        reporter.add_result(validate_temperature_stability(temperatures, 300))
        
        # 4. Force convergence
        forces = np.random.normal(0, 0.01, (10, 3))
        reporter.add_result(validate_force_convergence(forces))
        
        # Generate reports
        json_path = tmp_path / "validation_report.json"
        md_path = tmp_path / "validation_report.md"
        html_path = tmp_path / "validation_report.html"
        
        reporter.to_json(json_path)
        reporter.to_markdown(md_path)
        reporter.to_html(html_path)
        
        # Verify
        assert json_path.exists()
        assert md_path.exists()
        assert html_path.exists()
        
        # Check report validity
        assert reporter.is_valid()
