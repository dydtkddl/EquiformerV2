"""
SurfScreen Auth Module

User management and authentication.
"""

from .user_models import User, Team, Quota, UserRole
from .auth_service import AuthService, get_auth_service

__all__ = [
    "User",
    "Team",
    "Quota",
    "UserRole",
    "AuthService",
    "get_auth_service",
]
