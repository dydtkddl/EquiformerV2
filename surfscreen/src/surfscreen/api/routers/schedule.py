"""
Schedule API Router

REST API endpoints for job scheduling.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import logging

from ...scheduler import (
    Scheduler,
    get_scheduler,
    ScheduleType,
    ScheduleStatus,
)
from ...scheduler.schedule_models import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    ScheduleHistoryResponse,
    ScheduleHistoryEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


# ============================================
# Dependencies
# ============================================

def get_sched() -> Scheduler:
    """Dependency to get scheduler."""
    return get_scheduler()


# ============================================
# Endpoints
# ============================================

@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleCreate,
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Create a new schedule.
    
    Supports cron, interval, one-time, and dependency-based schedules.
    """
    schedule = scheduler.create_schedule(
        name=request.name,
        schedule_type=request.schedule_type,
        job_type=request.job_type,
        job_config=request.job_config,
        cron_expression=request.cron_expression,
        interval_seconds=request.interval_seconds,
        run_at=request.run_at,
        depends_on=request.depends_on,
        max_runs=request.max_runs,
    )
    
    return ScheduleResponse(
        schedule_id=schedule.schedule_id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        status=schedule.status,
        job_type=schedule.job_config.get("job_type", "unknown"),
        next_run=schedule.next_run,
        last_run=schedule.last_run,
        run_count=schedule.run_count,
        max_runs=schedule.max_runs,
        cron_expression=schedule.cron_expression,
        interval_seconds=schedule.interval_seconds,
        created_at=schedule.created_at,
    )


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    status: Optional[ScheduleStatus] = Query(None),
    schedule_type: Optional[ScheduleType] = Query(None),
    scheduler: Scheduler = Depends(get_sched),
):
    """
    List all schedules.
    
    Supports filtering by status and schedule type.
    """
    schedules = scheduler.list_schedules(
        status=status,
        schedule_type=schedule_type,
    )
    
    return ScheduleListResponse(
        schedules=[
            ScheduleResponse(
                schedule_id=s.schedule_id,
                name=s.name,
                schedule_type=s.schedule_type,
                status=s.status,
                job_type=s.job_config.get("job_type", "unknown"),
                next_run=s.next_run,
                last_run=s.last_run,
                run_count=s.run_count,
                max_runs=s.max_runs,
                cron_expression=s.cron_expression,
                interval_seconds=s.interval_seconds,
                created_at=s.created_at,
            )
            for s in schedules
        ],
        total=len(schedules),
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Get schedule by ID.
    """
    schedule = scheduler.get_schedule(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return ScheduleResponse(
        schedule_id=schedule.schedule_id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        status=schedule.status,
        job_type=schedule.job_config.get("job_type", "unknown"),
        next_run=schedule.next_run,
        last_run=schedule.last_run,
        run_count=schedule.run_count,
        max_runs=schedule.max_runs,
        cron_expression=schedule.cron_expression,
        interval_seconds=schedule.interval_seconds,
        created_at=schedule.created_at,
    )


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    request: ScheduleUpdate,
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Update a schedule.
    """
    schedule = scheduler.update_schedule(
        schedule_id=schedule_id,
        name=request.name,
        cron_expression=request.cron_expression,
        interval_seconds=request.interval_seconds,
        run_at=request.run_at,
        max_runs=request.max_runs,
        job_config=request.job_config,
    )
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return ScheduleResponse(
        schedule_id=schedule.schedule_id,
        name=schedule.name,
        schedule_type=schedule.schedule_type,
        status=schedule.status,
        job_type=schedule.job_config.get("job_type", "unknown"),
        next_run=schedule.next_run,
        last_run=schedule.last_run,
        run_count=schedule.run_count,
        max_runs=schedule.max_runs,
        cron_expression=schedule.cron_expression,
        interval_seconds=schedule.interval_seconds,
        created_at=schedule.created_at,
    )


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Delete a schedule.
    """
    success = scheduler.delete_schedule(schedule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"deleted": True, "schedule_id": schedule_id}


@router.post("/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: str,
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Pause a schedule.
    """
    success = scheduler.pause_schedule(schedule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"status": "paused", "schedule_id": schedule_id}


@router.post("/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: str,
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Resume a paused schedule.
    """
    success = scheduler.resume_schedule(schedule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"status": "active", "schedule_id": schedule_id}


@router.get("/{schedule_id}/history", response_model=ScheduleHistoryResponse)
async def get_schedule_history(
    schedule_id: str,
    limit: int = Query(50, ge=1, le=500),
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Get execution history for a schedule.
    """
    schedule = scheduler.get_schedule(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    history = scheduler.get_history(schedule_id, limit=limit)
    
    return ScheduleHistoryResponse(
        schedule_id=schedule_id,
        history=[
            ScheduleHistoryEntry(
                execution_id=h.get("execution_id", ""),
                started_at=h.get("started_at", ""),
                completed_at=h.get("completed_at"),
                status=h.get("status", "unknown"),
                result=h.get("result"),
                error=h.get("error"),
            )
            for h in history
        ],
        total=len(history),
    )


@router.post("/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: str,
    scheduler: Scheduler = Depends(get_sched),
):
    """
    Manually trigger a schedule to run immediately.
    """
    schedule = scheduler.get_schedule(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if schedule.status != ScheduleStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Schedule is {schedule.status.value}, cannot trigger"
        )
    
    # Execute immediately
    scheduler._execute_scheduled_job(schedule_id)
    
    return {
        "triggered": True,
        "schedule_id": schedule_id,
        "message": "Schedule triggered for immediate execution",
    }
