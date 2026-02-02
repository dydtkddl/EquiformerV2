"""
SurfScreen API Screening Router

흡착 스크리닝 엔드포인트
"""

import asyncio
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse

from surfscreen.api.models import (
    JobType, JobStatus, JobCreateResponse, ScreeningConfig, ScreeningResult
)
from surfscreen.api.dependencies import verify_api_key, get_job_manager_dep
from surfscreen.api.services.job_manager import JobManager


router = APIRouter(prefix="/screening", tags=["Screening"])


async def run_screening_task(job_id: str, job_manager: JobManager):
    """백그라운드 스크리닝 실행"""
    import traceback
    
    try:
        job_manager.update_job_status(job_id, status=JobStatus.RUNNING, progress=0)
        
        job_dir = job_manager.get_job_dir(job_id)
        input_dir = job_dir / "input"
        output_dir = job_dir / "output"
        
        # 요청 데이터 로드
        with open(job_dir / "request.json") as f:
            request = json.load(f)
        
        config = request.get("config", {})
        
        # 필요한 모듈 import (지연 로드)
        from surfscreen import SurfaceBuilder, MoleculeBuilder, AdsorptionSystem, CalculatorFactory
        
        # 표면 로드
        surface_files = list(input_dir.glob("surface_*"))
        if not surface_files:
            raise ValueError("No surface file found")
        
        surface_path = surface_files[0]
        surf = SurfaceBuilder.from_file(
            str(surface_path),
            fixed_layers=config.get("fix_layers", 2)
        )
        
        job_manager.update_job_status(job_id, progress=10)
        
        # Calculator 생성
        calc = CalculatorFactory.create(
            config.get("engine", "mace"),
            model=config.get("model", "medium"),
            device=config.get("device", "cuda")
        )
        
        job_manager.update_job_status(job_id, progress=15)
        
        # 분자 로드 및 스크리닝
        molecule_files = list(input_dir.glob("molecule_*"))
        all_results = []
        
        total_molecules = len(molecule_files)
        
        for i, mol_path in enumerate(molecule_files):
            mol = MoleculeBuilder.from_file(str(mol_path))
            
            system = AdsorptionSystem(surf, mol)
            
            rotations = config.get("rotations", [0, 45, 90, 135])
            configs = system.generate_configurations(
                rotations=rotations,
                max_configs=config.get("max_configs", 50)
            )
            
            mol_output = output_dir / mol.name
            mol_output.mkdir(parents=True, exist_ok=True)
            
            results = system.optimize_all(
                calc,
                output_dir=str(mol_output),
                fmax=config.get("fmax", 0.05),
                steps=config.get("steps", 500)
            )
            
            all_results.extend(results)
            
            # 진행률 업데이트
            progress = 15 + (i + 1) / total_molecules * 80
            job_manager.update_job_status(job_id, progress=progress)
        
        # 결과 정렬
        all_results.sort(key=lambda x: x.adsorption_energy)
        
        # 결과 저장
        results_data = {
            "total_configs": len(all_results),
            "converged_configs": sum(1 for r in all_results if r.converged),
            "best_e_ads": all_results[0].adsorption_energy if all_results else 0,
            "avg_e_ads": sum(r.adsorption_energy for r in all_results) / len(all_results) if all_results else 0,
            "results": [
                {
                    "name": r.config_name,
                    "e_ads": r.adsorption_energy,
                    "height": r.height,
                    "site_type": r.site_type,
                    "converged": r.converged
                }
                for r in all_results
            ]
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
    summary="Create Screening Job",
    description="새 스크리닝 Job 생성 및 백그라운드 실행"
)
async def create_screening_job(
    background_tasks: BackgroundTasks,
    surface: UploadFile = File(..., description="Surface structure file (xyz, poscar, etc.)"),
    molecules: List[UploadFile] = File(..., description="Molecule structure file(s)"),
    config: str = Form(default="{}", description="Screening config JSON"),
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
) -> JobCreateResponse:
    """
    스크리닝 Job 생성
    
    - surface: 표면 구조 파일
    - molecules: 분자 구조 파일들
    - config: 스크리닝 설정 (JSON 문자열)
    
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
        JobType.SCREENING,
        request_data={"config": config_dict}
    )
    
    job_dir = job_manager.get_job_dir(job_id)
    input_dir = job_dir / "input"
    
    # 파일 저장
    surface_ext = Path(surface.filename).suffix or ".xyz"
    surface_path = input_dir / f"surface_001{surface_ext}"
    with open(surface_path, "wb") as f:
        f.write(await surface.read())
    
    for i, mol in enumerate(molecules, 1):
        mol_ext = Path(mol.filename).suffix or ".xyz"
        mol_path = input_dir / f"molecule_{i:03d}{mol_ext}"
        with open(mol_path, "wb") as f:
            f.write(await mol.read())
    
    # 백그라운드 실행
    background_tasks.add_task(run_screening_task, job_id, job_manager)
    
    return JobCreateResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Screening job created. Use GET /jobs/{job_id} to check status."
    )


@router.get(
    "/{job_id}/result",
    response_model=ScreeningResult,
    summary="Get Screening Result",
    description="스크리닝 결과 조회"
)
async def get_screening_result(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
) -> ScreeningResult:
    """스크리닝 결과 조회"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_info.job_type != JobType.SCREENING:
        raise HTTPException(status_code=400, detail="Not a screening job")
    
    if job_info.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job not completed: {job_info.status.value}")
    
    result_path = job_manager.get_job_dir(job_id) / "output" / "results.json"
    
    with open(result_path) as f:
        data = json.load(f)
    
    from datetime import datetime
    
    return ScreeningResult(
        job_id=job_id,
        total_configs=data["total_configs"],
        converged_configs=data["converged_configs"],
        best_e_ads=data["best_e_ads"],
        avg_e_ads=data["avg_e_ads"],
        top_results=data["results"][:20],
        completed_at=job_info.completed_at or datetime.utcnow()
    )


@router.get(
    "/{job_id}/report",
    summary="Generate Screening Report",
    description="스크리닝 결과 HTML 리포트 생성"
)
async def generate_screening_report(
    job_id: str,
    theme: str = "dark",
    job_manager: JobManager = Depends(get_job_manager_dep),
    _: str = Depends(verify_api_key)
):
    """스크리닝 리포트 생성"""
    job_info = job_manager.get_job_status(job_id)
    
    if not job_info or job_info.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    output_dir = job_manager.get_job_dir(job_id) / "output"
    report_path = output_dir / "report.html"
    
    # 리포트 생성
    if not report_path.exists():
        from surfscreen.report import ScreeningReportGenerator
        gen = ScreeningReportGenerator(str(output_dir), theme=theme)
        gen.generate(str(report_path))
    
    return FileResponse(
        path=str(report_path),
        media_type="text/html",
        filename=f"{job_id}_screening_report.html"
    )
