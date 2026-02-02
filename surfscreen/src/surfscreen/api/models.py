"""
SurfScreen API Pydantic Models

요청/응답 스키마 정의
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ============ Enums ============

class JobStatus(str, Enum):
    """Job 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job 유형"""
    SCREENING = "screening"
    MD = "md"
    ANALYSIS = "analysis"


class Ensemble(str, Enum):
    """MD 앙상블"""
    NVT = "nvt"
    NPT = "npt"
    NVE = "nve"


class Thermostat(str, Enum):
    """열욕"""
    LANGEVIN = "langevin"
    BERENDSEN = "berendsen"
    NOSE_HOOVER = "nose_hoover"


# ============ Base Models ============

class APIResponse(BaseModel):
    """공통 API 응답"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
    code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ Screening Models ============

class ScreeningConfig(BaseModel):
    """스크리닝 설정"""
    model_config = ConfigDict(from_attributes=True)
    
    engine: str = Field(default="mace", description="계산 엔진 (mace, xtb, emt)")
    model: str = Field(default="medium", description="MACE 모델 크기")
    device: str = Field(default="cuda", description="디바이스 (cuda, cpu)")
    rotations: List[float] = Field(default=[0, 45, 90, 135], description="회전 각도")
    heights: List[float] = Field(default=[1.5, 2.0, 2.5], description="초기 높이 (Å)")
    max_configs: int = Field(default=50, description="최대 구성 수")
    fix_layers: int = Field(default=2, description="고정할 표면 층 수")
    fmax: float = Field(default=0.05, description="최대 힘 수렴 조건 (eV/Å)")
    steps: int = Field(default=500, description="최대 최적화 스텝")


class ScreeningJobRequest(BaseModel):
    """스크리닝 Job 요청"""
    model_config = ConfigDict(from_attributes=True)
    
    surface_filename: Optional[str] = None
    molecule_filenames: Optional[List[str]] = None
    config: ScreeningConfig = Field(default_factory=ScreeningConfig)


class ScreeningResultItem(BaseModel):
    """개별 스크리닝 결과"""
    name: str
    e_ads: float = Field(description="흡착 에너지 (eV)")
    height: float = Field(description="높이 (Å)")
    site_type: str
    converged: bool = True


class ScreeningResult(BaseModel):
    """스크리닝 전체 결과"""
    model_config = ConfigDict(from_attributes=True)
    
    job_id: str
    total_configs: int
    converged_configs: int
    best_e_ads: float
    avg_e_ads: float
    top_results: List[ScreeningResultItem]
    completed_at: datetime


# ============ MD Models ============

class MDConfig(BaseModel):
    """MD 설정"""
    model_config = ConfigDict(from_attributes=True)
    
    ensemble: Ensemble = Field(default=Ensemble.NVT)
    temperature: float = Field(default=300.0, description="온도 (K)")
    pressure: float = Field(default=1.0, description="압력 (bar, NPT only)")
    timestep: float = Field(default=1.0, description="타임스텝 (fs)")
    steps: int = Field(default=10000, description="시뮬레이션 스텝 수")
    thermostat: Thermostat = Field(default=Thermostat.LANGEVIN)
    engine: str = Field(default="mace")
    model: str = Field(default="medium")
    device: str = Field(default="cuda")
    log_interval: int = Field(default=100, description="로그 기록 간격")
    traj_interval: int = Field(default=100, description="궤적 저장 간격")


class MDJobRequest(BaseModel):
    """MD Job 요청"""
    model_config = ConfigDict(from_attributes=True)
    
    structure_filename: Optional[str] = None
    config: MDConfig = Field(default_factory=MDConfig)


class MDResult(BaseModel):
    """MD 결과"""
    model_config = ConfigDict(from_attributes=True)
    
    job_id: str
    total_steps: int
    total_time_fs: float
    avg_temperature: float
    final_energy: float
    trajectory_frames: int
    completed_at: datetime


# ============ Job Models ============

class JobInfo(BaseModel):
    """Job 정보"""
    model_config = ConfigDict(from_attributes=True)
    
    job_id: str
    job_type: JobType
    status: JobStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="진행률 (%)")
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None


class JobListResponse(BaseModel):
    """Job 목록 응답"""
    total: int
    jobs: List[JobInfo]


class JobCreateResponse(BaseModel):
    """Job 생성 응답"""
    job_id: str
    status: JobStatus = JobStatus.PENDING
    message: str = "Job created successfully"


# ============ Health Models ============

class HealthStatus(BaseModel):
    """헬스체크 응답"""
    status: str = "ok"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    engines: List[str] = Field(default_factory=list)


class ReadinessStatus(BaseModel):
    """준비 상태 응답"""
    ready: bool
    checks: Dict[str, bool]
