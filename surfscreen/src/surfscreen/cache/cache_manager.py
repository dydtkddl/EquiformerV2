"""
Cache Manager

Redis-based caching system for calculation results with graceful degradation.
"""

import hashlib
import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration."""
    
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    default_ttl: int = 7 * 24 * 60 * 60  # 7 days in seconds
    max_memory: str = "1gb"
    key_prefix: str = "surfscreen:"
    enabled: bool = True
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            default_ttl=int(os.getenv("CACHE_TTL", str(7 * 24 * 60 * 60))),
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        )


@dataclass
class CacheStats:
    """Cache statistics."""
    
    hits: int = 0
    misses: int = 0
    total_keys: int = 0
    memory_used: str = "0B"
    uptime_seconds: int = 0
    connected: bool = False
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100


@dataclass
class CacheEntry:
    """Cache entry metadata."""
    
    key: str
    created_at: str
    expires_at: Optional[str]
    size_bytes: int
    ttl_seconds: int
    hit_count: int = 0


class CacheManager:
    """
    Redis-based cache manager with graceful degradation.
    
    If Redis is unavailable, operations become no-ops instead of failing.
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache manager.
        
        Args:
            config: Cache configuration. If None, loads from environment.
        """
        self.config = config or CacheConfig.from_env()
        self._redis: Optional[Any] = None
        self._connected = False
        self._local_stats = CacheStats()
        
        if self.config.enabled:
            self._connect()
    
    def _connect(self) -> bool:
        """Attempt to connect to Redis."""
        try:
            import redis
            
            self._redis = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
            return True
            
        except ImportError:
            logger.warning("Redis package not installed. Caching disabled.")
            self._connected = False
            return False
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self._connected = False
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self._connected or not self._redis:
            return False
        
        try:
            self._redis.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.config.key_prefix}{key}"
    
    @staticmethod
    def generate_cache_key(
        structure_hash: str,
        engine: str,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Generate cache key from calculation parameters.
        
        Args:
            structure_hash: Hash of the atomic structure
            engine: Calculator engine name
            parameters: Calculation parameters
            
        Returns:
            Cache key string
        """
        # Sort parameters for consistent hashing
        params_str = json.dumps(parameters, sort_keys=True)
        combined = f"{structure_hash}:{engine}:{params_str}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    @staticmethod
    def hash_structure(positions: Any, symbols: List[str], cell: Any = None) -> str:
        """
        Generate hash from atomic structure.
        
        Args:
            positions: Atomic positions array
            symbols: List of element symbols
            cell: Optional unit cell
            
        Returns:
            Hash string
        """
        import numpy as np
        
        # Round positions to avoid floating point issues
        pos_rounded = np.round(positions, decimals=6).tobytes()
        symbols_str = ",".join(symbols)
        
        if cell is not None:
            cell_rounded = np.round(cell, decimals=6).tobytes()
            data = pos_rounded + symbols_str.encode() + cell_rounded
        else:
            data = pos_rounded + symbols_str.encode()
        
        return hashlib.sha256(data).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/error
        """
        if not self.is_connected:
            self._local_stats.misses += 1
            return None
        
        try:
            full_key = self._make_key(key)
            data = self._redis.get(full_key)
            
            if data is None:
                self._local_stats.misses += 1
                logger.debug(f"Cache miss: {key}")
                return None
            
            self._local_stats.hits += 1
            logger.debug(f"Cache hit: {key}")
            
            # Update hit count
            hit_key = f"{full_key}:hits"
            self._redis.incr(hit_key)
            
            return pickle.loads(data)
            
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self._local_stats.misses += 1
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds. Defaults to config default.
            metadata: Optional metadata to store with value
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.config.default_ttl
            
            # Serialize value
            data = pickle.dumps(value)
            
            # Store value with TTL
            self._redis.setex(full_key, ttl, data)
            
            # Store metadata
            if metadata:
                meta_key = f"{full_key}:meta"
                meta_data = {
                    "created_at": datetime.utcnow().isoformat(),
                    "ttl": ttl,
                    "size_bytes": len(data),
                    **metadata,
                }
                self._redis.setex(meta_key, ttl, json.dumps(meta_data))
            
            # Initialize hit counter
            hit_key = f"{full_key}:hits"
            self._redis.setex(hit_key, ttl, "0")
            
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key)
            
            # Delete value, metadata, and hit counter
            self._redis.delete(full_key)
            self._redis.delete(f"{full_key}:meta")
            self._redis.delete(f"{full_key}:hits")
            
            logger.debug(f"Cache delete: {key}")
            return True
            
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.is_connected:
            return False
        
        try:
            full_key = self._make_key(key)
            return bool(self._redis.exists(full_key))
        except Exception:
            return False
    
    def clear(self, pattern: str = "*") -> int:
        """
        Clear cache entries matching pattern.
        
        Args:
            pattern: Key pattern to match (e.g., "screening:*")
            
        Returns:
            Number of deleted keys
        """
        if not self.is_connected:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = list(self._redis.scan_iter(match=full_pattern))
            
            if keys:
                deleted = self._redis.delete(*keys)
                logger.info(f"Cache cleared: {deleted} keys")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return 0
    
    def get_stats(self) -> CacheStats:
        """
        Get cache statistics.
        
        Returns:
            CacheStats object
        """
        if not self.is_connected:
            return CacheStats(
                hits=self._local_stats.hits,
                misses=self._local_stats.misses,
                connected=False,
            )
        
        try:
            info = self._redis.info()
            
            # Count keys with our prefix
            pattern = self._make_key("*")
            total_keys = len(list(self._redis.scan_iter(match=pattern, count=1000)))
            
            return CacheStats(
                hits=info.get("keyspace_hits", 0) + self._local_stats.hits,
                misses=info.get("keyspace_misses", 0) + self._local_stats.misses,
                total_keys=total_keys,
                memory_used=info.get("used_memory_human", "0B"),
                uptime_seconds=info.get("uptime_in_seconds", 0),
                connected=True,
            )
            
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return CacheStats(
                hits=self._local_stats.hits,
                misses=self._local_stats.misses,
                connected=False,
            )
    
    def list_keys(self, pattern: str = "*", limit: int = 100) -> List[CacheEntry]:
        """
        List cache entries matching pattern.
        
        Args:
            pattern: Key pattern
            limit: Maximum number of entries to return
            
        Returns:
            List of CacheEntry objects
        """
        if not self.is_connected:
            return []
        
        try:
            full_pattern = self._make_key(pattern)
            entries = []
            
            for i, key in enumerate(self._redis.scan_iter(match=full_pattern)):
                if i >= limit:
                    break
                
                # Skip metadata and hit counter keys
                key_str = key.decode() if isinstance(key, bytes) else key
                if key_str.endswith(":meta") or key_str.endswith(":hits"):
                    continue
                
                # Get TTL
                ttl = self._redis.ttl(key)
                
                # Get size
                size = self._redis.memory_usage(key) or 0
                
                # Get hit count
                hit_key = f"{key_str}:hits"
                hit_count = int(self._redis.get(hit_key) or 0)
                
                # Get metadata
                meta_key = f"{key_str}:meta"
                meta_data = self._redis.get(meta_key)
                
                created_at = None
                if meta_data:
                    meta = json.loads(meta_data)
                    created_at = meta.get("created_at")
                
                # Calculate expiry
                expires_at = None
                if ttl > 0 and created_at:
                    try:
                        created = datetime.fromisoformat(created_at)
                        expires_at = (created + timedelta(seconds=ttl)).isoformat()
                    except Exception:
                        pass
                
                # Remove prefix from key for display
                display_key = key_str.replace(self.config.key_prefix, "", 1)
                
                entries.append(CacheEntry(
                    key=display_key,
                    created_at=created_at or "unknown",
                    expires_at=expires_at,
                    size_bytes=size,
                    ttl_seconds=ttl,
                    hit_count=hit_count,
                ))
            
            return entries
            
        except Exception as e:
            logger.warning(f"Cache list error: {e}")
            return []
    
    def close(self):
        """Close Redis connection."""
        if self._redis:
            try:
                self._redis.close()
            except Exception:
                pass
            self._redis = None
            self._connected = False


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager


def reset_cache_manager():
    """Reset global cache manager (useful for testing)."""
    global _cache_manager
    
    if _cache_manager:
        _cache_manager.close()
    
    _cache_manager = None
