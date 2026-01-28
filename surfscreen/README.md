# SurfScreen

Enterprise-grade surface adsorption screening platform using MACE MLIP.

## Installation

```bash
cd surfscreen
pip install -e ".[mace]"
```

## Quick Start

### 1. Create Molecule

```bash
# From SMILES
surfscreen molecule from-smiles "CCO" -o ethanol.xyz

# From PubChem
surfscreen molecule from-pubchem 2244 --by cid -o aspirin.xyz
surfscreen molecule from-pubchem acetone --by name -o acetone.xyz
```

### 2. Create Surface

```bash
surfscreen surface create Cu --miller 111 --supercell 3x3x1 -o cu111.xyz
surfscreen surface create Pt --miller 100 --supercell 4x4x1 -o pt100.xyz
```

### 3. Run Screening

```bash
surfscreen screen run -s cu111.xyz -m ethanol.xyz --engine mace --device cuda
```

### 4. Generate Report

```bash
surfscreen screen report screening_results/ethanol -o report.html
```

## CPU Thread Control

By default, SurfScreen uses 80% of available CPUs. To control:

```bash
# Option 1: CLI argument
surfscreen screen run -s cu111.xyz -m mol.xyz --ncpus 8

# Option 2: Environment variable (RECOMMENDED - set before run)
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
surfscreen screen run -s cu111.xyz -m mol.xyz
```

## Python API

```python
from surfscreen import MoleculeBuilder, SurfaceBuilder
from surfscreen.adsorption import AdsorptionSystem
from surfscreen.calculator import CalculatorFactory

# Create molecule and surface
mol = MoleculeBuilder.from_smiles("CCO")
surf = SurfaceBuilder.from_element("Cu", (1,1,1), layers=4)

# Run screening
system = AdsorptionSystem(surf, mol)
configs = system.generate_configurations()

calc = CalculatorFactory.create("mace", device="cuda")
results = system.optimize_all(calc)
```

## License

MIT
