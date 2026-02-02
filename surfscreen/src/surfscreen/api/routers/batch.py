"""
Batch API Router

REST API endpoints for batch processing.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List
import logging

from ...batch import (
    BatchProcessor,
    BatchJob,
    BatchConfig,
    BatchJobStatus,
)
from ...batch.batch_models import (
    BatchJobCreate,
    BatchJobResponse,
    BatchListResponse,
    BatchResultsResponse,
)
from ...batch.batch_processor import get_batch_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


# ============================================
# Dependencies
# ============================================

def get_processor() -> BatchProcessor:
    """Dependency to get batch processor."""
    return get_batch_processor()


# ============================================
# Endpoints
# ============================================

@router.post("/submit", response_model=BatchJobResponse)
async def submit_batch_job(
    request: BatchJobCreate,
    background_tasks: BackgroundTasks,
    processor: BatchProcessor = Depends(get_processor),
):
    """
    Submit a new batch job.
    
    Creates a batch job with multiple tasks and starts processing in background.
    """
    # Parse configuration
    config = None
    if request.config:
        config = BatchConfig(**request.config)
    
    # Convert tasks to internal format
    tasks = [
        {
            "molecule_path": task.molecule_path,
            "surface_path": task.surface_path,
            "parameters": task.parameters,
            "engine": request.engine,
        }
        for task in request.tasks
    ]
    
    # Create job
    job = processor.create_job(
        job_type=request.job_type,
        tasks=tasks,
        config=config,
        name=request.name,
    )
    
    # Start processing in background
    background_tasks.add_task(processor.run_job, job)
    
    progress = job.progress
    
    return BatchJobResponse(
        batch_id=job.batch_id,
        name=job.name,
        status=job.status,
        job_type=job.job_type,
        progress=progress.to_dict(),
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@router.get("", response_model=BatchListResponse)
async def list_batch_jobs(
    status: Optional[BatchJobStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    processor: BatchProcessor = Depends(get_processor),
):
    """
    List all batch jobs.
    
    Supports filtering by status and pagination.
    """
    jobs = processor.list_jobs(status=status, limit=page_size * page)
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated = jobs[start:end]
    
    return BatchListResponse(
        batches=[
            BatchJobResponse(
                batch_id=job.batch_id,
                name=job.name,
                status=job.status,
                job_type=job.job_type,
                progress=job.progress.to_dict(),
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error=job.error,
            )
            for job in paginated
        ],
        total=len(jobs),
        page=page,
        page_size=page_size,
    )


@router.get("/{batch_id}", response_model=BatchJobResponse)
async def get_batch_job(
    batch_id: str,
    processor: BatchProcessor = Depends(get_processor),
):
    """
    Get batch job status.
    
    Returns current status and progress of the batch job.
    """
    job = processor.get_job(batch_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    progress = job.progress
    
    return BatchJobResponse(
        batch_id=job.batch_id,
        name=job.name,
        status=job.status,
        job_type=job.job_type,
        progress=progress.to_dict(),
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@router.get("/{batch_id}/results", response_model=BatchResultsResponse)
async def get_batch_results(
    batch_id: str,
    include_pending: bool = Query(False, description="Include pending tasks"),
    include_failed: bool = Query(True, description="Include failed tasks"),
    processor: BatchProcessor = Depends(get_processor),
):
    """
    Get batch job results.
    
    Returns results for completed tasks. Can optionally include pending/failed.
    """
    job = processor.get_job(batch_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    result = job.get_result()
    
    # Filter results
    results = []
    for r in result.results:
        if r.status == "completed":
            results.append({
                "task_id": r.task_id,
                "status": r.status,
                "molecule": r.molecule,
                "surface": r.surface,
                "result": r.result,
                "duration_seconds": r.duration_seconds,
            })
        elif r.status == "failed" and include_failed:
            results.append({
                "task_id": r.task_id,
                "status": r.status,
                "molecule": r.molecule,
                "surface": r.surface,
                "error": r.error,
            })
        elif r.status == "pending" and include_pending:
            results.append({
                "task_id": r.task_id,
                "status": r.status,
                "molecule": r.molecule,
                "surface": r.surface,
            })
    
    return BatchResultsResponse(
        batch_id=batch_id,
        status=job.status,
        progress=result.progress.to_dict(),
        results=results,
        completed_count=result.progress.completed,
        failed_count=result.progress.failed,
    )


@router.delete("/{batch_id}")
async def cancel_batch_job(
    batch_id: str,
    processor: BatchProcessor = Depends(get_processor),
):
    """
    Cancel a batch job.
    
    Stops processing and marks job as cancelled.
    """
    success = processor.cancel_job(batch_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    return {
        "batch_id": batch_id,
        "status": "cancelled",
        "message": "Batch job cancelled",
    }


@router.post("/{batch_id}/resume")
async def resume_batch_job(
    batch_id: str,
    background_tasks: BackgroundTasks,
    processor: BatchProcessor = Depends(get_processor),
):
    """
    Resume a paused or failed batch job.
    
    Continues processing from the last checkpoint.
    """
    job = processor.resume_job(batch_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail="Batch job checkpoint not found")
    
    # Continue processing in background
    background_tasks.add_task(processor.run_job, job)
    
    return BatchJobResponse(
        batch_id=job.batch_id,
        name=job.name,
        status=job.status,
        job_type=job.job_type,
        progress=job.progress.to_dict(),
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@router.get("/{batch_id}/download")
async def download_batch_results(
    batch_id: str,
    format: str = Query("json", enum=["json", "csv"]),
    processor: BatchProcessor = Depends(get_processor),
):
    """
    Download batch results.
    
    Returns results in specified format (JSON or CSV).
    """
    job = processor.get_job(batch_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    if job.status not in [BatchJobStatus.COMPLETED, BatchJobStatus.PARTIAL]:
        raise HTTPException(
            status_code=400,
            detail="Batch job not yet completed"
        )
    
    result = job.get_result()
    
    if format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "task_id", "status", "molecule", "surface", "energy", "error"
        ])
        
        # Data
        for r in result.results:
            energy = r.result.get("energy", "") if r.result else ""
            writer.writerow([
                r.task_id,
                r.status,
                r.molecule,
                r.surface,
                energy,
                r.error or "",
            ])
        
        from fastapi.responses import StreamingResponse
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=batch_{batch_id}.csv"
            }
        )
    
    else:  # JSON
        return result.to_dict()
