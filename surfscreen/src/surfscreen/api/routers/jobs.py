"""
SurfScreen API Jobs Router

Job 관리 엔드포인트
"""

import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from surfscreen.api.models import (
    JobStatus, JobType, JobInfo, JobListResponse
)
from surfscreen.api.dependencies import verify_api_key, get_job_manager_dep
from surfscreen.api.services.job_manager import JobManager


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "",
    response_model=JobListResponse,
    summary="List Jobs",
    description="모든 Job 목록 조회 (필터링 가능)"
)
async def list_jobs(
    status_filter: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    limit: int = 100,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
) -> JobListResponse:
    """
    Job 목록 조회
    
    Query Parameters:
        - status_filter: 상태 필터 (pending, running, completed, failed, cancelled)
        - job_type: 유형 필터 (screening, md, analysis)
        - limit: 최대 반환 수 (기본 100)
    """
    jobs = job_manager.list_jobs(
        status_filter=status_filter,
        job_type_filter=job_type,
        limit=limit
    )
    
    return JobListResponse(total=len(jobs), jobs=jobs)


@router.get(
    "/{job_id}",
    response_model=JobInfo,
    summary="Get Job",
    description="특정 Job 상세 정보 조회"
)
async def get_job(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
) -> JobInfo:
    """Job 상세 정보 조회"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    return job_info


@router.delete(
    "/{job_id}",
    summary="Cancel Job",
    description="실행 중인 Job 취소"
)
async def cancel_job(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
):
    """Job 취소"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    if job_info.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job already {job_info.status.value}"
        )
    
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )
    
    return {"message": f"Job {job_id} cancelled", "job_id": job_id}


@router.get(
    "/{job_id}/result",
    summary="Get Job Result",
    description="Job 결과 JSON 반환"
)
async def get_job_result(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
):
    """Job 결과 조회"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    if job_info.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed. Current status: {job_info.status.value}"
        )
    
    result_path = job_manager.get_job_dir(job_id) / "output" / "results.json"
    
    if not result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found"
        )
    
    import json
    with open(result_path) as f:
        return json.load(f)


@router.get(
    "/{job_id}/download",
    summary="Download Job Results",
    description="Job 결과를 ZIP 파일로 다운로드"
)
async def download_job_results(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
):
    """Job 결과 ZIP 다운로드"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    job_dir = job_manager.get_job_dir(job_id)
    output_dir = job_dir / "output"
    
    if not output_dir.exists() or not any(output_dir.iterdir()):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No output files available"
        )
    
    # ZIP 생성
    zip_path = job_dir / f"{job_id}_results.zip"
    
    if not zip_path.exists():
        shutil.make_archive(
            str(zip_path.with_suffix("")),
            "zip",
            output_dir
        )
    
    return FileResponse(
        path=str(zip_path),
        filename=f"{job_id}_results.zip",
        media_type="application/zip"
    )


@router.get(
    "/{job_id}/logs",
    summary="Get Job Logs",
    description="Job 실행 로그 조회"
)
async def get_job_logs(
    job_id: str,
    tail: int = 100,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
):
    """Job 로그 조회"""
    job_dir = job_manager.get_job_dir(job_id)
    log_path = job_dir / "job.log"
    
    if not log_path.exists():
        return {"logs": "", "lines": 0}
    
    with open(log_path) as f:
        lines = f.readlines()
    
    # tail 적용
    if tail and len(lines) > tail:
        lines = lines[-tail:]
    
    return {
        "logs": "".join(lines),
        "lines": len(lines)
    }
