"""
Batch Processing Models

Pydantic models and dataclasses for batch processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class BatchJobStatus(str, Enum):
    """Batch job status enumeration."""
    
    PENDING = "pending"
    RUNNING = "running"
    PARTIAL = "partial"  # Some tasks completed, some pending/failed
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchPriority(str, Enum):
    """Batch job priority levels."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    
    max_workers: int = 4
    chunk_size: int = 10
    priority: BatchPriority = BatchPriority.NORMAL
    timeout_per_task: int = 3600  # seconds
    retry_failed: bool = True
    max_retries: int = 3
    save_partial: bool = True
    continue_on_error: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_workers": self.max_workers,
            "chunk_size": self.chunk_size,
            "priority": self.priority.value,
            "timeout_per_task": self.timeout_per_task,
            "retry_failed": self.retry_failed,
            "max_retries": self.max_retries,
            "save_partial": self.save_partial,
            "continue_on_error": self.continue_on_error,
        }


@dataclass
class BatchProgress:
    """Batch job progress tracking."""
    
    total: int = 0
    completed: int = 0
    failed: int = 0
    pending: int = 0
    running: int = 0
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total == 0:
            return 0.0
        return ((self.completed + self.failed) / self.total) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        done = self.completed + self.failed
        if done == 0:
            return 0.0
        return (self.completed / done) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "pending": self.pending,
            "running": self.running,
            "percentage": round(self.percentage, 1),
            "success_rate": round(self.success_rate, 1),
        }


@dataclass
class TaskResult:
    """Individual task result within a batch."""
    
    task_id: str
    status: str  # "completed", "failed", "pending", "running"
    molecule: str
    surface: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class BatchResult:
    """Complete batch job result."""
    
    batch_id: str
    status: BatchJobStatus
    progress: BatchProgress
    results: List[TaskResult] = field(default_factory=list)
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    config: Optional[BatchConfig] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "results": [
                {
                    "task_id": r.task_id,
                    "status": r.status,
                    "molecule": r.molecule,
                    "surface": r.surface,
                    "result": r.result,
                    "error": r.error,
                    "duration_seconds": r.duration_seconds,
                }
                for r in self.results
            ],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


# ============================================
# Pydantic Models for API
# ============================================

class TaskInput(BaseModel):
    """Single task input for batch."""
    
    molecule_path: str = Field(..., description="Path or ID of molecule")
    surface_path: Optional[str] = Field(None, description="Path or ID of surface")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BatchJobCreate(BaseModel):
    """Request model for creating a batch job."""
    
    name: Optional[str] = Field(None, max_length=256, description="Batch job name")
    job_type: str = Field(..., description="Job type: 'screening' or 'md'")
    tasks: List[TaskInput] = Field(..., min_items=1, max_items=1000)
    engine: str = Field("emt", description="Calculator engine")
    config: Optional[Dict[str, Any]] = Field(None, description="Batch configuration")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "CO Screening on Cu Surfaces",
                "job_type": "screening",
                "tasks": [
                    {"molecule_path": "co.xyz", "surface_path": "cu111.xyz"},
                    {"molecule_path": "co.xyz", "surface_path": "cu100.xyz"},
                ],
                "engine": "mace",
                "config": {"max_workers": 4},
            }
        }


class BatchJobResponse(BaseModel):
    """Response model for batch job."""
    
    batch_id: str
    name: Optional[str]
    status: BatchJobStatus
    job_type: str
    progress: Dict[str, Any]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]


class BatchListResponse(BaseModel):
    """Response model for batch list."""
    
    batches: List[BatchJobResponse]
    total: int
    page: int
    page_size: int


class BatchResultsResponse(BaseModel):
    """Response model for batch results."""
    
    batch_id: str
    status: BatchJobStatus
    progress: Dict[str, Any]
    results: List[Dict[str, Any]]
    completed_count: int
    failed_count: int
