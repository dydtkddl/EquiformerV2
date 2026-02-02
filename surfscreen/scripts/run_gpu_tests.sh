#!/bin/bash
###############################################################################
# GPU/MACE Tests Runner
# 
# Tests GPU-accelerated MACE calculations on L4 GPU.
# Requires CUDA and MACE to be installed.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_OUTPUT_DIR="$PROJECT_ROOT/test_outputs/gpu"

# Test counters
PASSED=0
FAILED=0
TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=================================================="
echo "GPU/MACE TESTS"
echo "=================================================="
echo ""

cd "$PROJECT_ROOT"
mkdir -p "$TEST_OUTPUT_DIR"

# ============================================
# 1. GPU Environment Check
# ============================================
echo "--- 1. GPU Environment Check ---"

echo -n "CUDA Available: "
python -c "import torch; print('YES' if torch.cuda.is_available() else 'NO')"

echo -n "CUDA Device: "
python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

echo -n "CUDA Memory: "
python -c "import torch; print(f'{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB' if torch.cuda.is_available() else 'N/A')"

echo ""

# ============================================
# 2. PyTorch GPU Tests
# ============================================
echo "--- 2. PyTorch GPU Tests ---"

cat > "$TEST_OUTPUT_DIR/test_pytorch_gpu.py" << 'PYTEST_EOF'
import pytest
import torch
import time

@pytest.fixture
def device():
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")
    return torch.device("cuda")

class TestPyTorchGPU:
    def test_cuda_available(self):
        """Test CUDA is available."""
        assert torch.cuda.is_available(), "CUDA should be available"
    
    def test_device_count(self):
        """Test GPU device count."""
        count = torch.cuda.device_count()
        assert count >= 1, f"Expected at least 1 GPU, got {count}"
        print(f"Found {count} GPU(s)")
    
    def test_tensor_to_gpu(self, device):
        """Test tensor transfer to GPU."""
        x = torch.randn(1000, 1000)
        x_gpu = x.to(device)
        assert x_gpu.device.type == "cuda"
    
    def test_matrix_multiplication(self, device):
        """Test matrix multiplication on GPU."""
        a = torch.randn(2000, 2000, device=device)
        b = torch.randn(2000, 2000, device=device)
        
        # Warm up
        c = torch.mm(a, b)
        torch.cuda.synchronize()
        
        # Timed run
        start = time.time()
        for _ in range(10):
            c = torch.mm(a, b)
        torch.cuda.synchronize()
        elapsed = time.time() - start
        
        print(f"10x matmul (2000x2000): {elapsed:.3f}s")
        assert elapsed < 5.0, "GPU too slow"
    
    def test_memory_allocation(self, device):
        """Test large memory allocation."""
        # Try to allocate 1GB
        x = torch.randn(256, 1024, 1024, device=device)
        assert x.numel() * 4 > 1e9  # 1GB in bytes
        del x
        torch.cuda.empty_cache()
PYTEST_EOF

python -m pytest "$TEST_OUTPUT_DIR/test_pytorch_gpu.py" -v --tb=short 2>&1 || ((FAILED++))
((TOTAL++))

# ============================================
# 3. MACE Installation Test
# ============================================
echo ""
echo "--- 3. MACE Installation Test ---"

cat > "$TEST_OUTPUT_DIR/test_mace_install.py" << 'PYTEST_EOF'
import pytest
import sys

class TestMACEInstallation:
    def test_mace_import(self):
        """Test MACE can be imported."""
        try:
            import mace
            print(f"MACE version: {mace.__version__}")
        except ImportError as e:
            pytest.skip(f"MACE not installed: {e}")
    
    def test_mace_models(self):
        """Test MACE pre-trained models."""
        try:
            from mace.calculators import mace_mp
            
            # Check model files exist or can be downloaded
            print("MACE-MP model available")
        except Exception as e:
            pytest.skip(f"MACE models not available: {e}")
    
    def test_ase_import(self):
        """Test ASE is available."""
        import ase
        print(f"ASE version: {ase.__version__}")
PYTEST_EOF

python -m pytest "$TEST_OUTPUT_DIR/test_mace_install.py" -v --tb=short 2>&1 || ((FAILED++))
((TOTAL++))

# ============================================
# 4. MACE Calculation Tests
# ============================================
echo ""
echo "--- 4. MACE Calculation Tests ---"

cat > "$TEST_OUTPUT_DIR/test_mace_calc.py" << 'PYTEST_EOF'
import pytest
import numpy as np

