# SurfScreen v0.9.0

<div align="center">

![SurfScreen Logo](docs/assets/logo.png)

**Enterprise-grade Surface Adsorption Screening Platform**

[![CI](https://github.com/your-org/surfscreen/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/surfscreen/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Documentation](docs/) | [Quick Start](#quick-start) | [API Reference](docs/api_guide.md) | [Dashboard](#web-dashboard)

</div>

---

## Features

🔬 **Multi-Calculator Support**: EMT, MACE-MP, xTB calculators  
🖥️ **Web Dashboard**: Modern Next.js interface  
🚀 **REST API**: FastAPI with OpenAPI documentation  
📊 **MD Simulation**: NVT/NVE ensembles with analysis  
✅ **Scientific Validation**: Physics-based validation framework  
🐳 **Docker Ready**: Production-ready containers

## Quick Start

### Installation

```bash
# From PyPI
pip install surfscreen

# From source
git clone https://github.com/your-org/surfscreen.git
cd surfscreen
pip install -e ".[all]"
```

### Docker (Recommended)

```bash
# Clone and configure
git clone https://github.com/your-org/surfscreen.git
cd surfscreen
cp .env.example .env

# Start all services
docker-compose up -d

# Open dashboard: http://localhost:3000
# API docs:       http://localhost:8000/docs
```

### Basic Usage

```bash
# Create molecule from SMILES
surfscreen molecule from-smiles "CCO" -o ethanol.xyz

# Create surface
surfscreen surface create Cu --miller 111 --supercell 3x3x1 -o cu111.xyz

# Run screening
surfscreen screen run -s cu111.xyz -m ethanol.xyz --engine mace

# Run MD simulation
surfscreen md structure.xyz --temperature 300 --steps 10000

# Generate report
surfscreen screen report results/ -o report.html
```

## Web Dashboard

### Start Dashboard

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

### Features

- 📊 Real-time job monitoring
- 📁 File upload for structures
- ⚙️ Calculator configuration
- 📈 Result visualization
- 🌙 Dark/Light theme

## REST API

### Start API Server

```bash
surfscreen api start --port 8000
```

### Endpoints

| Endpoint                   | Method | Description          |
| -------------------------- | ------ | -------------------- |
| `/health`                  | GET    | Health check         |
| `/api/v1/jobs`             | GET    | List all jobs        |
| `/api/v1/screening/submit` | POST   | Submit screening job |
| `/api/v1/md/submit`        | POST   | Submit MD job        |

See full API docs at `http://localhost:8000/docs`

## CLI Commands

```bash
# Molecule handling
surfscreen molecule from-smiles "CC=O" -o acetaldehyde.xyz
surfscreen molecule from-pubchem aspirin --by name -o aspirin.xyz

# Surface generation
surfscreen surface create Pt --miller 100 --layers 4 -o pt100.xyz
surfscreen surface from-mp mp-30 --miller 111 -o cu111.xyz

# Screening
surfscreen screen run -s surface.xyz -m molecule.xyz --engine mace
surfscreen screen multi -s surface.xyz -m mol1.xyz -m mol2.xyz

# MD Simulation
surfscreen md structure.xyz -T 300 --steps 10000 --ensemble nvt

# Analysis
surfscreen analysis msd trajectory.traj --species Li
surfscreen analysis rdf trajectory.traj --pair Li-O
surfscreen analysis diffusion trajectory.traj

# Validation
surfscreen validate all --output report.html
surfscreen validate units

# Export
surfscreen export csv results/ -o results.csv
surfscreen export excel results/ -o results.xlsx
```

## Project Structure

```
surfscreen/
├── src/surfscreen/     # Python package
│   ├── api/            # REST API
│   ├── cli/            # CLI commands
│   ├── calculators/    # Calculator backends
│   ├── md/             # MD simulation
│   ├── validation/     # Scientific validation
│   └── ...
├── dashboard/          # Next.js web frontend
├── tests/              # Test suites
├── docs/               # Documentation
├── Dockerfile.api      # API container
├── Dockerfile.dashboard # Dashboard container
└── docker-compose.yml  # Container orchestration
```

## Documentation

- [User Guide](docs/user_guide.md) - Complete usage guide
- [Developer Guide](docs/developer_guide.md) - Contributing guide
- [Deployment Guide](docs/deployment.md) - Production deployment
- [API Reference](docs/api_guide.md) - API documentation
- [Changelog](CHANGELOG.md) - Version history

## Requirements

- Python 3.9+
- Node.js 18+ (for dashboard)
- ASE (Atomic Simulation Environment)
- Optional: MACE, xTB

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
# Setup development environment
pip install -e ".[dev,test]"

# Run tests
pytest tests/ -v

# Run linting
ruff check src/
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Citation

If you use SurfScreen in your research, please cite:

```bibtex
@software{surfscreen,
  title = {SurfScreen: Enterprise Surface Adsorption Screening Platform},
  author = {Your Team},
  year = {2026},
  url = {https://github.com/your-org/surfscreen}
}
```

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/your-org/surfscreen/issues)
- 💬 [Discussions](https://github.com/your-org/surfscreen/discussions)
