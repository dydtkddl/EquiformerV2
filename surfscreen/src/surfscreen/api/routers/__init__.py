"""
SurfScreen API Routers Package
"""

from surfscreen.api.routers.health import router as health_router
from surfscreen.api.routers.jobs import router as jobs_router
from surfscreen.api.routers.screening import router as screening_router
from surfscreen.api.routers.md import router as md_router

# Phase 11: Advanced Features
from surfscreen.api.routers.cache import router as cache_router
from surfscreen.api.routers.batch import router as batch_router
from surfscreen.api.routers.schedule import router as schedule_router
from surfscreen.api.routers.users import router as users_router
from surfscreen.api.routers.webhooks import router as webhooks_router

__all__ = [
    "health_router",
    "jobs_router",
    "screening_router",
    "md_router",
    # Phase 11
    "cache_router",
    "batch_router",
    "schedule_router",
    "users_router",
    "webhooks_router",
]