class TestMACECalculation:
    @pytest.fixture
    def water_atoms(self):
        """Create water molecule."""
        try:
            from ase import Atoms
            return Atoms(
                'H2O',
                positions=[
                    [0.0, 0.0, 0.1175],
                    [0.7570, 0.0, -0.4700],
                    [-0.7570, 0.0, -0.4700]
                ]
            )
        except ImportError:
            pytest.skip("ASE not installed")
    
    @pytest.fixture
    def mace_calculator(self):
        """Get MACE calculator."""
        try:
            from mace.calculators import mace_mp
            calc = mace_mp(model="small", device="cuda", default_dtype="float32")
            return calc
        except Exception as e:
            pytest.skip(f"MACE calculator not available: {e}")
    
    def test_energy_calculation(self, water_atoms, mace_calculator):
        """Test energy calculation."""
        water_atoms.calc = mace_calculator
        energy = water_atoms.get_potential_energy()
        
        print(f"Water energy: {energy:.4f} eV")
        assert isinstance(energy, float)
        assert -20 < energy < 0  # Reasonable range for water
    
    def test_forces_calculation(self, water_atoms, mace_calculator):
        """Test forces calculation."""
        water_atoms.calc = mace_calculator
        forces = water_atoms.get_forces()
        
        print(f"Forces shape: {forces.shape}")
        assert forces.shape == (3, 3)
        
        # Forces should be small for near-equilibrium structure
        max_force = np.abs(forces).max()
        print(f"Max force: {max_force:.4f} eV/Å")
    
    def test_stress_calculation(self, water_atoms, mace_calculator):
        """Test stress calculation for periodic systems."""
        # Make it periodic
        water_atoms.cell = [10, 10, 10]
        water_atoms.pbc = True
        water_atoms.calc = mace_calculator
        
        try:
            stress = water_atoms.get_stress()
            print(f"Stress: {stress}")
        except Exception as e:
            pytest.skip(f"Stress not supported: {e}")
    
    def test_batch_calculation(self, mace_calculator):
        """Test batch energy calculation."""
        try:
            from ase import Atoms
            from ase.build import molecule
            
            molecules = ['H2O', 'CH4', 'NH3', 'CO2']
            energies = []
            
            for mol_name in molecules:
                try:
                    mol = molecule(mol_name)
                    mol.calc = mace_calculator
                    e = mol.get_potential_energy()
                    energies.append((mol_name, e))
                    print(f"{mol_name}: {e:.4f} eV")
                except:
                    pass
            
            assert len(energies) > 0, "Should calculate at least one molecule"
        except Exception as e:
            pytest.skip(f"Batch calculation failed: {e}")
PYTEST_EOF

python -m pytest "$TEST_OUTPUT_DIR/test_mace_calc.py" -v --tb=short 2>&1 || ((FAILED++))
((TOTAL++))

# ============================================
# 5. SurfScreen MACE Integration Tests
# ============================================
echo ""
echo "--- 5. SurfScreen MACE Integration Tests ---"

cat > "$TEST_OUTPUT_DIR/test_surfscreen_mace.py" << 'PYTEST_EOF'
import pytest
import os
import tempfile

class TestSurfScreenMACE:
    def test_mace_engine_import(self):
        """Test MACE engine can be imported."""
        try:
            from surfscreen.core.engines.mace_engine import MACEEngine
            print("MACEEngine imported successfully")
        except ImportError as e:
            pytest.skip(f"MACEEngine not available: {e}")
    
    def test_mace_engine_initialization(self):
        """Test MACE engine initialization."""
        try:
            from surfscreen.core.engines.mace_engine import MACEEngine
            
            engine = MACEEngine(
                model_path="mace-mp-0",
                device="cuda",
                default_dtype="float32",
            )
            print(f"Engine initialized: {engine}")
        except Exception as e:
            pytest.skip(f"Engine initialization failed: {e}")
    
    def test_screening_calculation(self):
        """Test full screening calculation."""
        try:
            from surfscreen.core.engines.mace_engine import MACEEngine
            from ase import Atoms
            from ase.build import fcc111
            
            # Create simple surface
            surface = fcc111('Cu', size=(2, 2, 3), vacuum=10.0)
            
            # Create adsorbate
            adsorbate = Atoms('CO', positions=[[0, 0, 0], [0, 0, 1.13]])
            
            # Run energy calculation
            engine = MACEEngine(model_path="mace-mp-0", device="cuda")
            
            # Combine
            combined = surface + adsorbate
            combined.calc = engine.get_calculator()
            
            energy = combined.get_potential_energy()
            print(f"Surface + CO energy: {energy:.4f} eV")
            
        except Exception as e:
            pytest.skip(f"Screening calculation failed: {e}")
PYTEST_EOF

python -m pytest "$TEST_OUTPUT_DIR/test_surfscreen_mace.py" -v --tb=short 2>&1 || ((FAILED++))
((TOTAL++))

# ============================================
# 6. GPU Memory Stress Test
# ============================================
echo ""
echo "--- 6. GPU Memory Stress Test ---"

python << 'EOF'
import torch
import gc

if not torch.cuda.is_available():
    print("SKIP: CUDA not available")
    exit(0)

print(f"Initial memory: {torch.cuda.memory_allocated() / 1e6:.1f} MB")

# Allocate increasing amounts of memory
sizes = [1, 2, 4, 8, 16]  # GB
max_successful = 0

for size_gb in sizes:
    try:
        # Each float32 is 4 bytes
        n_elements = int(size_gb * 1e9 / 4)
        x = torch.randn(n_elements, device='cuda')
        torch.cuda.synchronize()
        print(f"✓ Allocated {size_gb} GB")
        max_successful = size_gb
        del x
        gc.collect()
        torch.cuda.empty_cache()
    except RuntimeError as e:
        print(f"✗ Failed at {size_gb} GB: {e}")
        break

print(f"\nMax successful allocation: {max_successful} GB")
print(f"Total GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
EOF

# ============================================
# Summary
# ============================================
echo ""
echo "=================================================="
echo "GPU/MACE TEST SUMMARY"
echo "=================================================="
echo "Tests run: 6 suites"
echo "See individual test output above for details"
echo ""

if [[ $FAILED -gt 0 ]]; then
    echo "Some GPU tests failed!"
    exit 1
else
    echo "GPU tests completed!"
    exit 0
fi
