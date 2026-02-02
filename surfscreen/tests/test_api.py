"""
Test SurfScreen REST API

API 엔드포인트 테스트
"""

import pytest
import json
from pathlib import Path


class TestAPIImports:
    """API 모듈 import 테스트"""
    
    def test_import_config(self):
        """config 모듈 import"""
        from surfscreen.api.config import Settings, get_settings
        assert Settings is not None
        assert get_settings is not None
    
    def test_import_models(self):
        """models 모듈 import"""
        from surfscreen.api.models import (
            JobStatus, JobType, JobInfo,
            ScreeningConfig, MDConfig
        )
        assert JobStatus.PENDING.value == "pending"
        assert JobType.SCREENING.value == "screening"
    
    def test_import_job_manager(self):
        """job_manager import"""
        from surfscreen.api.services.job_manager import JobManager, get_job_manager
        assert JobManager is not None


class TestModels:
    """Pydantic 모델 테스트"""
    
    def test_job_status_enum(self):
        """JobStatus enum"""
        from surfscreen.api.models import JobStatus
        
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"
    
    def test_screening_config_defaults(self):
        """ScreeningConfig 기본값"""
        from surfscreen.api.models import ScreeningConfig
        
        config = ScreeningConfig()
        
        assert config.engine == "mace"
        assert config.device == "cuda"
        assert config.max_configs == 50
        assert 0 in config.rotations
    
    def test_md_config_defaults(self):
        """MDConfig 기본값"""
        from surfscreen.api.models import MDConfig, Ensemble, Thermostat
        
        config = MDConfig()
        
        assert config.ensemble == Ensemble.NVT
        assert config.temperature == 300.0
        assert config.steps == 10000
        assert config.thermostat == Thermostat.LANGEVIN
    
    def test_job_info_serialization(self):
        """JobInfo 직렬화"""
        from datetime import datetime
        from surfscreen.api.models import JobInfo, JobStatus, JobType
        
        info = JobInfo(
            job_id="test123",
            job_type=JobType.SCREENING,
            status=JobStatus.RUNNING,
            progress=50.0,
            created_at=datetime.utcnow()
        )
        
        data = info.model_dump()
        
        assert data["job_id"] == "test123"
        assert data["status"] == "running"
        assert data["progress"] == 50.0


