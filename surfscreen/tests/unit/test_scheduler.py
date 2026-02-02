"""
Unit Tests for Scheduler Module

Tests Scheduler, schedule types, and job execution.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json


class TestScheduleType:
    """Tests for ScheduleType enum."""
    
    def test_schedule_types(self):
        """Test schedule type values."""
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        assert ScheduleType.CRON.value == "cron"
        assert ScheduleType.INTERVAL.value == "interval"
        assert ScheduleType.ONCE.value == "once"
        assert ScheduleType.DEPENDENCY.value == "dependency"


class TestScheduleStatus:
    """Tests for ScheduleStatus enum."""
    
    def test_schedule_statuses(self):
        """Test schedule status values."""
        from surfscreen.scheduler.schedule_models import ScheduleStatus
        
        assert ScheduleStatus.ACTIVE.value == "active"
        assert ScheduleStatus.PAUSED.value == "paused"
        assert ScheduleStatus.COMPLETED.value == "completed"
        assert ScheduleStatus.FAILED.value == "failed"


class TestScheduledJob:
    """Tests for ScheduledJob dataclass."""
    
    def test_job_creation(self):
        """Test scheduled job creation."""
        from surfscreen.scheduler.schedule_models import (
            ScheduledJob,
            ScheduleType,
            ScheduleStatus,
        )
        
        job = ScheduledJob(
            schedule_id="sched-123",
            name="Daily Screening",
            schedule_type=ScheduleType.CRON,
            status=ScheduleStatus.ACTIVE,
            job_config={"job_type": "screening"},
            cron_expression="0 0 * * *",
        )
        
        assert job.schedule_id == "sched-123"
        assert job.name == "Daily Screening"
        assert job.schedule_type == ScheduleType.CRON
        assert job.run_count == 0
    
    def test_job_to_dict(self):
        """Test scheduled job serialization."""
        from surfscreen.scheduler.schedule_models import (
            ScheduledJob,
            ScheduleType,
            ScheduleStatus,
        )
        
        job = ScheduledJob(
            schedule_id="sched-123",
            name="Test Job",
            schedule_type=ScheduleType.INTERVAL,
            status=ScheduleStatus.ACTIVE,
            job_config={"job_type": "md"},
            interval_seconds=3600,
            created_at="2026-01-01T00:00:00",
        )
        
        data = job.to_dict()
        
        assert data["schedule_id"] == "sched-123"
        assert data["schedule_type"] == "interval"
        assert data["status"] == "active"
        assert data["interval_seconds"] == 3600


class TestScheduleCreate:
    """Tests for ScheduleCreate Pydantic model."""
    
    def test_cron_schedule_validation(self):
        """Test cron schedule validation."""
        from surfscreen.scheduler.schedule_models import ScheduleCreate, ScheduleType
        
        schedule = ScheduleCreate(
            name="Daily Job",
            schedule_type=ScheduleType.CRON,
            job_type="screening",
            job_config={"engine": "mace"},
            cron_expression="0 0 * * *",
        )
        
        assert schedule.cron_expression == "0 0 * * *"
    
    def test_interval_schedule_validation(self):
        """Test interval schedule validation."""
        from surfscreen.scheduler.schedule_models import ScheduleCreate, ScheduleType
        
        schedule = ScheduleCreate(
            name="Hourly Job",
            schedule_type=ScheduleType.INTERVAL,
            job_type="screening",
            job_config={},
            interval_seconds=3600,
        )
        
        assert schedule.interval_seconds == 3600
    
    def test_interval_minimum(self):
        """Test interval minimum requirement."""
        from surfscreen.scheduler.schedule_models import ScheduleCreate, ScheduleType
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ScheduleCreate(
                name="Too Frequent",
                schedule_type=ScheduleType.INTERVAL,
                job_type="screening",
                job_config={},
                interval_seconds=30,  # Below 60 minimum
            )


class TestScheduler:
    """Tests for Scheduler class."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance with temp storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock APScheduler not being installed
            with patch("surfscreen.scheduler.scheduler.BackgroundScheduler", None):
                from surfscreen.scheduler.scheduler import Scheduler
                
                sched = Scheduler(storage_dir=Path(tmpdir))
                yield sched
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock job executor."""
        def executor(job_config):
            return {"status": "completed", "result": job_config}
        return executor
    
    def test_scheduler_creation(self):
        """Test scheduler initialization."""
        from surfscreen.scheduler.scheduler import Scheduler
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(storage_dir=Path(tmpdir))
            
            assert scheduler.storage_dir == Path(tmpdir)
            assert len(scheduler.schedules) == 0
    
    def test_create_cron_schedule(self, mock_executor):
        """Test creating a cron schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType, ScheduleStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Daily Screening",
                schedule_type=ScheduleType.CRON,
                job_type="screening",
                job_config={"engine": "mace"},
                cron_expression="0 0 * * *",
            )
            
            assert schedule.name == "Daily Screening"
            assert schedule.schedule_type == ScheduleType.CRON
            assert schedule.status == ScheduleStatus.ACTIVE
            assert schedule.schedule_id in scheduler.schedules
    
    def test_create_interval_schedule(self, mock_executor):
        """Test creating an interval schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Hourly Check",
                schedule_type=ScheduleType.INTERVAL,
                job_type="md",
                job_config={},
                interval_seconds=3600,
            )
            
            assert schedule.interval_seconds == 3600
            assert schedule.next_run is not None
    
    def test_create_once_schedule(self, mock_executor):
        """Test creating a one-time schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            run_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
            
            schedule = scheduler.create_schedule(
                name="One-time Job",
                schedule_type=ScheduleType.ONCE,
                job_type="screening",
                job_config={},
                run_at=run_at,
            )
            
            assert schedule.run_at == run_at
            assert schedule.next_run == run_at
    
    def test_get_schedule(self, mock_executor):
        """Test retrieving a schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Test",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={},
                interval_seconds=3600,
            )
            
            retrieved = scheduler.get_schedule(schedule.schedule_id)
            
            assert retrieved is schedule
            assert scheduler.get_schedule("nonexistent") is None
    
    def test_list_schedules(self, mock_executor):
        """Test listing schedules with filtering."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType, ScheduleStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            sched1 = scheduler.create_schedule(
                name="Schedule 1",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={},
                interval_seconds=3600,
            )
            sched2 = scheduler.create_schedule(
                name="Schedule 2",
                schedule_type=ScheduleType.CRON,
                job_type="test",
                job_config={},
                cron_expression="0 * * * *",
            )
            
            # List all
            all_schedules = scheduler.list_schedules()
            assert len(all_schedules) == 2
            
            # Filter by type
            interval_schedules = scheduler.list_schedules(
                schedule_type=ScheduleType.INTERVAL
            )
            assert len(interval_schedules) == 1
    
    def test_pause_and_resume_schedule(self, mock_executor):
        """Test pausing and resuming a schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType, ScheduleStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Test",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={},
                interval_seconds=3600,
            )
            
            # Pause
            scheduler.pause_schedule(schedule.schedule_id)
            assert schedule.status == ScheduleStatus.PAUSED
            
            # Resume
            scheduler.resume_schedule(schedule.schedule_id)
            assert schedule.status == ScheduleStatus.ACTIVE
    
    def test_delete_schedule(self, mock_executor):
        """Test deleting a schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Test",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={},
                interval_seconds=3600,
            )
            
            schedule_id = schedule.schedule_id
            
            success = scheduler.delete_schedule(schedule_id)
            
            assert success is True
            assert scheduler.get_schedule(schedule_id) is None
    
    def test_schedule_execution(self, mock_executor):
        """Test scheduled job execution."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Test",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={"param": "value"},
                interval_seconds=3600,
            )
            
            # Manually trigger execution
            scheduler._execute_scheduled_job(schedule.schedule_id)
            
            # Check execution was recorded
            assert schedule.run_count == 1
            assert schedule.last_run is not None
            assert schedule.last_result is not None
    
    def test_schedule_execution_failure(self):
        """Test handling of failed scheduled job."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        def failing_executor(job_config):
            raise ValueError("Execution failed")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=failing_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Failing Job",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={},
                interval_seconds=3600,
            )
            
            # Execute (should handle error gracefully)
            scheduler._execute_scheduled_job(schedule.schedule_id)
            
            assert schedule.last_error is not None
            assert "Execution failed" in schedule.last_error
    
    def test_max_runs_limit(self, mock_executor):
        """Test schedule completion after max runs."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType, ScheduleStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Limited Job",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={},
                interval_seconds=3600,
                max_runs=3,
            )
            
            # Execute max_runs times
            for _ in range(3):
                scheduler._execute_scheduled_job(schedule.schedule_id)
            
            assert schedule.run_count == 3
            assert schedule.status == ScheduleStatus.COMPLETED
    
    def test_get_history(self, mock_executor):
        """Test getting execution history."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler.create_schedule(
                name="Test",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={},
                interval_seconds=3600,
            )
            
            # Execute a few times
            scheduler._execute_scheduled_job(schedule.schedule_id)
            scheduler._execute_scheduled_job(schedule.schedule_id)
            
            history = scheduler.get_history(schedule.schedule_id)
            
            assert len(history) == 2
            assert history[0]["status"] == "completed"
    
    def test_persistence(self, mock_executor):
        """Test schedule persistence to disk."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create scheduler and add schedule
            scheduler1 = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            schedule = scheduler1.create_schedule(
                name="Persistent Job",
                schedule_type=ScheduleType.INTERVAL,
                job_type="test",
                job_config={"key": "value"},
                interval_seconds=3600,
            )
            
            schedule_id = schedule.schedule_id
            
            # Create new scheduler instance (simulates restart)
            scheduler2 = Scheduler(
                executor_fn=mock_executor,
                storage_dir=Path(tmpdir),
            )
            
            # Schedule should be loaded from disk
            loaded_schedule = scheduler2.get_schedule(schedule_id)
            
            assert loaded_schedule is not None
            assert loaded_schedule.name == "Persistent Job"


class TestNextRunCalculation:
    """Tests for next run time calculation."""
    
    def test_interval_next_run(self):
        """Test next run calculation for interval schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType, ScheduledJob, ScheduleStatus
        
        scheduler = Scheduler.__new__(Scheduler)
        
        schedule = ScheduledJob(
            schedule_id="test",
            name="Test",
            schedule_type=ScheduleType.INTERVAL,
            status=ScheduleStatus.ACTIVE,
            job_config={},
            interval_seconds=3600,
        )
        
        next_run = scheduler._calculate_next_run(schedule)
        
        assert next_run is not None
        # Should be approximately 1 hour from now
        next_dt = datetime.fromisoformat(next_run)
        now = datetime.utcnow()
        diff = (next_dt - now).total_seconds()
        assert 3590 < diff < 3610  # Within 10 seconds of 1 hour
    
    def test_once_next_run(self):
        """Test next run for one-time schedule."""
        from surfscreen.scheduler.scheduler import Scheduler
        from surfscreen.scheduler.schedule_models import ScheduleType, ScheduledJob, ScheduleStatus
        
        scheduler = Scheduler.__new__(Scheduler)
        
        run_at = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        
        schedule = ScheduledJob(
            schedule_id="test",
            name="Test",
            schedule_type=ScheduleType.ONCE,
            status=ScheduleStatus.ACTIVE,
            job_config={},
            run_at=run_at,
        )
        
        next_run = scheduler._calculate_next_run(schedule)
        
        assert next_run == run_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
