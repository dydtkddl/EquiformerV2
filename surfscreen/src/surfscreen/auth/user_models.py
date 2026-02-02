"""
User Models

Models for user management and authentication.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr, validator
import secrets
import string


class UserRole(str, Enum):
    """User role enumeration."""
    
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


@dataclass
class APIKey:
    """API key information."""
    
    key_id: str
    key_hash: str  # SHA256 hash, not the actual key
    name: str
    created_at: str
    last_used: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "name": self.name,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "expires_at": self.expires_at,
            "is_active": self.is_active,
        }


@dataclass
class Quota:
    """User quota/usage limits."""
    
    max_jobs_per_day: int = 100
    max_compute_hours: float = 24.0
    max_storage_gb: float = 10.0
    max_concurrent_jobs: int = 5
    
    # Current usage
    jobs_today: int = 0
    compute_hours_used: float = 0.0
    storage_gb_used: float = 0.0
    concurrent_jobs: int = 0
    
    last_reset: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "limits": {
                "max_jobs_per_day": self.max_jobs_per_day,
                "max_compute_hours": self.max_compute_hours,
                "max_storage_gb": self.max_storage_gb,
                "max_concurrent_jobs": self.max_concurrent_jobs,
            },
            "usage": {
                "jobs_today": self.jobs_today,
                "compute_hours_used": round(self.compute_hours_used, 2),
                "storage_gb_used": round(self.storage_gb_used, 2),
                "concurrent_jobs": self.concurrent_jobs,
            },
            "last_reset": self.last_reset,
        }
    
    def can_submit_job(self) -> bool:
        """Check if user can submit a new job."""
        return (
            self.jobs_today < self.max_jobs_per_day and
            self.concurrent_jobs < self.max_concurrent_jobs
        )
    
    def reset_daily(self):
        """Reset daily counters."""
        self.jobs_today = 0
        self.last_reset = datetime.utcnow().isoformat()


@dataclass
class User:
    """User model."""
    
    user_id: str
    email: str
    name: str
    role: UserRole = UserRole.USER
    team_id: Optional[str] = None
    
    # API keys (hashed)
    api_keys: List[APIKey] = field(default_factory=list)
    
    # Quota
    quota: Quota = field(default_factory=Quota)
    
    # Metadata
    created_at: str = ""
    last_login: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self, include_keys: bool = False) -> Dict[str, Any]:
        result = {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role.value,
            "team_id": self.team_id,
            "quota": self.quota.to_dict(),
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active": self.is_active,
        }
        
        if include_keys:
            result["api_keys"] = [k.to_dict() for k in self.api_keys]
        else:
            result["api_keys_count"] = len(self.api_keys)
        
        return result


@dataclass
class Team:
    """Team/organization model."""
    
    team_id: str
    name: str
    owner_id: str
    
    # Members
    member_ids: List[str] = field(default_factory=list)
    
    # Team quota (shared among members)
    quota: Quota = field(default_factory=Quota)
    
    # Metadata
    created_at: str = ""
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "member_count": len(self.member_ids),
            "quota": self.quota.to_dict(),
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


# ============================================
# Pydantic Models for API
# ============================================

class UserCreate(BaseModel):
    """Request model for creating a user."""
    
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=256)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.USER
    team_id: Optional[str] = None
    
    @validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v


class UserUpdate(BaseModel):
    """Request model for updating a user."""
    
    name: Optional[str] = Field(None, max_length=256)
    role: Optional[UserRole] = None
    team_id: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response model for user."""
    
    user_id: str
    email: str
    name: str
    role: UserRole
    team_id: Optional[str]
    api_keys_count: int
    created_at: str
    last_login: Optional[str]
    is_active: bool


class UserDetailResponse(BaseModel):
    """Detailed user response with quota."""
    
    user_id: str
    email: str
    name: str
    role: UserRole
    team_id: Optional[str]
    quota: Dict[str, Any]
    api_keys: List[Dict[str, Any]]
    created_at: str
    last_login: Optional[str]


class APIKeyCreate(BaseModel):
    """Request model for creating API key."""
    
    name: str = Field(..., min_length=1, max_length=64)
    expires_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """Response model for API key."""
    
    key_id: str
    key: str  # Only returned on creation
    name: str
    created_at: str
    expires_at: Optional[str]


class APIKeyListResponse(BaseModel):
    """Response model for API key list."""
    
    keys: List[Dict[str, Any]]
    total: int


class QuotaUpdate(BaseModel):
    """Request model for updating quota."""
    
    max_jobs_per_day: Optional[int] = Field(None, ge=1)
    max_compute_hours: Optional[float] = Field(None, ge=0.1)
    max_storage_gb: Optional[float] = Field(None, ge=0.1)
    max_concurrent_jobs: Optional[int] = Field(None, ge=1)


class UsageResponse(BaseModel):
    """Response model for usage statistics."""
    
    user_id: str
    quota: Dict[str, Any]
    can_submit_job: bool


# ============================================
# Utility Functions
# ============================================

def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key."""
    alphabet = string.ascii_letters + string.digits
    return "sk-" + "".join(secrets.choice(alphabet) for _ in range(length))


def generate_key_id() -> str:
    """Generate a key ID."""
    return "key_" + secrets.token_hex(8)
