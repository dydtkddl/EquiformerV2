"""
API Middleware Package

Provides authentication, rate limiting, and other middleware for API security.
"""

from surfscreen.api.middleware.auth import (
    AuthenticationMiddleware,
    CurrentUser,
    UserRole,
    get_current_user,
    require_auth,
    require_role,
    require_permission,
    api_key_authenticator,
    jwt_authenticator,
    generate_api_key,
    hash_api_key,
    verify_api_key_hash,
)

from surfscreen.api.middleware.rate_limit import (
    RateLimitMiddleware,
    RateLimiter,
    RateLimitConfig,
    RateLimitPlan,
    rate_limit,
)

__all__ = [
    # Auth
    "AuthenticationMiddleware",
    "CurrentUser",
    "UserRole",
    "get_current_user",
    "require_auth",
    "require_role",
    "require_permission",
    "api_key_authenticator",
    "jwt_authenticator",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key_hash",
    # Rate Limit
    "RateLimitMiddleware",
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitPlan",
    "rate_limit",
]
