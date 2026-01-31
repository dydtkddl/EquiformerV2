# SurfScreen v0.3.0

Enterprise-grade surface adsorption screening platform using MACE MLIP.

## Installation

```bash
cd surfscreen
pip install -e ".[mace]"

# Optional dependencies
pip install pandas openpyxl  # Excel export
pip install mp-api           # Materials Project integration
pip install pyyaml           # Workflow templates
```

## ✨ New in v0.3.0

- 📦 **Export**: CSV, JSON, Excel, ZIP 다중 포맷 내보내기
- 💾 **Checkpoint**: 대규모 작업 중단/재개 지원
- 📝 **Templates**: 워크플로우 템플릿 시스템
- 🔗 **Materials Project**: MP API 연동 표면 생성
- 🔊 **Phonon Analysis**: 진동 분석, ZPE, Gibbs 자유에너지
- 📏 **Coverage Analysis**: 표면 피복도 분석
- 🔢 **Multi-molecule**: 다중 분자 순차 스크리닝

## Quick Start

### 1. Create Molecule

```bash
# From SMILES
surfscreen molecule from-smiles "CCO" -o ethanol.xyz

# From PubChem
surfscreen molecule from-pubchem acetone --by name -o acetone.xyz
```

### 2. Create Surface

```bash
# From element
surfscreen surface create Cu --miller 111 --supercell 3x3x1 -o cu111.xyz

# From Materials Project
surfscreen surface from-mp mp-30 --miller 111 --layers 4 -o cu111_mp.xyz
```

### 3. Run Screening

```bash
# Single molecule
surfscreen screen run -s cu111.xyz -m ethanol.xyz --engine mace --device cuda

# Multiple molecules
surfscreen screen multi -s cu111.xyz -m mol1.xyz -m mol2.xyz -o results/
```

### 4. Generate Report

```bash
surfscreen screen report screening_results/ethanol -o report.html
```

### 5. Export Results

```bash
surfscreen export csv results/ -o results.csv
surfscreen export excel results/ -o results.xlsx
surfscreen export zip results/ -o results.zip
```

## Checkpoint & Resume

```bash
# Check status
surfscreen checkpoint status results/

# Reset failed tasks
surfscreen checkpoint reset-failed results/

# Resume screening (automatic with existing checkpoint)
surfscreen screen run -s surf.xyz -m mol.xyz -o results/ --resume
```

## Workflow Templates

```bash
# Install default templates
surfscreen template install-defaults

# List templates
surfscreen template list

# Run template
surfscreen template run basic_screening -v element=Cu -v molecule=acetone

# Dry-run (preview commands)
surfscreen template run md_simulation --dry-run
```

## Analysis Features

```bash
# MSD & Diffusion
surfscreen analysis msd trajectory.traj -o msd.html

# RDF
surfscreen analysis rdf trajectory.traj --pair Cu-O -o rdf.html

# Boltzmann Distribution
surfscreen analysis boltzmann results/ -T 300 -o boltzmann.html

# Coverage Analysis
surfscreen analysis coverage structure.xyz --n-surface 36

# Phonon & Gibbs Free Energy
surfscreen analysis phonon structure.xyz --engine xtb
surfscreen analysis gibbs structure.xyz -T 298.15
```

## CPU Thread Control

By default, SurfScreen uses 80% of available CPUs.

```bash
# Option 1: CLI argument
surfscreen screen run -s cu111.xyz -m mol.xyz --ncpus 8

# Option 2: Environment variable
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
```

## Python API

```python
from surfscreen import (
    MoleculeBuilder, SurfaceBuilder,
    ExportManager, CheckpointManager,
    TemplateEngine, PhononAnalyzer
)
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

# Export results
exporter = ExportManager("results/")
exporter.to_excel("results.xlsx")
exporter.to_zip("archive.zip")
```

## Documentation

Full documentation: [docs/index.html](docs/index.html)

## License

MIT
