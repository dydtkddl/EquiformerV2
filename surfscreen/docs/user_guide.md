# SurfScreen User Guide

A comprehensive guide for using SurfScreen for surface adsorption screening and MD simulations.

## Getting Started

### Installation

```bash
# From PyPI
pip install surfscreen

# From source
git clone https://github.com/your-org/surfscreen.git
cd surfscreen
pip install -e ".[all]"
```

### Quick Start

```bash
# Run a screening calculation
surfscreen screen molecule.xyz surface.xyz -o results/

# Run an MD simulation
surfscreen md structure.xyz --temperature 300 --steps 1000

# Start the API server
surfscreen api start

# Open dashboard
# Navigate to http://localhost:3000
```

## Web Dashboard

### Overview

The web dashboard provides a graphical interface for:

- Submitting screening jobs
- Running MD simulations
- Monitoring job status
- Viewing results

### Dashboard Pages

#### Home Dashboard

- **Stats Cards**: Total jobs, running, completed, failed
- **Recent Jobs**: Quick access to recent calculations
- **Server Status**: API connection indicator
- **Quick Actions**: Create new jobs

#### Jobs Page

- View all jobs with filtering and sorting
- Filter by status: Pending, Running, Completed, Failed
- Filter by type: Screening, MD Simulation
- Search by job ID or name

#### Screening Page

- Upload molecule and surface structures
- Configure calculator (EMT, MACE, xTB)
- Set number of configurations to test
- Advanced options: force threshold, optimization steps

#### MD Simulation Page

- Upload initial structure
- Select ensemble: NVT, NVE, NPT
- Set temperature, pressure, timestep, steps
- Choose thermostat: Langevin, Nosé-Hoover

#### Settings Page

- API connection settings
- Theme selection (light/dark)
- Default calculator and device
- Enable/disable real-time updates

## CLI Commands

### Screening

```bash
# Basic screening
surfscreen screen molecule.xyz surface.xyz

# With options
surfscreen screen molecule.xyz surface.xyz \
    --engine mace \
    --n-configs 50 \
    --fmax 0.01 \
    --output results/
```

### MD Simulation

```bash
# NVT simulation
surfscreen md structure.xyz \
    --temperature 300 \
    --timestep 1.0 \
    --steps 10000 \
    --ensemble nvt \
    --output md_output/

# NVE simulation
surfscreen md structure.xyz \
    --ensemble nve \
    --steps 5000
```

### Analysis

```bash
# Calculate MSD
surfscreen analysis msd trajectory.traj --species Li

# Calculate diffusion coefficient
surfscreen analysis diffusion trajectory.traj --species Li

# Calculate RDF
surfscreen analysis rdf trajectory.traj --pair Li-O
```

### Validation

```bash
# Run all validations
surfscreen validate all --output report.html

# Validate unit conversions
surfscreen validate units

# Validate adsorption energy
surfscreen validate adsorption -m CO -s "Cu(111)" -e -0.55
```

## Workflow Examples

### Surface Screening Workflow

1. **Prepare Structures**
   - Molecule: XYZ format (e.g., CO.xyz)
   - Surface: XYZ format (e.g., Cu111.xyz)

2. **Run Screening**

   ```bash
   surfscreen screen CO.xyz Cu111.xyz -n 100 --engine mace
   ```

3. **View Results**
   - Rankings by adsorption energy
   - Optimized geometries
   - Energy distributions

### MD Simulation Workflow

1. **Prepare System**
   - Create adsorption complex
   - Set cell parameters

2. **Run Equilibration**

   ```bash
   surfscreen md system.xyz -T 300 --steps 5000 --ensemble nvt
   ```

3. **Run Production**

   ```bash
   surfscreen md equilibrated.xyz -T 300 --steps 100000 --ensemble nvt
   ```

4. **Analyze Results**
   ```bash
   surfscreen analysis msd trajectory.traj
   surfscreen analysis diffusion trajectory.traj
   ```

## File Formats

### Input Files

| Format       | Extension | Description              |
| ------------ | --------- | ------------------------ |
| XYZ          | .xyz      | Standard XYZ coordinates |
| Extended XYZ | .extxyz   | With cell and properties |
| CIF          | .cif      | Crystallographic format  |
| VASP POSCAR  | POSCAR    | VASP structure format    |
| PDB          | .pdb      | Protein Data Bank        |
| MOL2         | .mol2     | Tripos format            |

### Output Files

| File              | Description                |
| ----------------- | -------------------------- |
| results.json      | Screening results (JSON)   |
| trajectory.traj   | MD trajectory (ASE format) |
| optimized\_\*.xyz | Optimized structures       |
| report.html       | Analysis report            |

### Surface Export Formats

`surfscreen surface create` 명령어는 파일 확장자에 따라 자동으로 형식을 결정합니다:

| Extension | Format       | Use Case                                   |
| --------- | ------------ | ------------------------------------------ |
| .extxyz   | Extended XYZ | **Default**, preserves cell and properties |
| .cif      | CIF          | Crystallographic exchange                  |
| .xyz      | XYZ          | Basic coordinates only                     |
| .pdb      | PDB          | Protein Data Bank format                   |
| .mol2     | MOL2         | Tripos format for molecular modeling       |
| POSCAR    | VASP         | VASP/DFT calculations                      |

## Calculators

### EMT (Effective Medium Theory)

- **Speed**: Very fast
- **Accuracy**: Low (metals only)
- **Use for**: Quick tests, Cu/Ag/Au/Pd/Pt

### MACE-MP

- **Speed**: Moderate
- **Accuracy**: High (DFT-level)
- **Use for**: Production calculations
- **Requires**: PyTorch, MACE package

### xTB

- **Speed**: Fast
- **Accuracy**: Moderate (organic molecules)
- **Use for**: Organic adsorbates
- **Requires**: xTB package

## Tips and Best Practices

### Screening

- Start with fewer configurations (10-20) to test
- Use EMT for quick prototyping
- Switch to MACE for production runs
- Check convergence with fmax < 0.05 eV/Å

### MD Simulations

- Equilibrate before production run
- Use timestep ≤ 1 fs for stable dynamics
- Monitor temperature and energy conservation
- Save trajectory every 10-100 steps

### Performance

- Use GPU (cuda) for MACE when available
- Batch multiple molecules for efficiency
- Use multiprocessing for independent calculations

## Troubleshooting

### Common Issues

**MACE not found**

```bash
pip install mace-torch
```

**xTB not found**

```bash
conda install -c conda-forge xtb
```

**CUDA out of memory**

```bash
# Use smaller model or CPU
surfscreen screen mol.xyz surf.xyz --device cpu
```

**Optimization not converging**

- Increase max steps
- Reduce fmax threshold
- Check for unrealistic structures

## Support

- **Documentation**: https://surfscreen.readthedocs.io
- **Issues**: https://github.com/your-org/surfscreen/issues
- **Email**: surfscreen@example.com
