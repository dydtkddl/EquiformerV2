"""
Users API Router

REST API endpoints for user management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import logging

from ...auth import (
    AuthService,
    get_auth_service,
    User,
    UserRole,
)
from ...auth.user_models import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserDetailResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    QuotaUpdate,
    UsageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# ============================================
# Dependencies
# ============================================

def get_auth() -> AuthService:
    """Dependency to get auth service."""
    return get_auth_service()


# ============================================
# User Endpoints
# ============================================

@router.post("", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    auth: AuthService = Depends(get_auth),
):
    """
    Create a new user.
    """
    try:
        user = auth.create_user(
            email=request.email,
            name=request.name,
            password=request.password,
            role=request.role,
            team_id=request.team_id,
        )
        
        return UserResponse(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            role=user.role,
            team_id=user.team_id,
            api_keys_count=len(user.api_keys),
            created_at=user.created_at,
            last_login=user.last_login,
            is_active=user.is_active,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[UserResponse])
async def list_users(
    role: Optional[UserRole] = Query(None),
    team_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    auth: AuthService = Depends(get_auth),
):
    """
    List all users.
    """
    users = auth.list_users(
        role=role,
        team_id=team_id,
        is_active=is_active,
    )
    
    return [
        UserResponse(
            user_id=u.user_id,
            email=u.email,
            name=u.name,
            role=u.role,
            team_id=u.team_id,
            api_keys_count=len(u.api_keys),
            created_at=u.created_at,
            last_login=u.last_login,
            is_active=u.is_active,
        )
        for u in users
    ]


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user(
    # In a real app, this would come from authentication middleware
    # For now, we'll use a placeholder
):
    """
    Get current authenticated user.
    
    Note: This is a placeholder. In production, the user would be
    extracted from the authentication token/API key.
    """
    raise HTTPException(
        status_code=501,
        detail="Authentication middleware not implemented"
    )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    auth: AuthService = Depends(get_auth),
):
    """
    Get user by ID.
    """
    user = auth.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserDetailResponse(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        role=user.role,
        team_id=user.team_id,
        quota=user.quota.to_dict(),
        api_keys=[k.to_dict() for k in user.api_keys],
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    auth: AuthService = Depends(get_auth),
):
    """
    Update user information.
    """
    user = auth.update_user(
        user_id=user_id,
        name=request.name,
        role=request.role,
        team_id=request.team_id,
        is_active=request.is_active,
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        role=user.role,
        team_id=user.team_id,
        api_keys_count=len(user.api_keys),
        created_at=user.created_at,
        last_login=user.last_login,
        is_active=user.is_active,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    auth: AuthService = Depends(get_auth),
):
    """
    Delete a user.
    """
    success = auth.delete_user(user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"deleted": True, "user_id": user_id}


# ============================================
# API Key Endpoints
# ============================================

@router.post("/{user_id}/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    user_id: str,
    request: APIKeyCreate,
    auth: AuthService = Depends(get_auth),
):
    """
    Create a new API key for a user.
    
    Note: The raw key is only returned once. Store it securely.
    """
    try:
        raw_key, api_key = auth.create_api_key(
            user_id=user_id,
            name=request.name,
            expires_days=request.expires_days,
        )
        
        return APIKeyResponse(
            key_id=api_key.key_id,
            key=raw_key,  # Only time the raw key is returned
            name=api_key.name,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    user_id: str,
    auth: AuthService = Depends(get_auth),
):
    """
    List API keys for a user.
    
    Note: Raw keys are not returned, only metadata.
    """
    user = auth.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    keys = auth.list_api_keys(user_id)
    
    return APIKeyListResponse(
        keys=[k.to_dict() for k in keys],
        total=len(keys),
    )


@router.delete("/{user_id}/api-keys/{key_id}")
async def revoke_api_key(
    user_id: str,
    key_id: str,
    auth: AuthService = Depends(get_auth),
):
    """
    Revoke an API key.
    """
    success = auth.revoke_api_key(user_id, key_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"revoked": True, "key_id": key_id}


# ============================================
# Quota/Usage Endpoints
# ============================================

@router.get("/{user_id}/usage", response_model=UsageResponse)
async def get_user_usage(
    user_id: str,
    auth: AuthService = Depends(get_auth),
):
    """
    Get user usage and quota information.
    """
    user = auth.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UsageResponse(
        user_id=user_id,
        quota=user.quota.to_dict(),
        can_submit_job=user.quota.can_submit_job(),
    )


@router.put("/{user_id}/quota")
async def update_user_quota(
    user_id: str,
    request: QuotaUpdate,
    auth: AuthService = Depends(get_auth),
):
    """
    Update user quota limits (admin only).
    """
    quota = auth.update_quota(
        user_id=user_id,
        max_jobs_per_day=request.max_jobs_per_day,
        max_compute_hours=request.max_compute_hours,
        max_storage_gb=request.max_storage_gb,
        max_concurrent_jobs=request.max_concurrent_jobs,
    )
    
    if not quota:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"updated": True, "quota": quota.to_dict()}
