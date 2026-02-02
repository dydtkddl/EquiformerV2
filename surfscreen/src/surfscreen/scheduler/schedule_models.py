"""
Schedule Models

Pydantic models and dataclasses for job scheduling.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class ScheduleType(str, Enum):
    """Type of schedule."""
    
    CRON = "cron"      # Cron expression
    INTERVAL = "interval"  # Fixed interval
    ONCE = "once"      # One-time execution
    DEPENDENCY = "dependency"  # After another job


class ScheduleStatus(str, Enum):
    """Schedule status."""
    
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"  # For one-time schedules
    FAILED = "failed"


@dataclass
class ScheduledJob:
    """Scheduled job information."""
    
    schedule_id: str
    name: str
    schedule_type: ScheduleType
    status: ScheduleStatus
    job_config: Dict[str, Any]
    
    # Schedule parameters
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[str] = None  # ISO format
    depends_on: Optional[str] = None  # Job ID to wait for
    
    # Execution tracking
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None = unlimited
    
    # Results
    last_result: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "schedule_type": self.schedule_type.value,
            "status": self.status.value,
            "job_config": self.job_config,
            "cron_expression": self.cron_expression,
            "interval_seconds": self.interval_seconds,
            "run_at": self.run_at,
            "depends_on": self.depends_on,
            "next_run": self.next_run,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ============================================
# Pydantic Models for API
# ============================================

class ScheduleCreate(BaseModel):
    """Request model for creating a schedule."""
    
    name: str = Field(..., min_length=1, max_length=256)
    schedule_type: ScheduleType = Field(..., description="Type of schedule")
    job_type: str = Field(..., description="Job type: 'screening', 'md', or 'batch'")
    job_config: Dict[str, Any] = Field(..., description="Job configuration")
    
    # Schedule parameters (one required based on type)
    cron_expression: Optional[str] = Field(
        None,
        description="Cron expression (e.g., '0 0 * * *' for daily at midnight)"
    )
    interval_seconds: Optional[int] = Field(
        None,
        ge=60,
        description="Interval in seconds (minimum 60)"
    )
    run_at: Optional[str] = Field(
        None,
        description="ISO datetime for one-time execution"
    )
    depends_on: Optional[str] = Field(
        None,
        description="Job ID to wait for before running"
    )
    
    max_runs: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum number of runs (None = unlimited)"
    )
    
    @validator("cron_expression")
    def validate_cron(cls, v, values):
        if values.get("schedule_type") == ScheduleType.CRON and not v:
            raise ValueError("cron_expression required for cron schedule")
        return v
    
    @validator("interval_seconds")
    def validate_interval(cls, v, values):
        if values.get("schedule_type") == ScheduleType.INTERVAL and not v:
            raise ValueError("interval_seconds required for interval schedule")
        return v
    
    @validator("run_at")
    def validate_run_at(cls, v, values):
        if values.get("schedule_type") == ScheduleType.ONCE and not v:
            raise ValueError("run_at required for one-time schedule")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Daily CO Screening",
                "schedule_type": "cron",
                "job_type": "screening",
                "job_config": {
                    "molecule_path": "co.xyz",
                    "surface_path": "cu111.xyz",
                    "engine": "mace",
                },
                "cron_expression": "0 0 * * *",
                "max_runs": 30,
            }
        }


class ScheduleUpdate(BaseModel):
    """Request model for updating a schedule."""
    
    name: Optional[str] = Field(None, max_length=256)
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = Field(None, ge=60)
    run_at: Optional[str] = None
    max_runs: Optional[int] = Field(None, ge=1)
    job_config: Optional[Dict[str, Any]] = None


class ScheduleResponse(BaseModel):
    """Response model for schedule."""
    
    schedule_id: str
    name: str
    schedule_type: ScheduleType
    status: ScheduleStatus
    job_type: str
    next_run: Optional[str]
    last_run: Optional[str]
    run_count: int
    max_runs: Optional[int]
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    created_at: str


class ScheduleListResponse(BaseModel):
    """Response model for schedule list."""
    
    schedules: List[ScheduleResponse]
    total: int


class ScheduleHistoryEntry(BaseModel):
    """Schedule execution history entry."""
    
    execution_id: str
    started_at: str
    completed_at: Optional[str]
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]


class ScheduleHistoryResponse(BaseModel):
    """Response model for schedule history."""
    
    schedule_id: str
    history: List[ScheduleHistoryEntry]
    total: int
