"""
SurfScreen Test Configuration (conftest.py)

Shared fixtures and configuration for all tests.
"""

import os
import sys
import pytest
import tempfile
import asyncio
from pathlib import Path
from typing import Generator, Any
from unittest.mock import MagicMock, AsyncMock

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


# ============================================
# Pytest Configuration
# ============================================

def pytest_configure(config):
    """Pytest configuration hook."""
    # Register custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "gpu: marks tests requiring GPU")
    config.addinivalue_line("markers", "network: marks tests requiring network")
    config.addinivalue_line("markers", "integration: marks integration tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    skip_slow = pytest.mark.skip(reason="skipping slow tests")
    skip_gpu = pytest.mark.skip(reason="skipping GPU tests")
    skip_network = pytest.mark.skip(reason="skipping network tests")
    
    for item in items:
        if "slow" in item.keywords and os.environ.get("SKIP_SLOW_TESTS") == "true":
            item.add_marker(skip_slow)
        if "gpu" in item.keywords and os.environ.get("SKIP_GPU_TESTS") == "true":
            item.add_marker(skip_gpu)
        if "network" in item.keywords and os.environ.get("SKIP_NETWORK_TESTS") == "true":
            item.add_marker(skip_network)


# ============================================
# Async Fixtures
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================
# Temp Directory Fixtures
# ============================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir: Path) -> Generator[Path, None, None]:
    """Create temporary file for test."""
    filepath = temp_dir / "test_file.txt"
    filepath.write_text("test content")
    yield filepath


# ============================================
# Mock Fixtures
# ============================================

@pytest.fixture
def mock_cache_manager():
    """Create mock CacheManager."""
    mock = MagicMock()
    mock.get = MagicMock(return_value=None)
    mock.set = MagicMock(return_value=True)
    mock.delete = MagicMock(return_value=True)
    mock.clear = MagicMock(return_value=True)
    mock.get_stats = MagicMock(return_value={
        "hits": 100,
        "misses": 20,
        "size": 1024,
    })
    return mock


@pytest.fixture
def mock_batch_processor():
    """Create mock BatchProcessor."""
    mock = MagicMock()
    mock.submit = MagicMock(return_value="batch-123")
    mock.get_status = MagicMock(return_value="running")
    mock.get_progress = MagicMock(return_value={"completed": 50, "total": 100})
    mock.get_result = MagicMock(return_value={"status": "completed"})
    return mock


@pytest.fixture
def mock_scheduler():
    """Create mock Scheduler."""
    mock = MagicMock()
    mock.add_job = MagicMock(return_value="job-123")
    mock.remove_job = MagicMock(return_value=True)
    mock.list_jobs = MagicMock(return_value=[])
    mock.pause = MagicMock(return_value=True)
    mock.resume = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_auth_service():
    """Create mock AuthService."""
    mock = MagicMock()
    
    # Mock user
    mock_user = MagicMock()
    mock_user.user_id = "user-123"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.role = MagicMock(value="user")
    
    mock.authenticate = MagicMock(return_value=mock_user)
    mock.create_user = MagicMock(return_value=mock_user)
    mock.get_user = MagicMock(return_value=mock_user)
    mock.verify_api_key = MagicMock(return_value=mock_user)
    
    return mock


@pytest.fixture
def mock_notification_service():
    """Create mock NotificationService."""
    mock = MagicMock()
    mock.send = AsyncMock(return_value=True)
    mock.register_webhook = MagicMock(return_value="wh-123")
    mock.trigger_event = AsyncMock(return_value=True)
    return mock


# ============================================
# API Test Fixtures
# ============================================

@pytest.fixture
def api_client():
    """Create FastAPI test client."""
    try:
        from fastapi.testclient import TestClient
        from surfscreen.api.main import app
        
        with TestClient(app) as client:
            yield client
    except ImportError:
        pytest.skip("FastAPI or surfscreen.api not available")


@pytest.fixture
def async_api_client():
    """Create async HTTP client for API tests."""
    try:
        import httpx
        
        base_url = os.environ.get("SURFSCREEN_API_URL", "http://localhost:8000")
        
        async def get_client():
            async with httpx.AsyncClient(base_url=base_url) as client:
                yield client
        
        return get_client
    except ImportError:
        pytest.skip("httpx not available")


# ============================================
# Sample Data Fixtures
# ============================================

@pytest.fixture
def sample_xyz_content() -> str:
    """Sample XYZ file content."""
    return """3
Water molecule
O  0.000000  0.000000  0.117489
H  0.756950  0.000000 -0.469957
H -0.756950  0.000000 -0.469957
"""


@pytest.fixture
def sample_cif_content() -> str:
    """Sample CIF file content."""
    return """data_test
_cell_length_a   3.0
_cell_length_b   3.0
_cell_length_c   20.0
_cell_angle_alpha   90.0
_cell_angle_beta    90.0
_cell_angle_gamma   90.0
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Cu1  0.0  0.0  0.5
Cu2  0.5  0.5  0.5
"""


@pytest.fixture
def sample_xyz_file(temp_dir: Path, sample_xyz_content: str) -> Path:
    """Create sample XYZ file."""
    filepath = temp_dir / "molecule.xyz"
    filepath.write_text(sample_xyz_content)
    return filepath


@pytest.fixture
def sample_cif_file(temp_dir: Path, sample_cif_content: str) -> Path:
    """Create sample CIF file."""
    filepath = temp_dir / "surface.cif"
    filepath.write_text(sample_cif_content)
    return filepath


# ============================================
# GPU Fixtures
# ============================================

@pytest.fixture
def gpu_available() -> bool:
    """Check if GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


@pytest.fixture
def skip_if_no_gpu(gpu_available):
    """Skip test if GPU not available."""
    if not gpu_available:
        pytest.skip("GPU not available")


# ============================================
# Logging Configuration
# ============================================

@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests."""
    import logging
    
    log_level = os.environ.get("PYTEST_LOG_LEVEL", "WARNING")
    logging.basicConfig(level=getattr(logging, log_level))
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