class TestJobManager:
    """JobManager 테스트"""
    
    def test_create_job(self, tmp_path, monkeypatch):
        """Job 생성"""
        from surfscreen.api.services.job_manager import JobManager, get_job_manager
        from surfscreen.api.models import JobType, JobStatus
        from surfscreen.api.config import Settings
        
        # 설정 오버라이드
        settings = Settings(JOBS_DIR=tmp_path / "jobs")
        monkeypatch.setattr("surfscreen.api.services.job_manager.get_settings", lambda: settings)
        
        # 싱글톤 리셋
        JobManager._instance = None
        
        manager = get_job_manager()
        
        job_id = manager.create_job(JobType.SCREENING, {"test": "data"})
        
        assert job_id is not None
        assert len(job_id) == 8
        
        # 디렉토리 확인
        job_dir = settings.JOBS_DIR / job_id
        assert job_dir.exists()
        assert (job_dir / "input").exists()
        assert (job_dir / "output").exists()
        assert (job_dir / "status.json").exists()
    
    def test_get_job_status(self, tmp_path, monkeypatch):
        """Job 상태 조회"""
        from surfscreen.api.services.job_manager import JobManager, get_job_manager
        from surfscreen.api.models import JobType, JobStatus
        from surfscreen.api.config import Settings
        
        settings = Settings(JOBS_DIR=tmp_path / "jobs")
        monkeypatch.setattr("surfscreen.api.services.job_manager.get_settings", lambda: settings)
        
        JobManager._instance = None
        manager = get_job_manager()
        
        job_id = manager.create_job(JobType.MD)
        status = manager.get_job_status(job_id)
        
        assert status is not None
        assert status.job_id == job_id
        assert status.status == JobStatus.PENDING
        assert status.job_type == JobType.MD
    
    def test_update_job_status(self, tmp_path, monkeypatch):
        """Job 상태 업데이트"""
        from surfscreen.api.services.job_manager import JobManager, get_job_manager
        from surfscreen.api.models import JobType, JobStatus
        from surfscreen.api.config import Settings
        
        settings = Settings(JOBS_DIR=tmp_path / "jobs")
        monkeypatch.setattr("surfscreen.api.services.job_manager.get_settings", lambda: settings)
        
        JobManager._instance = None
        manager = get_job_manager()
        
        job_id = manager.create_job(JobType.SCREENING)
        
        # 상태 업데이트
        manager.update_job_status(job_id, status=JobStatus.RUNNING, progress=25.0)
        
        status = manager.get_job_status(job_id)
        
        assert status.status == JobStatus.RUNNING
        assert status.progress == 25.0
        assert status.started_at is not None
    
    def test_cancel_job(self, tmp_path, monkeypatch):
        """Job 취소"""
        from surfscreen.api.services.job_manager import JobManager, get_job_manager
        from surfscreen.api.models import JobType, JobStatus
        from surfscreen.api.config import Settings
        
        settings = Settings(JOBS_DIR=tmp_path / "jobs")
        monkeypatch.setattr("surfscreen.api.services.job_manager.get_settings", lambda: settings)
        
        JobManager._instance = None
        manager = get_job_manager()
        
        job_id = manager.create_job(JobType.SCREENING)
        manager.cancel_job(job_id)
        
        status = manager.get_job_status(job_id)
        
        assert status.status == JobStatus.CANCELLED
    
    def test_list_jobs(self, tmp_path, monkeypatch):
        """Job 목록 조회"""
        from surfscreen.api.services.job_manager import JobManager, get_job_manager
        from surfscreen.api.models import JobType, JobStatus
        from surfscreen.api.config import Settings
        
        settings = Settings(JOBS_DIR=tmp_path / "jobs")
        monkeypatch.setattr("surfscreen.api.services.job_manager.get_settings", lambda: settings)
        
        JobManager._instance = None
        manager = get_job_manager()
        
        # 여러 Job 생성
        manager.create_job(JobType.SCREENING)
        manager.create_job(JobType.MD)
        manager.create_job(JobType.SCREENING)
        
        jobs = manager.list_jobs()
        
        assert len(jobs) == 3
        
        # 필터 테스트
        screening_jobs = manager.list_jobs(job_type_filter=JobType.SCREENING)
        assert len(screening_jobs) == 2


# FastAPI 테스트 (TestClient 필요)
try:
    from fastapi.testclient import TestClient
    
    class TestHealthEndpoints:
        """Health 엔드포인트 테스트"""
        
        @pytest.fixture
        def client(self, tmp_path, monkeypatch):
            """테스트 클라이언트"""
            from surfscreen.api.config import Settings
            
            settings = Settings(JOBS_DIR=tmp_path / "jobs", DEBUG=True)
            monkeypatch.setattr("surfscreen.api.config.get_settings", lambda: settings)
            
            from surfscreen.api.main import app
            return TestClient(app)
        
        def test_health_check(self, client):
            """GET /health"""
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data
        
        def test_liveness_check(self, client):
            """GET /health/live"""
            response = client.get("/health/live")
            
            assert response.status_code == 200
            assert response.json()["status"] == "alive"


    class TestRootEndpoint:
        """Root 엔드포인트 테스트"""
        
        @pytest.fixture
        def client(self, tmp_path, monkeypatch):
            from surfscreen.api.config import Settings
            
            settings = Settings(JOBS_DIR=tmp_path / "jobs", DEBUG=True)
            monkeypatch.setattr("surfscreen.api.config.get_settings", lambda: settings)
            
            from surfscreen.api.main import app
            return TestClient(app)
        
        def test_root(self, client):
            """GET /"""
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "version" in data
            assert data["api_prefix"] == "/api/v1"

except ImportError:
    # FastAPI 테스트 클래스 스킵
    pass
