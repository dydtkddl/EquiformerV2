"""
SurfScreen API Configuration

환경변수 기반 설정 관리
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API 설정"""
    
    model_config = SettingsConfigDict(
        env_prefix="SURFSCREEN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # API 설정
    API_KEY: str = Field(default="dev-key-change-me", description="API 인증 키")
    API_TITLE: str = Field(default="SurfScreen API", description="API 제목")
    API_VERSION: str = Field(default="0.4.0", description="API 버전")
    DEBUG: bool = Field(default=False, description="디버그 모드")
    
    # 서버 설정
    HOST: str = Field(default="0.0.0.0", description="서버 호스트")
    PORT: int = Field(default=8000, description="서버 포트")
    WORKERS: int = Field(default=1, description="워커 수")
    
    # Job 관리
    JOBS_DIR: Path = Field(default=Path("./jobs"), description="Job 저장 디렉토리")
    MAX_CONCURRENT_JOBS: int = Field(default=4, description="최대 동시 작업 수")
    JOB_TIMEOUT_SECONDS: int = Field(default=3600, description="작업 타임아웃 (초)")
    
    # 계산 설정
    DEFAULT_ENGINE: str = Field(default="mace", description="기본 계산 엔진")
    DEFAULT_DEVICE: str = Field(default="cuda", description="기본 디바이스")
    NCPUS: Optional[int] = Field(default=None, description="CPU 스레드 수")
    
    # CORS 설정
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="허용된 CORS 출처"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])
    
    # 로깅
    LOG_LEVEL: str = Field(default="INFO", description="로그 레벨")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # jobs 디렉토리 생성
        self.JOBS_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """캐싱된 설정 인스턴스 반환"""
    return Settings()
