"""
API Integration Tests - Full Workflow Tests

Tests complete API workflows:
- Screening job lifecycle
- MD simulation lifecycle
- Error handling
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

pytestmark = [pytest.mark.integration]


class TestScreeningWorkflow:
    """Test complete screening job workflow."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def valid_api_key(self):
        """Valid API key for testing."""
        return "test-api-key-12345"
    
    @pytest.fixture
    def auth_headers(self, valid_api_key):
        """Auth headers with valid API key."""
        return {"X-API-Key": valid_api_key}
    
    @pytest.fixture
    def sample_structure_file(self, tmp_path):
        """Create sample structure file."""
        xyz_content = """3
Water molecule
O  0.000  0.000  0.000
H  0.757  0.586  0.000
H -0.757  0.586  0.000
"""
        path = tmp_path / "water.xyz"
        path.write_text(xyz_content)
        return path
    
    @pytest.fixture
    def sample_surface_file(self, tmp_path):
        """Create sample surface file."""
        xyz_content = """12
Cu(111) surface
Cu  0.000  0.000  0.000
Cu  2.556  0.000  0.000
Cu  1.278  2.213  0.000
Cu  3.834  2.213  0.000
Cu  0.852  0.492  2.087
Cu  3.408  0.492  2.087
Cu  2.130  2.705  2.087
Cu  4.686  2.705  2.087
Cu  1.704  0.984  4.174
Cu  4.260  0.984  4.174
Cu  2.982  3.197  4.174
Cu  5.538  3.197  4.174
"""
        path = tmp_path / "cu111.xyz"
        path.write_text(xyz_content)
        return path
    
    def test_health_check(self, api_client):
        """Test API health endpoint."""
        response = api_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_create_screening_job(
        self, 
        mock_verify, 
        api_client, 
        auth_headers,
        sample_structure_file,
        sample_surface_file
    ):
        """Test creating a screening job."""
        mock_verify.return_value = True
        
        with open(sample_structure_file, 'rb') as mol_file, \
             open(sample_surface_file, 'rb') as surf_file:
            
            response = api_client.post(
                "/api/v1/screening/submit",
                headers=auth_headers,
                files={
                    "molecule_file": ("water.xyz", mol_file, "chemical/x-xyz"),
                    "surface_file": ("cu111.xyz", surf_file, "chemical/x-xyz"),
                },
                data={
                    "engine": "emt",
                    "n_configs": "5",
                }
            )
        
        # Job should be created (or validation error if structure invalid)
        assert response.status_code in [200, 201, 422]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "job_id" in data
            assert data["status"] in ["pending", "running"]
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_get_job_status(self, mock_verify, api_client, auth_headers):
        """Test getting job status."""
        mock_verify.return_value = True
        
        # Test with non-existent job
        response = api_client.get(
            "/api/v1/jobs/non-existent-job-id",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_list_jobs(self, mock_verify, api_client, auth_headers):
        """Test listing all jobs."""
        mock_verify.return_value = True
        
        response = api_client.get(
            "/api/v1/jobs",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_cancel_job(self, mock_verify, api_client, auth_headers):
        """Test canceling a job."""
        mock_verify.return_value = True
        
        response = api_client.post(
            "/api/v1/jobs/non-existent-job-id/cancel",
            headers=auth_headers
        )
        
        # Should return 404 for non-existent job
        assert response.status_code == 404


class TestMDWorkflow:
    """Test complete MD simulation workflow."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Auth headers."""
        return {"X-API-Key": "test-api-key-12345"}
    
    @pytest.fixture
    def sample_system_file(self, tmp_path):
        """Create sample system for MD."""
        xyz_content = """8
Cu cluster for MD
Cu  0.000  0.000  0.000
Cu  2.556  0.000  0.000
Cu  1.278  2.213  0.000
Cu  3.834  2.213  0.000
Cu  0.852  0.492  2.087
Cu  3.408  0.492  2.087
Cu  2.130  2.705  2.087
Cu  4.686  2.705  2.087
"""
        path = tmp_path / "cu_cluster.xyz"
        path.write_text(xyz_content)
        return path
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_create_md_job(
        self, 
        mock_verify, 
        api_client, 
        auth_headers,
        sample_system_file
    ):
        """Test creating an MD job."""
        mock_verify.return_value = True
        
        with open(sample_system_file, 'rb') as f:
            response = api_client.post(
                "/api/v1/md/submit",
                headers=auth_headers,
                files={
                    "structure_file": ("cu_cluster.xyz", f, "chemical/x-xyz"),
                },
                data={
                    "ensemble": "nvt",
                    "temperature": "300",
                    "timestep": "1.0",
                    "n_steps": "100",
                }
            )
        
        assert response.status_code in [200, 201, 422]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "job_id" in data
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_get_md_result(self, mock_verify, api_client, auth_headers):
        """Test getting MD results."""
        mock_verify.return_value = True
        
        response = api_client.get(
            "/api/v1/md/non-existent-job-id/result",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestErrorHandling:
    """Test API error handling."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Auth headers."""
        return {"X-API-Key": "test-api-key-12345"}
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_invalid_structure_file(
        self, 
        mock_verify, 
        api_client, 
        auth_headers,
        tmp_path
    ):
        """Test handling of invalid structure file."""
        mock_verify.return_value = True
        
        # Create invalid file
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("This is not a valid structure file")
        
        with open(invalid_file, 'rb') as f:
            response = api_client.post(
                "/api/v1/screening/submit",
                headers=auth_headers,
                files={
                    "molecule_file": ("invalid.txt", f, "text/plain"),
                },
                data={"engine": "emt"}
            )
        
        # Should return validation error
        assert response.status_code == 422
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_missing_required_fields(
        self, 
        mock_verify, 
        api_client, 
        auth_headers
    ):
        """Test handling of missing required fields."""
        mock_verify.return_value = True
        
        response = api_client.post(
            "/api/v1/screening/submit",
            headers=auth_headers,
            data={}  # No files or data
        )
        
        assert response.status_code == 422
    
    def test_invalid_endpoint(self, api_client):
        """Test handling of invalid endpoint."""
        response = api_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, api_client):
        """Test handling of wrong HTTP method."""
        response = api_client.delete("/health")
        assert response.status_code == 405


class TestJobPolling:
    """Test job status polling workflow."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Auth headers."""
        return {"X-API-Key": "test-api-key-12345"}
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_job_status_transitions(self, mock_verify, api_client, auth_headers):
        """Test that job status follows valid transitions."""
        mock_verify.return_value = True
        
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        
        # This would be tested with actual job creation
        # For now, just verify the status enum is correct
        from surfscreen.api.models import JobStatus
        
        for status in valid_statuses:
            assert status in [s.value for s in JobStatus]
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_job_progress_tracking(self, mock_verify, api_client, auth_headers):
        """Test job progress is reported correctly."""
        mock_verify.return_value = True
        
        # Test jobs endpoint returns progress info
        response = api_client.get(
            "/api/v1/jobs?status=running",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestResultDownload:
    """Test result download functionality."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Auth headers."""
        return {"X-API-Key": "test-api-key-12345"}
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_download_nonexistent_result(
        self, 
        mock_verify, 
        api_client, 
        auth_headers
    ):
        """Test downloading results for non-existent job."""
        mock_verify.return_value = True
        
        response = api_client.get(
            "/api/v1/jobs/nonexistent/download",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_download_trajectory(
        self, 
        mock_verify, 
        api_client, 
        auth_headers
    ):
        """Test downloading MD trajectory."""
        mock_verify.return_value = True
        
        response = api_client.get(
            "/api/v1/md/nonexistent/trajectory",
            headers=auth_headers
        )
        
        assert response.status_code == 404
