"""
Integration Tests Package

Fixtures and configuration for API integration tests.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch, MagicMock

# Add src to path
import sys
tests_dir = Path(__file__).parent.parent
src_dir = tests_dir.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_xyz_content():
    """Sample XYZ file content."""
    return """3
Water molecule
O  0.000  0.000  0.000
H  0.757  0.586  0.000
H -0.757  0.586  0.000
"""


@pytest.fixture
def sample_surface_xyz():
    """Sample surface XYZ content."""
    return """4
Cu(111) slab
Cu  0.000  0.000  0.000
Cu  2.556  0.000  0.000
Cu  1.278  2.213  0.000
Cu  0.852  0.492  2.087
"""


@pytest.fixture
def sample_molecule_file(temp_dir, sample_xyz_content):
    """Create sample molecule file."""
    path = temp_dir / "molecule.xyz"
    path.write_text(sample_xyz_content)
    return path


@pytest.fixture
def sample_surface_file(temp_dir, sample_surface_xyz):
    """Create sample surface file."""
    path = temp_dir / "surface.xyz"
    path.write_text(sample_surface_xyz)
    return path


@pytest.fixture
def mock_job_manager():
    """Mock job manager for testing."""
    manager = MagicMock()
    manager.create_job.return_value = {
        "job_id": "test-job-123",
        "status": "pending",
        "created_at": "2026-02-02T09:00:00Z"
    }
    manager.get_job.return_value = {
        "job_id": "test-job-123",
        "status": "completed",
        "progress": 100
    }
    manager.list_jobs.return_value = []
    return manager


@pytest.fixture
def api_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from surfscreen.api.main import app
    return TestClient(app)


@pytest.fixture
def authenticated_client(api_client):
    """API client with authentication."""
    class AuthenticatedClient:
        def __init__(self, client):
            self.client = client
            self.headers = {"X-API-Key": "test-api-key-12345"}
        
        def get(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return self.client.get(url, **kwargs)
        
        def post(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return self.client.post(url, **kwargs)
        
        def put(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return self.client.put(url, **kwargs)
        
        def delete(self, url, **kwargs):
            kwargs.setdefault("headers", {}).update(self.headers)
            return self.client.delete(url, **kwargs)
    
    with patch('surfscreen.api.dependencies.verify_api_key', return_value=True):
        yield AuthenticatedClient(api_client)


# Markers registration
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
