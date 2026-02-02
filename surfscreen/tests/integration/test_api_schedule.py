"""
Integration Tests for Schedule API

Tests schedule management API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_scheduler():
    """Create a mock Scheduler."""
    mock = MagicMock()
    
    # Mock schedule
    mock_schedule = MagicMock()
    mock_schedule.schedule_id = "sched-123"
    mock_schedule.name = "Daily Screening"
    mock_schedule.schedule_type.value = "cron"
    mock_schedule.status.value = "active"
    mock_schedule.job_type = "screening"
    mock_schedule.cron_expression = "0 0 * * *"
    mock_schedule.next_run = "2026-01-02T00:00:00"
    mock_schedule.last_run = None
    mock_schedule.run_count = 0
    mock_schedule.to_dict.return_value = {
        "schedule_id": "sched-123",
        "name": "Daily Screening",
        "schedule_type": "cron",
        "status": "active",
        "cron_expression": "0 0 * * *",
        "next_run": "2026-01-02T00:00:00",
        "run_count": 0,
    }
    
    mock.create_schedule.return_value = mock_schedule
    mock.get_schedule.return_value = mock_schedule
    mock.list_schedules.return_value = [mock_schedule]
    mock.pause_schedule.return_value = True
    mock.resume_schedule.return_value = True
    mock.delete_schedule.return_value = True
    mock.get_history.return_value = []
    
    return mock


@pytest.fixture
def client(mock_scheduler):
    """Create test client with mocked scheduler."""
    with patch("surfscreen.api.routers.schedule.get_scheduler", return_value=mock_scheduler):
        from surfscreen.api.main import app
        
        with TestClient(app) as client:
            yield client


class TestScheduleCreate:
    """Tests for schedule creation endpoint."""
    
    def test_create_cron_schedule(self, client, mock_scheduler):
        """Test creating a cron schedule."""
        request_data = {
            "name": "Daily Screening",
            "schedule_type": "cron",
            "job_type": "screening",
            "job_config": {"engine": "mace"},
            "cron_expression": "0 0 * * *",
        }
        
        response = client.post("/api/v1/schedules", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "schedule_id" in data
        mock_scheduler.create_schedule.assert_called_once()
    
    def test_create_interval_schedule(self, client, mock_scheduler):
        """Test creating an interval schedule."""
        request_data = {
            "name": "Hourly Job",
            "schedule_type": "interval",
            "job_type": "md",
            "job_config": {},
            "interval_seconds": 3600,
        }
        
        response = client.post("/api/v1/schedules", json=request_data)
        
        assert response.status_code == 200
    
    def test_create_once_schedule(self, client, mock_scheduler):
        """Test creating a one-time schedule."""
        request_data = {
            "name": "One-time Job",
            "schedule_type": "once",
            "job_type": "screening",
            "job_config": {},
            "run_at": "2026-01-15T10:00:00",
        }
        
        response = client.post("/api/v1/schedules", json=request_data)
        
        assert response.status_code == 200


class TestScheduleList:
    """Tests for schedule list endpoint."""
    
    def test_list_schedules(self, client, mock_scheduler):
        """Test listing schedules."""
        response = client.get("/api/v1/schedules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "schedules" in data
        assert len(data["schedules"]) >= 0
    
    def test_list_with_status_filter(self, client, mock_scheduler):
        """Test listing with status filter."""
        response = client.get("/api/v1/schedules?status=active")
        
        assert response.status_code == 200
    
    def test_list_with_type_filter(self, client, mock_scheduler):
        """Test listing with type filter."""
        response = client.get("/api/v1/schedules?type=cron")
        
        assert response.status_code == 200


class TestScheduleGet:
    """Tests for schedule get endpoint."""
    
    def test_get_schedule(self, client, mock_scheduler):
        """Test getting a schedule."""
        response = client.get("/api/v1/schedules/sched-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["schedule_id"] == "sched-123"
    
    def test_get_schedule_not_found(self, client, mock_scheduler):
        """Test getting non-existent schedule."""
        mock_scheduler.get_schedule.return_value = None
        
        response = client.get("/api/v1/schedules/nonexistent")
        
        assert response.status_code == 404


class TestScheduleUpdate:
    """Tests for schedule update endpoint."""
    
    def test_update_schedule(self, client, mock_scheduler):
        """Test updating a schedule."""
        request_data = {
            "name": "Updated Name",
            "cron_expression": "0 12 * * *",
        }
        
        mock_scheduler.update_schedule.return_value = mock_scheduler.get_schedule.return_value
        
        response = client.put("/api/v1/schedules/sched-123", json=request_data)
        
        assert response.status_code == 200


class TestSchedulePauseResume:
    """Tests for schedule pause/resume endpoints."""
    
    def test_pause_schedule(self, client, mock_scheduler):
        """Test pausing a schedule."""
        response = client.post("/api/v1/schedules/sched-123/pause")
        
        assert response.status_code == 200
        mock_scheduler.pause_schedule.assert_called_with("sched-123")
    
    def test_resume_schedule(self, client, mock_scheduler):
        """Test resuming a schedule."""
        response = client.post("/api/v1/schedules/sched-123/resume")
        
        assert response.status_code == 200
        mock_scheduler.resume_schedule.assert_called_with("sched-123")


class TestScheduleTrigger:
    """Tests for schedule manual trigger endpoint."""
    
    def test_trigger_schedule(self, client, mock_scheduler):
        """Test manually triggering a schedule."""
        mock_scheduler.trigger_schedule.return_value = {"status": "triggered"}
        
        response = client.post("/api/v1/schedules/sched-123/trigger")
        
        assert response.status_code == 200


class TestScheduleDelete:
    """Tests for schedule delete endpoint."""
    
    def test_delete_schedule(self, client, mock_scheduler):
        """Test deleting a schedule."""
        response = client.delete("/api/v1/schedules/sched-123")
        
        assert response.status_code == 200
        mock_scheduler.delete_schedule.assert_called_with("sched-123")
    
    def test_delete_schedule_not_found(self, client, mock_scheduler):
        """Test deleting non-existent schedule."""
        mock_scheduler.delete_schedule.return_value = False
        mock_scheduler.get_schedule.return_value = None
        
        response = client.delete("/api/v1/schedules/nonexistent")
        
        assert response.status_code == 404


class TestScheduleHistory:
    """Tests for schedule history endpoint."""
    
    def test_get_history(self, client, mock_scheduler):
        """Test getting schedule execution history."""
        mock_scheduler.get_history.return_value = [
            {"run_id": "run-1", "status": "completed", "timestamp": "2026-01-01T00:00:00"},
            {"run_id": "run-2", "status": "completed", "timestamp": "2026-01-02T00:00:00"},
        ]
        
        response = client.get("/api/v1/schedules/sched-123/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "history" in data
        assert len(data["history"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
