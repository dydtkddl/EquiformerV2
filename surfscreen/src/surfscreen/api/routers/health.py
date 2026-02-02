"""
SurfScreen API Health Router

헬스체크 엔드포인트
"""

from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends

from surfscreen.api.models import HealthStatus, ReadinessStatus
from surfscreen.api.config import get_settings, Settings


router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Health Check",
    description="API 서버 상태 및 사용 가능한 계산 엔진 확인"
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthStatus:
    """
    기본 헬스체크
    
    Returns:
        - status: "ok"
        - version: API 버전
        - engines: 사용 가능한 계산 엔진 목록
    """
    # 사용 가능한 엔진 확인
    engines = []
    
    try:
        from surfscreen.calculator import CalculatorFactory
        engines = CalculatorFactory.available()
    except ImportError:
        pass
    
    # 기본 엔진 추가
    if not engines:
        engines = ["emt"]  # EMT는 항상 사용 가능
    
    return HealthStatus(
        status="ok",
        version=settings.API_VERSION,
        timestamp=datetime.utcnow(),
        engines=engines
    )


@router.get(
    "/health/ready",
    response_model=ReadinessStatus,
    summary="Readiness Check",
    description="서비스 준비 상태 확인 (의존성 체크)"
)
async def readiness_check() -> ReadinessStatus:
    """
    준비 상태 체크 (Kubernetes readiness probe용)
    
    Returns:
        - ready: 전체 준비 상태
        - checks: 개별 체크 결과
    """
    checks: Dict[str, bool] = {}
    
    # ASE 체크
    try:
        import ase
        checks["ase"] = True
    except ImportError:
        checks["ase"] = False
    
    # NumPy 체크
    try:
        import numpy
        checks["numpy"] = True
    except ImportError:
        checks["numpy"] = False
    
    # Calculator 체크
    try:
        from surfscreen.calculator import CalculatorFactory
        checks["calculator"] = len(CalculatorFactory.available()) > 0
    except Exception:
        checks["calculator"] = False
    
    # Jobs 디렉토리 체크
    try:
        from surfscreen.api.config import get_settings
        settings = get_settings()
        checks["jobs_dir"] = settings.JOBS_DIR.exists()
    except Exception:
        checks["jobs_dir"] = False
    
    ready = all(checks.values())
    
    return ReadinessStatus(ready=ready, checks=checks)


@router.get(
    "/health/live",
    summary="Liveness Check",
    description="서비스 생존 상태 확인"
)
async def liveness_check() -> Dict[str, str]:
    """
    생존 상태 체크 (Kubernetes liveness probe용)
    
    Returns:
        {"status": "alive"}
    """
    return {"status": "alive"}
