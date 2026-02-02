"""
SurfScreen REST API Package

FastAPI 기반 엔터프라이즈급 REST API
- 비동기 Job 처리
- 스크리닝 및 MD 시뮬레이션 제어
- OpenAPI 문서 자동 생성
"""

from surfscreen.api.main import app, create_app

__all__ = ["app", "create_app"]
