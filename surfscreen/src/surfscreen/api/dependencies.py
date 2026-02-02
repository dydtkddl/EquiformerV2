"""
SurfScreen API Dependencies

의존성 주입 및 인증
"""

from typing import Optional
from fastapi import Header, HTTPException, status, Depends

from surfscreen.api.config import get_settings, Settings
from surfscreen.api.services.job_manager import get_job_manager, JobManager


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings)
) -> str:
    """
    API Key 검증
    
    Headers:
        X-API-Key: API 인증 키
        
    Returns:
        검증된 API 키
        
    Raises:
        HTTPException(401): 인증 실패
    """
    # 디버그 모드에서는 인증 우회
    if settings.DEBUG:
        return "debug-mode"
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include 'X-API-Key' header.",
            headers={"WWW-Authenticate": "API-Key"}
        )
    
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API-Key"}
        )
    
    return x_api_key


async def get_job_manager_dep() -> JobManager:
    """JobManager 의존성"""
    return get_job_manager()


# Optional API Key (일부 엔드포인트용)
async def optional_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings)
) -> Optional[str]:
    """선택적 API Key 검증 (헬스체크 등)"""
    if not x_api_key:
        return None
    
    if x_api_key == settings.API_KEY or settings.DEBUG:
        return x_api_key
    
    return None
