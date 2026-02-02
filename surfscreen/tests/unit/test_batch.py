"""
Unit Tests for Batch Module

Tests BatchJob, BatchProcessor, and batch models.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile


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
        assert config.timeout_per_task == 3600
    
    def test_custom_config(self):
        """Test custom batch configuration."""
        from surfscreen.batch.batch_models import BatchConfig, BatchPriority
        
        config = BatchConfig(
            max_workers=8,
            chunk_size=20,
            max_retries=5,
            timeout_per_task=300,
            priority=BatchPriority.HIGH,
        )
        
        assert config.max_workers == 8
        assert config.chunk_size == 20
        assert config.timeout_per_task == 300
        assert config.priority == BatchPriority.HIGH
    
    def test_config_to_dict(self):
        """Test config serialization."""
        from surfscreen.batch.batch_models import BatchConfig
        
        config = BatchConfig()
        data = config.to_dict()
        
        assert "max_workers" in data
        assert "priority" in data


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
    
    def test_success_rate(self):
        """Test success rate calculation."""
        from surfscreen.batch.batch_models import BatchProgress
        
        progress = BatchProgress(total=100, completed=80, failed=20)
        
        assert progress.success_rate == 80.0


class TestBatchJob:
    """Tests for BatchJob class."""
    
    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            {"molecule_path": "mol1.xyz", "surface_path": "surf1.cif"},
            {"molecule_path": "mol2.xyz", "surface_path": "surf2.cif"},
            {"molecule_path": "mol3.xyz", "surface_path": "surf3.cif"},
        ]
    
    def test_job_creation(self, sample_tasks):
        """Test batch job creation."""
        from surfscreen.batch.batch_processor import BatchJob
        from surfscreen.batch.batch_models import BatchJobStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            job = BatchJob(
                batch_id="test-123",
                job_type="screening",
                tasks=sample_tasks,
                output_dir=Path(tmpdir),
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
        
        with tempfile.TemporaryDirectory() as tmpdir:
            job = BatchJob(
                batch_id="test-123",
                job_type="screening",
                tasks=sample_tasks,
                output_dir=Path(tmpdir),
            )
            
            # PENDING -> RUNNING
            job.status = BatchJobStatus.RUNNING
            assert job.status == BatchJobStatus.RUNNING
            
            # RUNNING -> COMPLETED
            job.status = BatchJobStatus.COMPLETED
            assert job.status == BatchJobStatus.COMPLETED
    
    def test_job_progress(self, sample_tasks):
        """Test progress tracking."""
        from surfscreen.batch.batch_processor import BatchJob
        
        with tempfile.TemporaryDirectory() as tmpdir:
            job = BatchJob(
                batch_id="test-123",
                job_type="screening",
                tasks=sample_tasks,
                output_dir=Path(tmpdir),
            )
            
            progress = job.progress
            assert progress.total == 3
            assert progress.pending == 3
            assert progress.completed == 0


class TestBatchProcessor:
    """Tests for BatchProcessor class."""
    
    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks."""
        return [
            {"molecule_path": f"mol{i}.xyz", "surface_path": f"surf{i}.cif"}
            for i in range(5)
        ]
    
    @pytest.fixture
    def mock_executor(self):
        """Create a mock executor function."""
        def executor(task):
            return {"result": "success", "molecule": task.get("molecule_path")}
        return executor
    
    def test_processor_creation(self, mock_executor):
        """Test batch processor creation."""
        from surfscreen.batch.batch_processor import BatchProcessor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = BatchProcessor(
                executor_fn=mock_executor,
                output_dir=Path(tmpdir),
            )
            
            assert processor.executor_fn == mock_executor
            assert len(processor.active_jobs) == 0
    
    def test_create_job(self, sample_tasks, mock_executor):
        """Test job creation through processor."""
        from surfscreen.batch.batch_processor import BatchProcessor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = BatchProcessor(
                executor_fn=mock_executor,
                output_dir=Path(tmpdir),
            )
            
            job = processor.create_job(
                job_type="test",
                tasks=sample_tasks,
                name="Test Batch",
            )
            
            assert job.job_type == "test"
            assert job.name == "Test Batch"
            assert len(job.tasks) == 5
            assert job.batch_id in processor.active_jobs
    
    def test_get_job(self, sample_tasks, mock_executor):
        """Test retrieving a job."""
        from surfscreen.batch.batch_processor import BatchProcessor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = BatchProcessor(
                executor_fn=mock_executor,
                output_dir=Path(tmpdir),
            )
            job = processor.create_job(job_type="test", tasks=sample_tasks)
            
            retrieved = processor.get_job(job.batch_id)
            
            assert retrieved is job
            assert processor.get_job("nonexistent") is None
    
    def test_list_jobs(self, sample_tasks, mock_executor):
        """Test listing jobs with filtering."""
        from surfscreen.batch.batch_processor import BatchProcessor
        from surfscreen.batch.batch_models import BatchJobStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = BatchProcessor(
                executor_fn=mock_executor,
                output_dir=Path(tmpdir),
            )
            
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
    
    def test_cancel_job(self, sample_tasks, mock_executor):
        """Test job cancellation."""
        from surfscreen.batch.batch_processor import BatchProcessor
        from surfscreen.batch.batch_models import BatchJobStatus
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = BatchProcessor(
                executor_fn=mock_executor,
                output_dir=Path(tmpdir),
            )
            job = processor.create_job(job_type="test", tasks=sample_tasks)
            
            # Cancel pending job
            success = processor.cancel_job(job.batch_id)
            
            assert success is True
            assert job.status == BatchJobStatus.CANCELLED


class TestTaskResult:
    """Tests for TaskResult dataclass."""
    
    def test_success_result(self):
        """Test successful task result."""
        from surfscreen.batch.batch_models import TaskResult
        
        result = TaskResult(
            task_id="task-001",
            status="completed",
            molecule="mol1.xyz",
            surface="surf1.cif",
            result={"energy": -1.5},
        )
        
        assert result.status == "completed"
        assert result.error is None
    
    def test_failure_result(self):
        """Test failed task result."""
        from surfscreen.batch.batch_models import TaskResult
        
        result = TaskResult(
            task_id="task-002",
            status="failed",
            molecule="mol2.xyz",
            surface="surf2.cif",
            error="Something went wrong",
        )
        
        assert result.status == "failed"
        assert result.error == "Something went wrong"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
