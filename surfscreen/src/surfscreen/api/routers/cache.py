"""
Cache API Router

REST API endpoints for cache management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from ...cache import get_cache_manager, CacheManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


# ============================================
# Pydantic Models
# ============================================

class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    
    hits: int = Field(..., description="Number of cache hits")
    misses: int = Field(..., description="Number of cache misses")
    hit_rate: float = Field(..., description="Hit rate percentage")
    total_keys: int = Field(..., description="Total cached keys")
    memory_used: str = Field(..., description="Memory usage")
    uptime_seconds: int = Field(..., description="Redis uptime")
    connected: bool = Field(..., description="Connection status")


class CacheEntryResponse(BaseModel):
    """Cache entry response."""
    
    key: str
    created_at: str
    expires_at: Optional[str]
    size_bytes: int
    ttl_seconds: int
    hit_count: int


class CacheListResponse(BaseModel):
    """Cache list response."""
    
    entries: List[CacheEntryResponse]
    total: int


class CacheClearResponse(BaseModel):
    """Cache clear response."""
    
    deleted: int
    pattern: str


class CacheSetRequest(BaseModel):
    """Cache set request."""
    
    key: str = Field(..., min_length=1, max_length=256)
    value: str = Field(..., description="JSON-serialized value")
    ttl: Optional[int] = Field(None, ge=1, le=604800, description="TTL in seconds (max 7 days)")


class CacheSetResponse(BaseModel):
    """Cache set response."""
    
    success: bool
    key: str
    ttl: int


# ============================================
# Dependencies
# ============================================

def get_cache() -> CacheManager:
    """Dependency to get cache manager."""
    return get_cache_manager()


# ============================================
# Endpoints
# ============================================

@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(cache: CacheManager = Depends(get_cache)):
    """
    Get cache statistics.
    
    Returns cache hit/miss rates, memory usage, and connection status.
    """
    stats = cache.get_stats()
    
    return CacheStatsResponse(
        hits=stats.hits,
        misses=stats.misses,
        hit_rate=round(stats.hit_rate, 2),
        total_keys=stats.total_keys,
        memory_used=stats.memory_used,
        uptime_seconds=stats.uptime_seconds,
        connected=stats.connected,
    )


@router.get("/keys", response_model=CacheListResponse)
async def list_cache_keys(
    pattern: str = Query("*", description="Key pattern to match"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    cache: CacheManager = Depends(get_cache),
):
    """
    List cache entries matching pattern.
    
    Use wildcards in pattern (e.g., "screening:*", "*:mace:*").
    """
    entries = cache.list_keys(pattern=pattern, limit=limit)
    
    return CacheListResponse(
        entries=[
            CacheEntryResponse(
                key=e.key,
                created_at=e.created_at,
                expires_at=e.expires_at,
                size_bytes=e.size_bytes,
                ttl_seconds=e.ttl_seconds,
                hit_count=e.hit_count,
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.get("/{key}")
async def get_cache_entry(
    key: str,
    cache: CacheManager = Depends(get_cache),
):
    """
    Get specific cache entry.
    
    Returns the cached value if exists.
    """
    if not cache.is_connected:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    value = cache.get(key)
    
    if value is None:
        raise HTTPException(status_code=404, detail="Cache key not found")
    
    return {
        "key": key,
        "value": value,
        "exists": True,
    }


@router.delete("", response_model=CacheClearResponse)
async def clear_cache(
    pattern: str = Query("*", description="Key pattern to clear"),
    confirm: bool = Query(False, description="Confirm deletion"),
    cache: CacheManager = Depends(get_cache),
):
    """
    Clear cache entries matching pattern.
    
    Requires confirm=true to actually delete.
    """
    if not confirm:
        # Dry run - just count matching keys
        entries = cache.list_keys(pattern=pattern, limit=10000)
        return CacheClearResponse(deleted=len(entries), pattern=pattern)
    
    deleted = cache.clear(pattern)
    
    logger.info(f"Cache cleared: {deleted} keys matching '{pattern}'")
    
    return CacheClearResponse(deleted=deleted, pattern=pattern)


@router.delete("/{key}")
async def delete_cache_entry(
    key: str,
    cache: CacheManager = Depends(get_cache),
):
    """
    Delete specific cache entry.
    """
    if not cache.exists(key):
        raise HTTPException(status_code=404, detail="Cache key not found")
    
    success = cache.delete(key)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete cache entry")
    
    return {"deleted": True, "key": key}


@router.post("/warmup")
async def warmup_cache(
    cache: CacheManager = Depends(get_cache),
):
    """
    Warm up cache by preloading common data.
    
    This is a placeholder for implementing cache warming strategies.
    """
    if not cache.is_connected:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    # TODO: Implement cache warming logic
    # This could include:
    # - Preloading frequently accessed structures
    # - Caching reference data
    # - Pre-computing common calculations
    
    return {
        "status": "completed",
        "message": "Cache warmup completed (no-op in current version)",
    }


@router.get("/health")
async def cache_health(cache: CacheManager = Depends(get_cache)):
    """
    Check cache health status.
    """
    connected = cache.is_connected
    stats = cache.get_stats() if connected else None
    
    return {
        "status": "healthy" if connected else "degraded",
        "connected": connected,
        "message": "Cache operational" if connected else "Cache unavailable - operating in no-cache mode",
        "stats": {
            "hit_rate": f"{stats.hit_rate:.1f}%" if stats else "N/A",
            "memory": stats.memory_used if stats else "N/A",
        } if stats else None,
    }
