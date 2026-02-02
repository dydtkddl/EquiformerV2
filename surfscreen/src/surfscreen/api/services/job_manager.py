"""
SurfScreen API Job Manager

비동기 Job 관리 서비스
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from threading import Lock

from surfscreen.api.config import get_settings
from surfscreen.api.models import JobStatus, JobType, JobInfo


class JobManager:
    """Job 관리 싱글톤 서비스"""
    
    _instance: Optional["JobManager"] = None
    _lock = Lock()
    
    def __new__(cls):
        """싱글톤 패턴"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.settings = get_settings()
        self.jobs_dir = self.settings.JOBS_DIR
        self._active_jobs: Dict[str, asyncio.Task] = {}
        self._initialized = True
    
    def create_job(self, job_type: JobType, request_data: Optional[Dict] = None) -> str:
        """
        새 Job 생성
        
        Args:
            job_type: Job 유형 (screening, md, analysis)
            request_data: 요청 데이터 (저장용)
            
        Returns:
            생성된 job_id
        """
        job_id = str(uuid.uuid4())[:8]
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Input 디렉토리 생성
        (job_dir / "input").mkdir(exist_ok=True)
        (job_dir / "output").mkdir(exist_ok=True)
        
        # 상태 파일 생성
        status = JobInfo(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            progress=0.0,
            created_at=datetime.utcnow()
        )
        
        self._save_status(job_id, status)
        
        # 요청 데이터 저장
        if request_data:
            with open(job_dir / "request.json", "w") as f:
                json.dump(request_data, f, indent=2, default=str)
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """Job 상태 조회"""
        status_path = self.jobs_dir / job_id / "status.json"
        
        if not status_path.exists():
            return None
        
        with open(status_path) as f:
            data = json.load(f)
        
        # datetime 파싱
        for field in ["created_at", "started_at", "completed_at"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        return JobInfo(**data)
    
    def update_job_status(
        self, 
        job_id: str, 
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        error_message: Optional[str] = None,
        result_path: Optional[str] = None
    ) -> bool:
        """
        Job 상태 업데이트
        
        Args:
            job_id: Job ID
            status: 새 상태
            progress: 진행률 (0-100)
            error_message: 에러 메시지
            result_path: 결과 파일 경로
            
        Returns:
            성공 여부
        """
        current = self.get_job_status(job_id)
        if not current:
            return False
        
        if status:
            current.status = status
            if status == JobStatus.RUNNING and not current.started_at:
                current.started_at = datetime.utcnow()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                current.completed_at = datetime.utcnow()
        
        if progress is not None:
            current.progress = min(max(progress, 0.0), 100.0)
        
        if error_message:
            current.error_message = error_message
        
        if result_path:
            current.result_path = result_path
        
        self._save_status(job_id, current)
        return True
    
    def cancel_job(self, job_id: str) -> bool:
        """Job 취소"""
        # 실행 중인 태스크 취소
        if job_id in self._active_jobs:
            task = self._active_jobs[job_id]
            if not task.done():
                task.cancel()
            del self._active_jobs[job_id]
        
        return self.update_job_status(job_id, status=JobStatus.CANCELLED)
    
    def list_jobs(
        self, 
        status_filter: Optional[JobStatus] = None,
        job_type_filter: Optional[JobType] = None,
        limit: int = 100
    ) -> List[JobInfo]:
        """
        Job 목록 조회
        
        Args:
            status_filter: 상태 필터
            job_type_filter: 유형 필터
            limit: 최대 반환 수
            
        Returns:
            Job 정보 리스트
        """
        jobs = []
        
        if not self.jobs_dir.exists():
            return jobs
        
        for job_dir in sorted(self.jobs_dir.iterdir(), reverse=True):
            if not job_dir.is_dir():
                continue
            
            status_path = job_dir / "status.json"
            if not status_path.exists():
                continue
            
            try:
                job_info = self.get_job_status(job_dir.name)
                if not job_info:
                    continue
                
                # 필터 적용
                if status_filter and job_info.status != status_filter:
                    continue
                if job_type_filter and job_info.job_type != job_type_filter:
                    continue
                
                jobs.append(job_info)
                
                if len(jobs) >= limit:
                    break
                    
            except Exception:
                continue
        
        return jobs
    
    def get_job_dir(self, job_id: str) -> Path:
        """Job 디렉토리 경로 반환"""
        return self.jobs_dir / job_id
    
    def register_task(self, job_id: str, task: asyncio.Task):
        """비동기 태스크 등록"""
        self._active_jobs[job_id] = task
    
    def unregister_task(self, job_id: str):
        """비동기 태스크 등록 해제"""
        if job_id in self._active_jobs:
            del self._active_jobs[job_id]
    
    def _save_status(self, job_id: str, status: JobInfo):
        """상태 파일 저장"""
        status_path = self.jobs_dir / job_id / "status.json"
        
        data = status.model_dump()
        # datetime 직렬화
        for field in ["created_at", "started_at", "completed_at"]:
            if data.get(field):
                data[field] = data[field].isoformat()
        
        # 원자적 쓰기
        temp_path = status_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
        temp_path.replace(status_path)
    
    def cleanup_old_jobs(self, max_age_days: int = 7):
        """오래된 Job 정리"""
        import shutil
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        
        for job_dir in self.jobs_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            job_info = self.get_job_status(job_dir.name)
            if job_info and job_info.completed_at and job_info.completed_at < cutoff:
                try:
                    shutil.rmtree(job_dir)
                except Exception:
                    pass


# 싱글톤 인스턴스 getter
def get_job_manager() -> JobManager:
    return JobManager()
