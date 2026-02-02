"""
SurfScreen REST API Main Application

FastAPI 애플리케이션 구성
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from surfscreen.api.config import get_settings
from surfscreen.api.routers import (
    health_router,
    jobs_router,
    screening_router,
    md_router,
    # Phase 11: Advanced Features
    cache_router,
    batch_router,
    schedule_router,
    users_router,
    webhooks_router,
)


# 설정 로드
settings = get_settings()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("surfscreen.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
    logger.info(f"Starting SurfScreen API v{settings.API_VERSION}")
    logger.info(f"Jobs directory: {settings.JOBS_DIR}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Jobs 디렉토리 초기화
    settings.JOBS_DIR.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down SurfScreen API")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
## SurfScreen REST API

엔터프라이즈급 표면 흡착 스크리닝 및 분자 동역학 시뮬레이션 API.

### 주요 기능

- **🎯 Screening**: 다중 분자 흡착 위치 스크리닝
- **🔬 MD Simulation**: NVT/NPT/NVE 앙상블 MD 시뮬레이션
- **📊 Jobs**: 비동기 작업 관리 및 모니터링
- **📥 Downloads**: 결과 파일 및 리포트 다운로드

### 인증

모든 API 요청에 `X-API-Key` 헤더가 필요합니다.

```
X-API-Key: your-api-key
```
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# 전역 예외 핸들러
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 유효성 검증 에러 핸들러"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "code": "VALIDATION_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# 라우터 등록
app.include_router(health_router)
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(screening_router, prefix="/api/v1")
app.include_router(md_router, prefix="/api/v1")

# Phase 11: Advanced Features
app.include_router(cache_router, prefix="/api/v1")
app.include_router(batch_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")


# Root 엔드포인트
@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """API 루트 - 기본 정보"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": "/api/v1"
    }


def create_app() -> FastAPI:
    """앱 팩토리 (테스트용)"""
    return app


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "surfscreen.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS
    )
