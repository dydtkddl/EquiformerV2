"""
Integration Tests for Batch API

Tests batch processing API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
import json


@pytest.fixture
def mock_batch_processor():
    """Create a mock BatchProcessor."""
    mock = MagicMock()
    
    # Mock job
    mock_job = MagicMock()
    mock_job.batch_id = "batch-123"
    mock_job.name = "Test Batch"
    mock_job.job_type = "screening"
    mock_job.status.value = "pending"
    mock_job.progress = MagicMock(total=10, completed=0, failed=0, percentage=0.0)
    mock_job.created_at = "2026-01-01T00:00:00"
    mock_job.to_dict.return_value = {
        "batch_id": "batch-123",
        "name": "Test Batch",
        "status": "pending",
        "progress": {"total": 10, "completed": 0, "failed": 0, "percentage": 0.0},
    }
    
    mock.create_job.return_value = mock_job
    mock.get_job.return_value = mock_job
    mock.list_jobs.return_value = [mock_job]
    mock.cancel_job.return_value = True
    
    return mock


@pytest.fixture
def client(mock_batch_processor):
    """Create test client with mocked batch processor."""
    with patch("surfscreen.api.routers.batch.get_batch_processor", return_value=mock_batch_processor):
        from surfscreen.api.main import app
        
        with TestClient(app) as client:
            yield client


class TestBatchSubmit:
    """Tests for batch submit endpoint."""
    
    def test_submit_batch_job(self, client, mock_batch_processor):
        """Test submitting a batch job."""
        request_data = {
            "name": "My Batch",
            "job_type": "screening",
            "tasks": [
                {"id": 1, "data": "task1"},
                {"id": 2, "data": "task2"},
            ],
            "engine": "mace",
        }
        
        response = client.post("/api/v1/batch/submit", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batch_id" in data
        mock_batch_processor.create_job.assert_called_once()
    
    def test_submit_batch_validation_error(self, client):
        """Test batch submission with invalid data."""
        request_data = {
            "job_type": "screening",
            # Missing required 'tasks' field
        }
        
        response = client.post("/api/v1/batch/submit", json=request_data)
        
        assert response.status_code == 422
    
    def test_submit_batch_empty_tasks(self, client):
        """Test batch submission with empty tasks."""
        request_data = {
            "job_type": "screening",
            "tasks": [],  # Empty tasks
        }
        
        response = client.post("/api/v1/batch/submit", json=request_data)
        
        assert response.status_code == 422


class TestBatchList:
    """Tests for batch list endpoint."""
    
    def test_list_batches(self, client, mock_batch_processor):
        """Test listing batch jobs."""
        response = client.get("/api/v1/batch")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batches" in data
        assert len(data["batches"]) >= 0
    
    def test_list_batches_with_status_filter(self, client, mock_batch_processor):
        """Test listing with status filter."""
        response = client.get("/api/v1/batch?status=running")
        
        assert response.status_code == 200
    
    def test_list_batches_pagination(self, client, mock_batch_processor):
        """Test listing with pagination."""
        response = client.get("/api/v1/batch?limit=10&offset=0")
        
        assert response.status_code == 200


class TestBatchGet:
    """Tests for batch get endpoint."""
    
    def test_get_batch(self, client, mock_batch_processor):
        """Test getting a batch job."""
        response = client.get("/api/v1/batch/batch-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["batch_id"] == "batch-123"
    
    def test_get_batch_not_found(self, client, mock_batch_processor):
        """Test getting non-existent batch."""
        mock_batch_processor.get_job.return_value = None
        
        response = client.get("/api/v1/batch/nonexistent")
        
        assert response.status_code == 404


class TestBatchResults:
    """Tests for batch results endpoint."""
    
    def test_get_results(self, client, mock_batch_processor):
        """Test getting batch results."""
        mock_job = mock_batch_processor.get_job.return_value
        mock_job.get_results.return_value = {
            "batch_id": "batch-123",
            "results": [
                {"task_index": 0, "success": True, "result": {"energy": -1.5}},
                {"task_index": 1, "success": True, "result": {"energy": -1.8}},
            ],
        }
        
        response = client.get("/api/v1/batch/batch-123/results")
        
        assert response.status_code == 200
    
    def test_get_results_not_ready(self, client, mock_batch_processor):
        """Test getting results when job is still running."""
        mock_job = mock_batch_processor.get_job.return_value
        mock_job.status.value = "running"
        mock_job.get_results.return_value = None
        
        response = client.get("/api/v1/batch/batch-123/results")
        
        # Should return partial results or appropriate status
        assert response.status_code in [200, 202]


class TestBatchCancel:
    """Tests for batch cancel endpoint."""
    
    def test_cancel_batch(self, client, mock_batch_processor):
        """Test cancelling a batch job."""
        response = client.post("/api/v1/batch/batch-123/cancel")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["cancelled"] is True
        mock_batch_processor.cancel_job.assert_called_with("batch-123")
    
    def test_cancel_batch_not_found(self, client, mock_batch_processor):
        """Test cancelling non-existent batch."""
        mock_batch_processor.cancel_job.return_value = False
        mock_batch_processor.get_job.return_value = None
        
        response = client.post("/api/v1/batch/nonexistent/cancel")
        
        assert response.status_code == 404


class TestBatchResume:
    """Tests for batch resume endpoint."""
    
    def test_resume_batch(self, client, mock_batch_processor):
        """Test resuming a paused batch."""
        mock_job = mock_batch_processor.get_job.return_value
        mock_job.status.value = "paused"
        
        mock_batch_processor.resume_job.return_value = mock_job
        
        response = client.post("/api/v1/batch/batch-123/resume")
        
        assert response.status_code == 200
    
    def test_resume_batch_not_found(self, client, mock_batch_processor):
        """Test resuming non-existent batch."""
        mock_batch_processor.resume_job.return_value = None
        mock_batch_processor.get_job.return_value = None
        
        response = client.post("/api/v1/batch/nonexistent/resume")
        
        assert response.status_code == 404


class TestBatchDownload:
    """Tests for batch download endpoint."""
    
    def test_download_results(self, client, mock_batch_processor):
        """Test downloading batch results."""
        mock_job = mock_batch_processor.get_job.return_value
        mock_job.status.value = "completed"
        mock_job.get_output_file.return_value = None  # No file available
        
        response = client.get("/api/v1/batch/batch-123/download")
        
        # May return 200 with data or 404 if file not ready
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
