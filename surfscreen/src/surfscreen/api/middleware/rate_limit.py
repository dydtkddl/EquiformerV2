"""
Rate Limiting Middleware

Provides rate limiting for API endpoints with configurable limits per key/IP.
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
import time
import logging
import asyncio

logger = logging.getLogger(__name__)


# ============================================
# Rate Limit Configuration
# ============================================

class RateLimitPlan(str, Enum):
    """Predefined rate limit plans."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a plan."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int = 10  # Extra requests allowed in burst
    
    @classmethod
    def from_plan(cls, plan: RateLimitPlan) -> "RateLimitConfig":
        """Create config from plan name."""
        plans = {
            RateLimitPlan.FREE: cls(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=500,
                burst_limit=5,
            ),
            RateLimitPlan.BASIC: cls(
                requests_per_minute=30,
                requests_per_hour=500,
                requests_per_day=5000,
                burst_limit=10,
            ),
            RateLimitPlan.PRO: cls(
                requests_per_minute=100,
                requests_per_hour=2000,
                requests_per_day=20000,
                burst_limit=30,
            ),
            RateLimitPlan.ENTERPRISE: cls(
                requests_per_minute=500,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_limit=100,
            ),
            RateLimitPlan.UNLIMITED: cls(
                requests_per_minute=10000,
                requests_per_hour=100000,
                requests_per_day=1000000,
                burst_limit=1000,
            ),
        }
        return plans.get(plan, plans[RateLimitPlan.FREE])


@dataclass
class PathRateLimitConfig:
    """Rate limit for specific path patterns."""
    path_pattern: str  # Regex or prefix match
    requests_per_minute: int
    match_type: str = "prefix"  # "prefix" or "regex"


# ============================================
# Token Bucket Algorithm
# ============================================

@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    last_update: float
    refill_rate: float  # Tokens per second
    
    @classmethod
    def create(cls, capacity: int, refill_rate: float) -> "TokenBucket":
        """Create a new full bucket."""
        return cls(
            capacity=capacity,
            tokens=capacity,
            last_update=time.time(),
            refill_rate=refill_rate,
        )
    
    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens.
        
        Returns (success, retry_after_seconds).
        """
        now = time.time()
        elapsed = now - self.last_update
        
        # Refill tokens
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate,
        )
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        else:
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.refill_rate
            return False, wait_time


# ============================================
# Sliding Window Counter
# ============================================

@dataclass
class WindowCounter:
    """Sliding window rate limit counter."""
    window_size: int  # Window size in seconds
    limit: int
    requests: Dict[int, int] = field(default_factory=dict)
    
    def _current_window(self) -> int:
        """Get current window ID."""
        return int(time.time()) // self.window_size
    
    def _clean_old_windows(self) -> None:
        """Remove old window data."""
        current = self._current_window()
        old_windows = [w for w in self.requests.keys() if w < current - 1]
        for w in old_windows:
            del self.requests[w]
    
    def check(self) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns (allowed, retry_after_seconds).
        """
        self._clean_old_windows()
        
        current = self._current_window()
        prev = current - 1
        
        # Get counts from current and previous windows
        current_count = self.requests.get(current, 0)
        prev_count = self.requests.get(prev, 0)
        
        # Calculate weighted count (sliding window approximation)
        elapsed_in_window = time.time() % self.window_size
        weight = 1.0 - (elapsed_in_window / self.window_size)
        weighted_count = current_count + (prev_count * weight)
        
        if weighted_count < self.limit:
            return True, 0
        else:
            # Time until enough requests expire
            retry_after = int(self.window_size - elapsed_in_window) + 1
            return False, retry_after
    
    def record(self) -> None:
        """Record a request."""
        current = self._current_window()
        self.requests[current] = self.requests.get(current, 0) + 1


# ============================================
# Rate Limiter
# ============================================

