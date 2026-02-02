"""
Unit Tests for Batch Module

Tests BatchJob, BatchProcessor, and batch models.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from pathlib import Path
import tempfile
import json


class TestBatchJobStatus:
    """Tests for BatchJobStatus enum."""
    
    def test_status_values(self):
        """Test batch job status values."""
        from surfscreen.batch.batch_models import BatchJobStatus
        
        assert BatchJobStatus.PENDING.value == "pending"
        assert BatchJobStatus.RUNNING.value == "running"
        assert BatchJobStatus.COMPLETED.value == "completed"
        assert BatchJobStatus.FAILED.value == "failed"
        assert BatchJobStatus.CANCELLED.value == "cancelled"


class TestBatchConfig:
    """Tests for BatchConfig dataclass."""
    
    def test_default_config(self):
        """Test default batch configuration."""
        from surfscreen.batch.batch_models import BatchConfig
        
        config = BatchConfig()
        
        assert config.max_workers == 4
        assert config.chunk_size == 10
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.timeout is None
    
    def test_custom_config(self):
        """Test custom batch configuration."""
        from surfscreen.batch.batch_models import BatchConfig
        
        config = BatchConfig(
            max_workers=8,
            chunk_size=20,
            max_retries=5,
            timeout=300,
        )
        
        assert config.max_workers == 8
        assert config.chunk_size == 20
        assert config.timeout == 300


class TestBatchProgress:
    """Tests for BatchProgress dataclass."""
    
    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        from surfscreen.batch.batch_models import BatchProgress
        
        progress = BatchProgress(total=100, completed=25, failed=5)
        
        assert progress.total == 100
        assert progress.completed == 25
        assert progress.failed == 5
        assert progress.percentage == 30.0  # (25 + 5) / 100 * 100
    
    def test_progress_zero_total(self):
        """Test progress with zero total."""
        from surfscreen.batch.batch_models import BatchProgress
        
        progress = BatchProgress(total=0, completed=0, failed=0)
        
        assert progress.percentage == 0.0


class TestBatchJob:
    """Tests for BatchJob class."""
    
    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            {"id": 1, "data": "task1"},
            {"id": 2, "data": "task2"},
            {"id": 3, "data": "task3"},
        ]
    
    def test_job_creation(self, sample_tasks):
        """Test batch job creation."""
        from surfscreen.batch.batch_processor import BatchJob
        from surfscreen.batch.batch_models import BatchJobStatus
        
        job = BatchJob(
            batch_id="test-123",
            job_type="screening",
            tasks=sample_tasks,
        )
        
        assert job.batch_id == "test-123"
        assert job.job_type == "screening"
        assert job.status == BatchJobStatus.PENDING
        assert len(job.tasks) == 3
        assert job.progress.total == 3
    
    def test_job_status_transitions(self, sample_tasks):
        """Test valid status transitions."""
        from surfscreen.batch.batch_processor import BatchJob
        from surfscreen.batch.batch_models import BatchJobStatus
        
        job = BatchJob(
            batch_id="test-123",
            job_type="screening",
            tasks=sample_tasks,
        )
        
        # PENDING -> RUNNING
        job.status = BatchJobStatus.RUNNING
        assert job.status == BatchJobStatus.RUNNING
        
        # RUNNING -> COMPLETED
        job.status = BatchJobStatus.COMPLETED
        assert job.status == BatchJobStatus.COMPLETED
    
    def test_job_update_progress(self, sample_tasks):
        """Test progress updates."""
        from surfscreen.batch.batch_processor import BatchJob
        
        job = BatchJob(
            batch_id="test-123",
            job_type="screening",
            tasks=sample_tasks,
        )
        
        job.update_progress(completed=1)
        assert job.progress.completed == 1
        
        job.update_progress(completed=2, failed=1)
        assert job.progress.completed == 2
        assert job.progress.failed == 1
    
    def test_job_checkpoint(self, sample_tasks):
        """Test checkpoint creation and loading."""
        from surfscreen.batch.batch_processor import BatchJob
        from surfscreen.batch.batch_models import BatchJobStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            job = BatchJob(
                batch_id="test-123",
                job_type="screening",
                tasks=sample_tasks,
                checkpoint_dir=Path(tmpdir),
            )
            
            job.status = BatchJobStatus.RUNNING
            job.update_progress(completed=2, failed=0)
            
            # Save checkpoint
            job.save_checkpoint()
            
            # Verify checkpoint file exists
            checkpoint_path = Path(tmpdir) / "test-123_checkpoint.json"
            assert checkpoint_path.exists()
            
            # Load checkpoint data
            with open(checkpoint_path) as f:
                data = json.load(f)
            
            assert data["batch_id"] == "test-123"
            assert data["progress"]["completed"] == 2


class TestBatchProcessor:
    """Tests for BatchProcessor class."""
    
    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks."""
        return [
            {"id": i, "value": i * 10}
            for i in range(5)
        ]
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor function."""
        def executor(task):
            return {"result": task["value"] * 2, "task_id": task["id"]}
        return executor
    
    def test_processor_creation(self, mock_executor):
        """Test batch processor creation."""
        from surfscreen.batch.batch_processor import BatchProcessor
        
        processor = BatchProcessor(executor_fn=mock_executor)
        
        assert processor.executor_fn == mock_executor
        assert len(processor.jobs) == 0
    
    def test_create_job(self, sample_tasks, mock_executor):
        """Test job creation through processor."""
        from surfscreen.batch.batch_processor import BatchProcessor
        
        processor = BatchProcessor(executor_fn=mock_executor)
        
        job = processor.create_job(
            job_type="test",
            tasks=sample_tasks,
            name="Test Batch",
        )
        
        assert job.job_type == "test"
        assert job.name == "Test Batch"
        assert len(job.tasks) == 5
        assert job.batch_id in processor.jobs
    
    def test_get_job(self, sample_tasks, mock_executor):
        """Test retrieving a job."""
        from surfscreen.batch.batch_processor import BatchProcessor
        
        processor = BatchProcessor(executor_fn=mock_executor)
        job = processor.create_job(job_type="test", tasks=sample_tasks)
        
        retrieved = processor.get_job(job.batch_id)
        
        assert retrieved is job
        assert processor.get_job("nonexistent") is None
    
    def test_list_jobs(self, sample_tasks, mock_executor):
        """Test listing jobs with filtering."""
        from surfscreen.batch.batch_processor import BatchProcessor
        from surfscreen.batch.batch_models import BatchJobStatus
        
        processor = BatchProcessor(executor_fn=mock_executor)
        
        job1 = processor.create_job(job_type="test", tasks=sample_tasks[:2])
        job2 = processor.create_job(job_type="test", tasks=sample_tasks[2:])
        
        job1.status = BatchJobStatus.COMPLETED
        
        # List all
        all_jobs = processor.list_jobs()
        assert len(all_jobs) == 2
        
        # Filter by status
        completed = processor.list_jobs(status=BatchJobStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].batch_id == job1.batch_id
    
    def test_run_job_success(self, sample_tasks, mock_executor):
        """Test successful job execution."""
        from surfscreen.batch.batch_processor import BatchProcessor
        from surfscreen.batch.batch_models import BatchJobStatus
        
        processor = BatchProcessor(executor_fn=mock_executor)
        job = processor.create_job(job_type="test", tasks=sample_tasks)
        
        result = processor.run_job(job)
        
        assert job.status == BatchJobStatus.COMPLETED
        assert result.total_tasks == 5
        assert result.successful_tasks == 5
        assert result.failed_tasks == 0
    
    def test_run_job_with_failures(self, sample_tasks):
        """Test job execution with some failures."""
        from surfscreen.batch.batch_processor import BatchProcessor
        from surfscreen.batch.batch_models import BatchJobStatus
        
        call_count = 0
        
        def failing_executor(task):
            nonlocal call_count
            call_count += 1
            if task["id"] == 2:
                raise ValueError("Task failed")
            return {"result": task["value"]}
        
        processor = BatchProcessor(executor_fn=failing_executor)
        job = processor.create_job(job_type="test", tasks=sample_tasks)
        
        result = processor.run_job(job)
        
        # Job should complete (partial success)
        assert result.successful_tasks == 4
        assert result.failed_tasks == 1
    
    def test_cancel_job(self, sample_tasks, mock_executor):
        """Test job cancellation."""
        from surfscreen.batch.batch_processor import BatchProcessor
        from surfscreen.batch.batch_models import BatchJobStatus
        
        processor = BatchProcessor(executor_fn=mock_executor)
        job = processor.create_job(job_type="test", tasks=sample_tasks)
        
        # Cancel pending job
        success = processor.cancel_job(job.batch_id)
        
        assert success is True
        assert job.status == BatchJobStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_run_job_async(self, sample_tasks, mock_executor):
        """Test asynchronous job execution."""
        from surfscreen.batch.batch_processor import BatchProcessor
        from surfscreen.batch.batch_models import BatchJobStatus
        
        processor = BatchProcessor(executor_fn=mock_executor)
        job = processor.create_job(job_type="test", tasks=sample_tasks)
        
        result = await processor.run_job_async(job)
        
        assert job.status == BatchJobStatus.COMPLETED
        assert result.successful_tasks == 5


class TestTaskResult:
    """Tests for TaskResult dataclass."""
    
    def test_success_result(self):
        """Test successful task result."""
        from surfscreen.batch.batch_models import TaskResult
        
        result = TaskResult(
            task_index=0,
            success=True,
            result={"data": "output"},
        )
        
        assert result.success is True
        assert result.error is None
    
    def test_failure_result(self):
        """Test failed task result."""
        from surfscreen.batch.batch_models import TaskResult
        
        result = TaskResult(
            task_index=1,
            success=False,
            error="Something went wrong",
        )
        
        assert result.success is False
        assert result.error == "Something went wrong"


class TestBatchResult:
    """Tests for BatchResult dataclass."""
    
    def test_batch_result_creation(self):
        """Test batch result summary."""
        from surfscreen.batch.batch_models import BatchResult, TaskResult
        
        task_results = [
            TaskResult(task_index=0, success=True, result={"v": 1}),
            TaskResult(task_index=1, success=True, result={"v": 2}),
            TaskResult(task_index=2, success=False, error="Failed"),
        ]
        
        result = BatchResult(
            batch_id="test-123",
            total_tasks=3,
            successful_tasks=2,
            failed_tasks=1,
            task_results=task_results,
        )
        
        assert result.total_tasks == 3
        assert result.successful_tasks == 2
        assert result.failed_tasks == 1
        assert len(result.task_results) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
