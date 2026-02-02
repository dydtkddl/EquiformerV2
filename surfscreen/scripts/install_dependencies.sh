#!/bin/bash
###############################################################################
# SurfScreen Dependencies Installer
# 
# Installs all required packages for running SurfScreen and tests.
# Uses pip only (no conda).
#
# Usage: ./install_dependencies.sh
###############################################################################

set -euo pipefail

echo "=================================================="
echo "SurfScreen Dependencies Installer"
echo "=================================================="
echo ""

# ============================================
# Core Dependencies
# ============================================
echo "Installing core dependencies..."

pip install --upgrade pip

# ASE and scientific computing
pip install \
    ase \
    numpy \
    scipy \
    pandas \
    matplotlib \
    scikit-learn

# ============================================
# MACE and ML
# ============================================
echo "Installing MACE and ML dependencies..."

pip install \
    torch \
    e3nn \
    mace-torch

# ============================================
# API Dependencies
# ============================================
echo "Installing API dependencies..."

pip install \
    fastapi \
    uvicorn[standard] \
    pydantic[email] \
    email-validator \
    python-jose[cryptography] \
    passlib[bcrypt] \
    python-multipart \
    httpx \
    aiohttp \
    aiofiles \
    redis \
    apscheduler

# ============================================
# Testing Dependencies
# ============================================
echo "Installing testing dependencies..."

pip install \
    pytest \
    pytest-cov \
    pytest-asyncio \
    pytest-xdist \
    pytest-timeout \
    coverage \
    hypothesis

# ============================================
# Utilities
# ============================================
echo "Installing utility packages..."

pip install \
    click \
    rich \
    pyyaml \
    toml \
    python-dotenv \
    jinja2 \
    psutil \
    tqdm

# ============================================
# Optional: Development Dependencies
# ============================================
echo "Installing development dependencies..."

pip install \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit

# ============================================
# Install SurfScreen in editable mode
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    echo ""
    echo "Installing SurfScreen in editable mode..."
    pip install -e "$PROJECT_ROOT"
fi

# ============================================
# Verify Installation
# ============================================
echo ""
echo "=================================================="
echo "Verifying installation..."
echo "=================================================="

python << 'EOF'
import sys

packages = [
    ('ase', 'ase'),
    ('numpy', 'numpy'),
    ('pandas', 'pandas'),
    ('fastapi', 'fastapi'),
    ('pydantic', 'pydantic'),
    ('email_validator', 'email-validator'),
    ('pytest', 'pytest'),
    ('httpx', 'httpx'),
    ('redis', 'redis'),
    ('torch', 'torch'),
]

failed = []
for import_name, package_name in packages:
    try:
        __import__(import_name)
        print(f"✓ {package_name}")
    except ImportError:
        print(f"✗ {package_name}")
        failed.append(package_name)

print("")
if failed:
    print(f"Failed to install: {', '.join(failed)}")
    sys.exit(1)
else:
    print("All packages installed successfully!")
EOF

echo ""
echo "=================================================="
echo "Installation complete!"
echo "=================================================="
echo ""
echo "Now run tests with:"
echo "  ./scripts/run_all_tests.sh --quick --parallel 4"