class RateLimiter:
    """
    Rate limiter with multiple strategies.
    
    Supports:
    - Per-key (API key or user ID) limiting
    - Per-IP limiting
    - Per-path limiting
    - Combination of above
    """
    
    def __init__(
        self,
        default_config: RateLimitConfig = None,
        path_configs: List[PathRateLimitConfig] = None,
    ):
        self.default_config = default_config or RateLimitConfig.from_plan(RateLimitPlan.FREE)
        self.path_configs = path_configs or []
        
        # Storage for rate limit state
        self._minute_counters: Dict[str, WindowCounter] = defaultdict(
            lambda: WindowCounter(window_size=60, limit=self.default_config.requests_per_minute)
        )
        self._hour_counters: Dict[str, WindowCounter] = defaultdict(
            lambda: WindowCounter(window_size=3600, limit=self.default_config.requests_per_hour)
        )
        self._day_counters: Dict[str, WindowCounter] = defaultdict(
            lambda: WindowCounter(window_size=86400, limit=self.default_config.requests_per_day)
        )
        self._burst_buckets: Dict[str, TokenBucket] = {}
        
        # Key-specific configs
        self._key_configs: Dict[str, RateLimitConfig] = {}
        
        # Cleanup task
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def set_key_config(self, key: str, config: RateLimitConfig) -> None:
        """Set rate limit config for specific key."""
        self._key_configs[key] = config
    
    def _get_config(self, key: str) -> RateLimitConfig:
        """Get config for key."""
        return self._key_configs.get(key, self.default_config)
    
    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create token bucket for key."""
        if key not in self._burst_buckets:
            config = self._get_config(key)
            # Refill rate based on per-minute limit
            refill_rate = config.requests_per_minute / 60.0
            self._burst_buckets[key] = TokenBucket.create(
                capacity=config.burst_limit,
                refill_rate=refill_rate,
            )
        return self._burst_buckets[key]
    
    def _maybe_cleanup(self) -> None:
        """Cleanup old data periodically."""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = now
            # Force cleanup by accessing each counter
            for counter in list(self._minute_counters.values()):
                counter._clean_old_windows()
            for counter in list(self._hour_counters.values()):
                counter._clean_old_windows()
            for counter in list(self._day_counters.values()):
                counter._clean_old_windows()
    
    def check(self, key: str, path: str = None) -> Tuple[bool, int, str]:
        """
        Check if request is allowed.
        
        Args:
            key: Identifier (API key, user ID, or IP)
            path: Request path for path-specific limits
        
        Returns:
            (allowed, retry_after_seconds, limit_type)
        """
        self._maybe_cleanup()
        config = self._get_config(key)
        
        # Update counters with correct limits
        self._minute_counters[key].limit = config.requests_per_minute
        self._hour_counters[key].limit = config.requests_per_hour
        self._day_counters[key].limit = config.requests_per_day
        
        # Check burst limit (token bucket)
        bucket = self._get_bucket(key)
        allowed, retry_after = bucket.consume()
        if not allowed:
            return False, int(retry_after) + 1, "burst"
        
        # Check minute limit
        allowed, retry_after = self._minute_counters[key].check()
        if not allowed:
            return False, retry_after, "minute"
        
        # Check hour limit
        allowed, retry_after = self._hour_counters[key].check()
        if not allowed:
            return False, retry_after, "hour"
        
        # Check day limit
        allowed, retry_after = self._day_counters[key].check()
        if not allowed:
            return False, retry_after, "day"
        
        return True, 0, ""
    
    def record(self, key: str) -> None:
        """Record a request."""
        self._minute_counters[key].record()
        self._hour_counters[key].record()
        self._day_counters[key].record()
    
    def get_remaining(self, key: str) -> Dict[str, int]:
        """Get remaining requests for key."""
        config = self._get_config(key)
        
        minute_counter = self._minute_counters[key]
        current_minute = minute_counter.requests.get(minute_counter._current_window(), 0)
        
        hour_counter = self._hour_counters[key]
        current_hour = sum(hour_counter.requests.values())
        
        day_counter = self._day_counters[key]
        current_day = sum(day_counter.requests.values())
        
        return {
            "minute_remaining": max(0, config.requests_per_minute - current_minute),
            "hour_remaining": max(0, config.requests_per_hour - current_hour),
            "day_remaining": max(0, config.requests_per_day - current_day),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================
# Rate Limit Middleware
# ============================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    Identifies clients by:
    1. API Key (X-API-Key header)
    2. User ID (from authenticated user)
    3. IP address (fallback)
    """
    
    def __init__(
        self,
        app,
        limiter: RateLimiter = None,
        excluded_paths: List[str] = None,
        key_extractor: Callable[[Request], str] = None,
    ):
        super().__init__(app)
        self.limiter = limiter or rate_limiter
        self.excluded_paths = excluded_paths or [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]
        self.key_extractor = key_extractor
    
    def _get_client_key(self, request: Request) -> str:
        """Extract client identifier from request."""
        if self.key_extractor:
            return self.key_extractor(request)
        
        # Try API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:16]}"  # Use prefix for privacy
        
        # Try authenticated user
        user = getattr(request.state, "user", None)
        if user:
            return f"user:{user.user_id}"
        
        # Fall back to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        path = request.url.path
        
        # Skip excluded paths
        if any(path.startswith(exc) for exc in self.excluded_paths):
            return await call_next(request)
        
        # Get client key
        client_key = self._get_client_key(request)
        
        # Check rate limit
        allowed, retry_after, limit_type = self.limiter.check(client_key, path)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_key} "
                f"(type: {limit_type}, retry_after: {retry_after}s)"
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "limit_type": limit_type,
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(
                        self.limiter._get_config(client_key).requests_per_minute
                    ),
                },
            )
        
        # Record request
        self.limiter.record(client_key)
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        remaining = self.limiter.get_remaining(client_key)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute_remaining"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour_remaining"])
        
        return response


# ============================================
# Rate Limit Dependency
# ============================================

def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
) -> Callable:
    """
    Dependency for endpoint-specific rate limiting.
    
    Usage:
        @app.post("/expensive-operation")
        async def expensive_op(
            _: None = Depends(rate_limit(requests_per_minute=5)),
        ):
            ...
    """
    endpoint_limiter = RateLimiter(
        default_config=RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_hour * 24,
        )
    )
    
    async def check_limit(request: Request):
        # Get client key
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        client_key = f"{ip}:{request.url.path}"
        
        allowed, retry_after, limit_type = endpoint_limiter.check(client_key)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Rate limit exceeded for this endpoint",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        
        endpoint_limiter.record(client_key)
        return None
    
    return check_limit
