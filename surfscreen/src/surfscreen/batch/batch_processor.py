"""
Batch Processor

Core batch processing engine for handling multiple calculations.
"""

import asyncio
import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

from .batch_models import (
    BatchConfig,
    BatchJobStatus,
    BatchProgress,
    BatchResult,
    TaskResult,
)

logger = logging.getLogger(__name__)


class BatchJob:
    """
    Represents a batch job with multiple tasks.
    
    Manages the lifecycle of batch processing including
    progress tracking, checkpointing, and result aggregation.
    """
    
    def __init__(
        self,
        batch_id: str,
        job_type: str,
        tasks: List[Dict[str, Any]],
        config: Optional[BatchConfig] = None,
        name: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize batch job.
        
        Args:
            batch_id: Unique batch identifier
            job_type: Type of job ('screening' or 'md')
            tasks: List of task definitions
            config: Batch configuration
            name: Optional batch name
            output_dir: Output directory for results
        """
        self.batch_id = batch_id
        self.job_type = job_type
        self.name = name or f"Batch-{batch_id[:8]}"
        self.config = config or BatchConfig()
        self.output_dir = output_dir or Path.cwd() / "batch_results" / batch_id
        
        # Initialize tasks
        self.tasks: List[Dict[str, Any]] = []
        for i, task in enumerate(tasks):
            self.tasks.append({
                "task_id": f"{batch_id}-{i:04d}",
                "index": i,
                "status": "pending",
                "input": task,
                "result": None,
                "error": None,
                "retries": 0,
                "started_at": None,
                "completed_at": None,
            })
        
        # State
        self.status = BatchJobStatus.PENDING
        self.created_at = datetime.utcnow().isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None
        
        # Thread safety
        self._lock = Lock()
        self._cancelled = False
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def progress(self) -> BatchProgress:
        """Get current progress."""
        with self._lock:
            total = len(self.tasks)
            completed = sum(1 for t in self.tasks if t["status"] == "completed")
            failed = sum(1 for t in self.tasks if t["status"] == "failed")
            running = sum(1 for t in self.tasks if t["status"] == "running")
            pending = sum(1 for t in self.tasks if t["status"] == "pending")
            
            return BatchProgress(
                total=total,
                completed=completed,
                failed=failed,
                pending=pending,
                running=running,
            )
    
    def get_result(self) -> BatchResult:
        """Get batch result."""
        with self._lock:
            results = [
                TaskResult(
                    task_id=t["task_id"],
                    status=t["status"],
                    molecule=t["input"].get("molecule_path", ""),
                    surface=t["input"].get("surface_path", ""),
                    result=t.get("result"),
                    error=t.get("error"),
                    duration_seconds=self._calculate_duration(t),
                    started_at=t.get("started_at"),
                    completed_at=t.get("completed_at"),
                )
                for t in self.tasks
            ]
            
            return BatchResult(
                batch_id=self.batch_id,
                status=self.status,
                progress=self.progress,
                results=results,
                created_at=self.created_at,
                started_at=self.started_at,
                completed_at=self.completed_at,
                config=self.config,
                error=self.error,
            )
    
    def _calculate_duration(self, task: Dict[str, Any]) -> float:
        """Calculate task duration in seconds."""
        started = task.get("started_at")
        completed = task.get("completed_at")
        
        if not started or not completed:
            return 0.0
        
        try:
            start = datetime.fromisoformat(started)
            end = datetime.fromisoformat(completed)
            return (end - start).total_seconds()
        except Exception:
            return 0.0
    
    def update_task(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Update task status and result."""
        with self._lock:
            for task in self.tasks:
                if task["task_id"] == task_id:
                    task["status"] = status
                    
                    if status == "running":
                        task["started_at"] = datetime.utcnow().isoformat()
                    elif status in ["completed", "failed"]:
                        task["completed_at"] = datetime.utcnow().isoformat()
                    
                    if result is not None:
                        task["result"] = result
                    
                    if error is not None:
                        task["error"] = error
                        task["retries"] += 1
                    
                    break
        
        # Save checkpoint
        if self.config.save_partial:
            self._save_checkpoint()
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get list of pending tasks."""
        with self._lock:
            return [t for t in self.tasks if t["status"] == "pending"]
    
    def get_failed_tasks(self) -> List[Dict[str, Any]]:
        """Get list of failed tasks eligible for retry."""
        with self._lock:
            return [
                t for t in self.tasks
                if t["status"] == "failed" and t["retries"] < self.config.max_retries
            ]
    
    def cancel(self):
        """Cancel the batch job."""
        with self._lock:
            self._cancelled = True
            self.status = BatchJobStatus.CANCELLED
            self.completed_at = datetime.utcnow().isoformat()
        
        self._save_checkpoint()
    
    @property
    def is_cancelled(self) -> bool:
        """Check if batch is cancelled."""
        return self._cancelled
    
    def _save_checkpoint(self):
        """Save checkpoint to disk."""
        checkpoint_path = self.output_dir / "checkpoint.json"
        
        try:
            data = {
                "batch_id": self.batch_id,
                "name": self.name,
                "job_type": self.job_type,
                "status": self.status.value,
                "config": self.config.to_dict(),
                "created_at": self.created_at,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "tasks": self.tasks,
            }
            
            with open(checkpoint_path, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
    
    @classmethod
    def load_from_checkpoint(cls, checkpoint_path: Path) -> "BatchJob":
        """Load batch job from checkpoint."""
        with open(checkpoint_path) as f:
            data = json.load(f)
        
        config = BatchConfig(**data.get("config", {}))
        
        job = cls(
            batch_id=data["batch_id"],
            job_type=data["job_type"],
            tasks=[t["input"] for t in data["tasks"]],
            config=config,
            name=data.get("name"),
            output_dir=checkpoint_path.parent,
        )
        
        # Restore task states
        for i, task_data in enumerate(data["tasks"]):
            job.tasks[i].update(task_data)
        
        job.status = BatchJobStatus(data["status"])
        job.created_at = data["created_at"]
        job.started_at = data.get("started_at")
        job.completed_at = data.get("completed_at")
        
        return job


class BatchProcessor:
    """
    Batch processor for running multiple calculations.
    
    Supports parallel execution, progress tracking, checkpointing,
    and error handling with retries.
    """
    
    def __init__(
        self,
        executor_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize batch processor.
        
        Args:
            executor_fn: Function to execute individual tasks
            output_dir: Base output directory
        """
        self.executor_fn = executor_fn or self._default_executor
        self.output_dir = output_dir or Path.cwd() / "batch_results"
        self.active_jobs: Dict[str, BatchJob] = {}
        self._lock = Lock()
    
    def create_job(
        self,
        job_type: str,
        tasks: List[Dict[str, Any]],
        config: Optional[BatchConfig] = None,
        name: Optional[str] = None,
    ) -> BatchJob:
        """
        Create a new batch job.
        
        Args:
            job_type: Type of job
            tasks: List of task definitions
            config: Batch configuration
            name: Optional job name
            
        Returns:
            Created BatchJob instance
        """
        batch_id = str(uuid.uuid4())
        job_dir = self.output_dir / batch_id
        
        job = BatchJob(
            batch_id=batch_id,
            job_type=job_type,
            tasks=tasks,
            config=config,
            name=name,
            output_dir=job_dir,
        )
        
        with self._lock:
            self.active_jobs[batch_id] = job
        
        logger.info(f"Created batch job: {batch_id} ({len(tasks)} tasks)")
        
        return job
    
    def get_job(self, batch_id: str) -> Optional[BatchJob]:
        """Get batch job by ID."""
        with self._lock:
            return self.active_jobs.get(batch_id)
    
    def list_jobs(
        self,
        status: Optional[BatchJobStatus] = None,
        limit: int = 100,
    ) -> List[BatchJob]:
        """List batch jobs with optional filtering."""
        with self._lock:
            jobs = list(self.active_jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return jobs[:limit]
    
    def run_job(self, job: BatchJob) -> BatchResult:
        """
        Run batch job synchronously.
        
        Args:
            job: BatchJob to run
            
        Returns:
            BatchResult with all task results
        """
        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.utcnow().isoformat()
        
        logger.info(f"Starting batch job: {job.batch_id} ({job.progress.total} tasks)")
        
        try:
            # Process tasks in chunks
            pending = job.get_pending_tasks()
            
            with ThreadPoolExecutor(max_workers=job.config.max_workers) as executor:
                while pending and not job.is_cancelled:
                    # Submit chunk
                    chunk = pending[:job.config.chunk_size]
                    futures = {
                        executor.submit(self._execute_task, job, task): task
                        for task in chunk
                    }
                    
                    # Wait for chunk completion
                    for future in as_completed(futures):
                        task = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Task {task['task_id']} failed: {e}")
                    
                    # Get next pending tasks (including retries)
                    pending = job.get_pending_tasks()
                    
                    # Add failed tasks for retry
                    if job.config.retry_failed:
                        for failed in job.get_failed_tasks():
                            failed["status"] = "pending"
                            pending.append(failed)
            
            # Determine final status
            progress = job.progress
            
            if job.is_cancelled:
                job.status = BatchJobStatus.CANCELLED
            elif progress.failed > 0 and progress.completed > 0:
                job.status = BatchJobStatus.PARTIAL
            elif progress.failed == progress.total:
                job.status = BatchJobStatus.FAILED
            else:
                job.status = BatchJobStatus.COMPLETED
            
            job.completed_at = datetime.utcnow().isoformat()
            
            logger.info(
                f"Batch job completed: {job.batch_id} "
                f"({progress.completed}/{progress.total} succeeded)"
            )
            
        except Exception as e:
            job.status = BatchJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow().isoformat()
            logger.error(f"Batch job failed: {job.batch_id} - {e}")
        
        # Save final checkpoint
        job._save_checkpoint()
        
        return job.get_result()
    
    async def run_job_async(self, job: BatchJob) -> BatchResult:
        """
        Run batch job asynchronously.
        
        Args:
            job: BatchJob to run
            
        Returns:
            BatchResult with all task results
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run_job, job)
    
    def _execute_task(self, job: BatchJob, task: Dict[str, Any]):
        """Execute a single task."""
        task_id = task["task_id"]
        
        # Mark as running
        job.update_task(task_id, "running")
        
        try:
            # Execute
            result = self.executor_fn(task["input"])
            
            # Mark as completed
            job.update_task(task_id, "completed", result=result)
            
            logger.debug(f"Task completed: {task_id}")
            
        except Exception as e:
            # Mark as failed
            job.update_task(task_id, "failed", error=str(e))
            
            if not job.config.continue_on_error:
                raise
            
            logger.warning(f"Task failed: {task_id} - {e}")
    
    def _default_executor(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """Default task executor (placeholder)."""
        # This should be overridden with actual calculation logic
        import time
        time.sleep(0.1)  # Simulate work
        
        return {
            "status": "completed",
            "molecule": task_input.get("molecule_path", ""),
            "surface": task_input.get("surface_path", ""),
            "energy": -1.0,  # Placeholder
        }
    
    def cancel_job(self, batch_id: str) -> bool:
        """Cancel a batch job."""
        job = self.get_job(batch_id)
        
        if job is None:
            return False
        
        job.cancel()
        logger.info(f"Cancelled batch job: {batch_id}")
        
        return True
    
    def resume_job(self, batch_id: str) -> Optional[BatchJob]:
        """
        Resume a batch job from checkpoint.
        
        Args:
            batch_id: Batch ID to resume
            
        Returns:
            Resumed BatchJob or None if not found
        """
        checkpoint_path = self.output_dir / batch_id / "checkpoint.json"
        
        if not checkpoint_path.exists():
            return None
        
        job = BatchJob.load_from_checkpoint(checkpoint_path)
        
        with self._lock:
            self.active_jobs[batch_id] = job
        
        logger.info(f"Resumed batch job: {batch_id} ({job.progress.pending} pending)")
        
        return job


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get or create global batch processor instance."""
    global _batch_processor
    
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    
    return _batch_processor
