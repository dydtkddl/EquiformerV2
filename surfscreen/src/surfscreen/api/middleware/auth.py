"""
Authentication and Authorization Middleware

Provides API key authentication, JWT token verification, and role-based access control.
"""

from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional, List, Callable, Any
from enum import Enum
from functools import wraps
from datetime import datetime, timedelta
import logging
import hashlib
import secrets

try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

logger = logging.getLogger(__name__)


# ============================================
# Security Schemes
# ============================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# ============================================
# User Context
# ============================================

class UserRole(str, Enum):
    """User roles for authorization."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class CurrentUser:
    """Represents the currently authenticated user."""
    
    def __init__(
        self,
        user_id: str,
        username: str,
        role: UserRole,
        permissions: Optional[List[str]] = None,
        team_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions or []
        self.team_id = team_id
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        if self.role == UserRole.ADMIN:
            return True  # Admins have all permissions
        return permission in self.permissions
    
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN


# ============================================
# API Key Authentication
# ============================================

class APIKeyAuthenticator:
    """Authenticates requests using API keys."""
    
    def __init__(self):
        self._auth_service = None
    
    def _get_auth_service(self):
        """Lazily get auth service."""
        if self._auth_service is None:
            try:
                from surfscreen.auth import get_auth_service
                self._auth_service = get_auth_service()
            except ImportError:
                logger.warning("Auth service not available")
                return None
        return self._auth_service
    
    async def authenticate(self, api_key: Optional[str]) -> Optional[CurrentUser]:
        """Authenticate using API key."""
        if not api_key:
            return None
        
        auth_service = self._get_auth_service()
        if not auth_service:
            # Fallback: accept any key in development mode
            if api_key.startswith("dev_"):
                return CurrentUser(
                    user_id="dev-user",
                    username="developer",
                    role=UserRole.ADMIN,
                    permissions=["*"],
                )
            return None
        
        # Verify API key through auth service
        user = auth_service.verify_api_key(api_key)
        if not user:
            return None
        
        return CurrentUser(
            user_id=user.user_id,
            username=user.username,
            role=UserRole(user.role.value),
            permissions=getattr(user, "permissions", []),
            team_id=getattr(user, "team_id", None),
        )


api_key_authenticator = APIKeyAuthenticator()


# ============================================
# JWT Authentication
# ============================================

class JWTAuthenticator:
    """Authenticates requests using JWT tokens."""
    
    def __init__(
        self,
        secret_key: str = "your-secret-key",  # Should be from config
        algorithm: str = "HS256",
        token_expire_hours: int = 24,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_hours = token_expire_hours
    
    def create_token(self, user_id: str, username: str, role: str) -> str:
        """Create a JWT token."""
        if not HAS_JWT:
            raise RuntimeError("PyJWT not installed")
        
        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=self.token_expire_hours),
            "iat": datetime.utcnow(),
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def authenticate(
        self,
        credentials: Optional[HTTPAuthorizationCredentials],
    ) -> Optional[CurrentUser]:
        """Authenticate using JWT token."""
        if not HAS_JWT:
            return None
        
        if not credentials:
            return None
        
        try:
            payload = jwt.decode(
                credentials.credentials,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            
            return CurrentUser(
                user_id=payload["sub"],
                username=payload["username"],
                role=UserRole(payload["role"]),
            )
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None


jwt_authenticator = JWTAuthenticator()


# ============================================
# Authentication Dependencies
# ============================================

async def get_current_user(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Optional[CurrentUser]:
    """
    Get current user from request.
    
    Tries API key first, then JWT token.
    Returns None if not authenticated.
    """
    # Try API key first
    if api_key:
        user = await api_key_authenticator.authenticate(api_key)
        if user:
            return user
    
    # Try JWT token
    if bearer:
        user = await jwt_authenticator.authenticate(bearer)
        if user:
            return user
    
    return None


async def require_auth(
    user: Optional[CurrentUser] = Depends(get_current_user),
) -> CurrentUser:
    """
    Require authentication.
    
    Raises 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """
    Require specific role(s).
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: CurrentUser = Depends(require_role([UserRole.ADMIN]))):
            ...
    """
    async def role_checker(
        user: CurrentUser = Depends(require_auth),
    ) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {[r.value for r in allowed_roles]}",
            )
        return user
    
    return role_checker


def require_permission(permission: str) -> Callable:
    """
    Require specific permission.
    
    Usage:
        @app.post("/jobs")
        async def create_job(user: CurrentUser = Depends(require_permission("jobs:create"))):
            ...
    """
    async def permission_checker(
        user: CurrentUser = Depends(require_auth),
    ) -> CurrentUser:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission}",
            )
        return user
    
    return permission_checker


# ============================================
# Authentication Middleware
# ============================================

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic authentication.
    
    Adds user info to request state if authentication headers are present.
    """
    
    def __init__(
        self,
        app,
        excluded_paths: Optional[List[str]] = None,
        require_auth: bool = False,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]
        self.require_auth = require_auth
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add user to state."""
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(exc) for exc in self.excluded_paths):
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        # Get bearer token
        auth_header = request.headers.get("Authorization")
        bearer = None
        if auth_header and auth_header.startswith("Bearer "):
            bearer = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=auth_header[7:],
            )
        
        # Authenticate
        user = None
        if api_key:
            user = await api_key_authenticator.authenticate(api_key)
        if not user and bearer:
            user = await jwt_authenticator.authenticate(bearer)
        
        # Store user in request state
        request.state.user = user
        
        # Require auth if configured
        if self.require_auth and not user:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "code": "UNAUTHORIZED",
                },
            )
        
        return await call_next(request)


# ============================================
# Utility Functions
# ============================================

def generate_api_key(prefix: str = "sk") -> str:
    """Generate a secure API key."""
    random_bytes = secrets.token_hex(32)
    return f"{prefix}_{random_bytes}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against stored hash."""
    return secrets.compare_digest(
        hash_api_key(api_key),
        stored_hash,
    )
