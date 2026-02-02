"""
SurfScreen Cache Module

Redis-based caching for calculation results.
"""

from .cache_manager import CacheManager, get_cache_manager
from .cache_decorators import cache_result, invalidate_cache

__all__ = [
    "CacheManager",
    "get_cache_manager",
    "cache_result",
    "invalidate_cache",
]
