"""
SurfScreen API MD Router

분자 동역학 시뮬레이션 엔드포인트
"""

import asyncio
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse

from surfscreen.api.models import (
    JobType, JobStatus, JobCreateResponse, MDConfig as MDConfigModel, MDResult
)
from surfscreen.api.dependencies import verify_api_key, get_job_manager_dep
from surfscreen.api.services.job_manager import JobManager


router = APIRouter(prefix="/md", tags=["MD Simulation"])


async def run_md_task(job_id: str, job_manager: JobManager):
    """백그라운드 MD 시뮬레이션 실행"""
    import traceback
    
    try:
        job_manager.update_job_status(job_id, status=JobStatus.RUNNING, progress=0)
        
        job_dir = job_manager.get_job_dir(job_id)
        input_dir = job_dir / "input"
        output_dir = job_dir / "output"
        
        # 요청 데이터 로드
        with open(job_dir / "request.json") as f:
            request = json.load(f)
        
        config_data = request.get("config", {})
        
        # Structure 파일 찾기
        structure_files = list(input_dir.glob("structure_*"))
        if not structure_files:
            raise ValueError("No structure file found")
        
        structure_path = structure_files[0]
        
        job_manager.update_job_status(job_id, progress=5)
        
        # MD 실행 (CPU-bound 작업이므로 thread에서 실행)
        def run_md_sync():
            from ase.io import read
            from surfscreen.md import MDEngine, MDConfig
            
            atoms = read(str(structure_path))
            
            md_config = MDConfig(
                ensemble=config_data.get("ensemble", "nvt"),
                temperature=config_data.get("temperature", 300.0),
                pressure=config_data.get("pressure", 1.0),
                timestep=config_data.get("timestep", 1.0),
                steps=config_data.get("steps", 10000),
                thermostat=config_data.get("thermostat", "langevin"),
                engine=config_data.get("engine", "mace"),
                model=config_data.get("model", "medium"),
                device=config_data.get("device", "cuda")
            )
            
            md_engine = MDEngine(atoms, md_config, str(output_dir))
            
            # 진행률 콜백
            total_steps = md_config.steps
            
            def progress_callback(step):
                progress = 5 + (step / total_steps) * 90
                job_manager.update_job_status(job_id, progress=progress)
            
            # MD 실행
            summary = md_engine.run(progress_callback=progress_callback)
            
            return summary
        
        # Thread에서 실행
        summary = await asyncio.to_thread(run_md_sync)
        
        # 결과 저장
        results_data = {
            "total_steps": summary.get("total_steps", 0),
            "total_time_fs": summary.get("total_time_fs", 0),
            "avg_temperature": summary.get("avg_temperature_K", 0),
            "final_energy": summary.get("final_energy_eV", 0),
            "trajectory_frames": summary.get("saved_frames", 0)
        }
        
        with open(output_dir / "results.json", "w") as f:
            json.dump(results_data, f, indent=2)
        
        job_manager.update_job_status(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result_path=str(output_dir / "results.json")
        )
        
    except Exception as e:
        job_manager.update_job_status(
            job_id,
            status=JobStatus.FAILED,
            error_message=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        )


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create MD Job",
    description="새 MD 시뮬레이션 Job 생성 및 백그라운드 실행"
)
async def create_md_job(
    background_tasks: BackgroundTasks,
    structure: UploadFile = File(..., description="Initial structure file"),
    config: str = Form(default="{}", description="MD config JSON"),
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
) -> JobCreateResponse:
    """
    MD Job 생성
    
    - structure: 초기 구조 파일
    - config: MD 설정 (JSON 문자열)
    
    Returns:
        job_id, status, message
    """
    try:
        config_dict = json.loads(config)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid config JSON"
        )
    
    # Job 생성
    job_id = job_manager.create_job(
        JobType.MD,
        request_data={"config": config_dict}
    )
    
    job_dir = job_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"
    
    # 파일 저장
    structure_ext = Path(structure.filename).suffix or ".xyz"
    structure_path = input_dir / f"structure_001{structure_ext}"
    with open(structure_path, "wb") as f:
        f.write(await structure.read())
    
    # 백그라운드 실행
    background_tasks.add_task(run_md_task, job_id, job_manager)
    
    return JobCreateResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="MD job created. Use GET /jobs/{job_id} to check status."
    )


@router.get(
    "/{job_id}/result",
    response_model=MDResult,
    summary="Get MD Result",
    description="MD 시뮬레이션 결과 조회"
)
async def get_md_result(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
) -> MDResult:
    """MD 결과 조회"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_info.job_type != JobType.MD:
        raise HTTPException(status_code=400, detail="Not an MD job")
    
    if job_info.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job not completed: {job_info.status.value}")
    
    result_path = job_manager.get_job_dir(job_id) / "output" / "results.json"
    
    with open(result_path) as f:
        data = json.load(f)
    
    from datetime import datetime
    
    return MDResult(
        job_id=job_id,
        total_steps=data.get("total_steps", 0),
        total_time_fs=data.get("total_time_fs", 0),
        avg_temperature=data.get("avg_temperature", 0),
        final_energy=data.get("final_energy", 0),
        trajectory_frames=data.get("trajectory_frames", 0),
        completed_at=job_info.completed_at or datetime.utcnow()
    )


@router.get(
    "/{job_id}/trajectory",
    summary="Download Trajectory",
    description="MD 궤적 파일 다운로드"
)
async def download_trajectory(
    job_id: str,
    format: str = "extxyz",
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
):
    """궤적 파일 다운로드"""
    output_dir = job_manager.get_job_dir(job_id) / "output"
    
    # 파일 형식에 따라 경로 결정
    if format == "extxyz":
        traj_path = output_dir / "trajectory.extxyz"
    elif format == "xyz":
        traj_path = output_dir / "trajectory.xyz"
    elif format == "traj":
        traj_path = output_dir / "trajectory.traj"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    if not traj_path.exists():
        raise HTTPException(status_code=404, detail="Trajectory file not found")
    
    return FileResponse(
        path=str(traj_path),
        filename=f"{job_id}_trajectory.{format}",
        media_type="application/octet-stream"
    )


@router.get(
    "/{job_id}/report",
    summary="Generate MD Report",
    description="MD 결과 HTML 리포트 생성"
)
async def generate_md_report(
    job_id: str,
    theme: str = "dark",
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
):
    """MD 리포트 생성"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info or job_info.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    output_dir = job_manager.get_job_dir(job_id) / "output"
    report_path = output_dir / "md_report.html"
    
    # 리포트 생성
    if not report_path.exists():
        from surfscreen.report import MDReportGenerator
        gen = MDReportGenerator(str(output_dir), theme=theme)
        gen.generate(str(report_path))
    
    return FileResponse(
        path=str(report_path),
        media_type="text/html",
        filename=f"{job_id}_md_report.html"
    )
