# SurfScreen Developer Guide

Technical documentation for developers contributing to SurfScreen.

## Project Structure

```
surfscreen/
├── src/surfscreen/          # Main package
│   ├── api/                 # REST API (FastAPI)
│   │   ├── main.py          # API entry point
│   │   ├── models.py        # Pydantic models
│   │   ├── dependencies.py  # Auth & DI
│   │   └── routers/         # API endpoints
│   ├── analysis/            # Trajectory analysis
│   │   └── dynamics.py      # MSD, RDF, diffusion
│   ├── calculators/         # Calculator abstraction
│   │   ├── base.py          # Base calculator
│   │   ├── mace_calc.py     # MACE wrapper
│   │   └── xtb_calc.py      # xTB wrapper
│   ├── cli/                 # CLI commands
│   ├── molecule/            # Molecule handling
│   ├── surface/             # Surface handling
│   ├── md/                  # MD simulation
│   ├── screener/           # Screening logic
│   ├── validation/          # Scientific validation
│   └── visualization/       # Plotting
├── dashboard/               # Web frontend (Next.js)
│   ├── src/
│   │   ├── app/             # Pages (App Router)
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   └── lib/             # Utilities
│   └── e2e/                 # Playwright tests
├── tests/                   # Python tests
│   ├── integration/         # API integration tests
│   └── validation/          # Scientific validation tests
├── docs/                    # Documentation
├── Dockerfile.api           # API container
├── Dockerfile.dashboard     # Dashboard container
└── docker-compose.yml       # Container orchestration
```

## Development Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Git

### Local Setup

```bash
# Clone repository
git clone https://github.com/your-org/surfscreen.git
cd surfscreen

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install package in development mode
pip install -e ".[dev,test]"

# Install dashboard dependencies
cd dashboard
npm install
```

### Development Server

```bash
# Terminal 1: API server
cd surfscreen
uvicorn surfscreen.api.main:app --reload

# Terminal 2: Dashboard
cd surfscreen/dashboard
npm run dev
```

## Adding a New Calculator

### 1. Create Calculator Class

```python
# src/surfscreen/calculators/new_calc.py
from .base import BaseCalculator

class NewCalculator(BaseCalculator):
    """New calculator implementation."""

    name = "new_calc"

    def __init__(self, device: str = "cpu", **kwargs):
        super().__init__(device=device)
        self._setup_calculator(**kwargs)

    def _setup_calculator(self, **kwargs):
        # Initialize your calculator here
        pass

    def calculate(self, atoms):
        """Calculate energy and forces."""
        # Implementation
        return {
            "energy": energy,
            "forces": forces,
        }

    def optimize(self, atoms, fmax: float = 0.05):
        """Geometry optimization."""
        # Implementation
        return optimized_atoms
```

### 2. Register Calculator

```python
# src/surfscreen/calculators/__init__.py
from .new_calc import NewCalculator

CALCULATORS = {
    "emt": EMTCalculator,
    "mace": MACECalculator,
    "xtb": XTBCalculator,
    "new_calc": NewCalculator,  # Add here
}
```

### 3. Add CLI Option

```python
# src/surfscreen/cli/screen.py
@click.option("--engine", type=click.Choice(["emt", "mace", "xtb", "new_calc"]))
```

### 4. Add Tests

```python
# tests/test_calculators.py
def test_new_calculator():
    from surfscreen.calculators import NewCalculator
    calc = NewCalculator()
    # Add tests
```

## Adding API Endpoints

### 1. Create Router

```python
# src/surfscreen/api/routers/new_feature.py
from fastapi import APIRouter, Depends
from ..dependencies import require_api_key

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.get("/")
async def list_items(api_key: str = Depends(require_api_key)):
    return {"items": []}

@router.post("/")
async def create_item(data: ItemCreate, api_key: str = Depends(require_api_key)):
    return {"id": "new-id"}
```

### 2. Register Router

```python
# src/surfscreen/api/main.py
from .routers import new_feature

app.include_router(new_feature.router, prefix="/api/v1")
```

### 3. Add Tests

```python
# tests/integration/test_new_feature.py
def test_new_feature_endpoint(api_client, auth_headers):
    response = api_client.get("/api/v1/new-feature/", headers=auth_headers)
    assert response.status_code == 200
```

## Testing

### Run All Tests

```bash
# Python tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/surfscreen --cov-report=html

# Skip slow tests
pytest tests/ -m "not slow"

# Run specific markers
pytest tests/ -m integration
pytest tests/ -m validation
```

### Dashboard Tests

```bash
cd dashboard

# Unit tests
npm test

# E2E tests
npx playwright test

# With UI
npx playwright test --ui
```

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Use Ruff for linting

```bash
# Format
ruff format src/

# Lint
ruff check src/
```

### TypeScript

- Follow ESLint config
- Use TypeScript strictly

```bash
cd dashboard
npm run lint
npm run type-check
```

## Git Workflow

### Branches

- `main`: Production-ready
- `develop`: Development branch
- `feature/*`: New features
- `fix/*`: Bug fixes

### Commit Messages

```
type(scope): description

feat(api): add new endpoint for batch processing
fix(md): correct energy conservation check
docs(readme): update installation instructions
test(validation): add unit tests for physics module
```

## Release Process

### 1. Update Version

```python
# src/surfscreen/__init__.py
__version__ = "0.9.0"
```

### 2. Update Changelog

```markdown
# CHANGELOG.md

## [0.9.0] - 2026-02-02

### Added

- New feature X

### Fixed

- Bug Y
```

### 3. Create Tag

```bash
git tag -a v0.9.0 -m "Release 0.9.0"
git push origin v0.9.0
```

### 4. Build Docker Images

```bash
docker build -f Dockerfile.api -t surfscreen-api:0.9.0 .
docker build -f Dockerfile.dashboard -t surfscreen-dashboard:0.9.0 ./dashboard
```

## Architecture Decisions

### Why FastAPI?

- Async support for I/O-bound operations
- Automatic OpenAPI documentation
- Pydantic validation
- Easy testing with TestClient

### Why Next.js?

- Server-side rendering for SEO
- App Router for modern patterns
- TypeScript support
- Easy deployment

### Why ASE?

- Industry standard for atomistic simulations
- Calculator abstraction
- Trajectory format support
- Many utilities (optimization, MD, etc.)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run linting and tests
5. Submit pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.
