"""
Auth Service

User management and authentication service.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from .user_models import (
    User,
    Team,
    Quota,
    UserRole,
    APIKey,
    generate_api_key,
    generate_key_id,
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication and user management service.
    
    Handles user CRUD, API key management, and quota tracking.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize auth service.
        
        Args:
            storage_dir: Directory for persistent storage
        """
        self.storage_dir = storage_dir or Path.cwd() / "auth_data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.users: Dict[str, User] = {}
        self.teams: Dict[str, Team] = {}
        self.api_key_index: Dict[str, str] = {}  # key_hash -> user_id
        
        self._lock = Lock()
        
        # Load persisted data
        self._load_data()
    
    # ========================================
    # User Management
    # ========================================
    
    def create_user(
        self,
        email: str,
        name: str,
        password: str,
        role: UserRole = UserRole.USER,
        team_id: Optional[str] = None,
    ) -> User:
        """
        Create a new user.
        
        Args:
            email: User email
            name: User name
            password: User password (will be hashed)
            role: User role
            team_id: Optional team ID
            
        Returns:
            Created User
        """
        with self._lock:
            # Check for duplicate email
            for user in self.users.values():
                if user.email.lower() == email.lower():
                    raise ValueError(f"Email already exists: {email}")
            
            user_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            user = User(
                user_id=user_id,
                email=email.lower(),
                name=name,
                role=role,
                team_id=team_id,
                quota=Quota(),
                created_at=now,
            )
            
            # Store password hash separately
            password_hash = self._hash_password(password)
            
            self.users[user_id] = user
        
        self._save_data()
        logger.info(f"Created user: {user_id} ({email})")
        
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        with self._lock:
            return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        with self._lock:
            for user in self.users.values():
                if user.email.lower() == email.lower():
                    return user
            return None
    
    def list_users(
        self,
        role: Optional[UserRole] = None,
        team_id: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """List users with optional filtering."""
        with self._lock:
            users = list(self.users.values())
        
        if role:
            users = [u for u in users if u.role == role]
        
        if team_id:
            users = [u for u in users if u.team_id == team_id]
        
        if is_active is not None:
            users = [u for u in users if u.is_active == is_active]
        
        return users
    
    def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        role: Optional[UserRole] = None,
        team_id: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[User]:
        """Update user information."""
        with self._lock:
            user = self.users.get(user_id)
            
            if not user:
                return None
            
            if name:
                user.name = name
            if role:
                user.role = role
            if team_id is not None:
                user.team_id = team_id
            if is_active is not None:
                user.is_active = is_active
        
        self._save_data()
        
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        with self._lock:
            if user_id not in self.users:
                return False
            
            # Remove API keys index entries
            user = self.users[user_id]
            for key in user.api_keys:
                self.api_key_index.pop(key.key_hash, None)
            
            del self.users[user_id]
        
        self._save_data()
        logger.info(f"Deleted user: {user_id}")
        
        return True
    
    # ========================================
    # API Key Management
    # ========================================
    
    def create_api_key(
        self,
        user_id: str,
        name: str,
        expires_days: Optional[int] = None,
    ) -> Tuple[str, APIKey]:
        """
        Create a new API key for a user.
        
        Args:
            user_id: User ID
            name: Key name
            expires_days: Optional expiration in days
            
        Returns:
            Tuple of (raw_key, APIKey object)
        """
        with self._lock:
            user = self.users.get(user_id)
            
            if not user:
                raise ValueError(f"User not found: {user_id}")
            
            # Generate key
            raw_key = generate_api_key()
            key_hash = self._hash_api_key(raw_key)
            key_id = generate_key_id()
            now = datetime.utcnow()
            
            expires_at = None
            if expires_days:
                expires_at = (now + timedelta(days=expires_days)).isoformat()
            
            api_key = APIKey(
                key_id=key_id,
                key_hash=key_hash,
                name=name,
                created_at=now.isoformat(),
                expires_at=expires_at,
            )
            
            user.api_keys.append(api_key)
            self.api_key_index[key_hash] = user_id
        
        self._save_data()
        logger.info(f"Created API key: {key_id} for user {user_id}")
        
        return raw_key, api_key
    
    def verify_api_key(self, raw_key: str) -> Optional[User]:
        """
        Verify an API key and return the associated user.
        
        Args:
            raw_key: Raw API key
            
        Returns:
            User if key is valid, None otherwise
        """
        if not raw_key or not raw_key.startswith("sk-"):
            return None
        
        key_hash = self._hash_api_key(raw_key)
        
        with self._lock:
            user_id = self.api_key_index.get(key_hash)
            
            if not user_id:
                return None
            
            user = self.users.get(user_id)
            
            if not user or not user.is_active:
                return None
            
            # Find the specific key and check expiration
            for api_key in user.api_keys:
                if api_key.key_hash == key_hash:
                    if not api_key.is_active:
                        return None
                    
                    if api_key.expires_at:
                        expires = datetime.fromisoformat(api_key.expires_at)
                        if datetime.utcnow() > expires:
                            return None
                    
                    # Update last used
                    api_key.last_used = datetime.utcnow().isoformat()
                    break
        
        self._save_data()
        
        return user
    
    def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        """Revoke an API key."""
        with self._lock:
            user = self.users.get(user_id)
            
            if not user:
                return False
            
            for i, key in enumerate(user.api_keys):
                if key.key_id == key_id:
                    # Remove from index
                    self.api_key_index.pop(key.key_hash, None)
                    # Remove from user
                    user.api_keys.pop(i)
                    break
            else:
                return False
        
        self._save_data()
        logger.info(f"Revoked API key: {key_id}")
        
        return True
    
    def list_api_keys(self, user_id: str) -> List[APIKey]:
        """List API keys for a user (hashed, not raw keys)."""
        with self._lock:
            user = self.users.get(user_id)
            
            if not user:
                return []
            
            return user.api_keys.copy()
    
    # ========================================
    # Quota Management
    # ========================================
    
    def get_quota(self, user_id: str) -> Optional[Quota]:
        """Get user quota."""
        with self._lock:
            user = self.users.get(user_id)
            return user.quota if user else None
    
    def update_quota(
        self,
        user_id: str,
        max_jobs_per_day: Optional[int] = None,
        max_compute_hours: Optional[float] = None,
        max_storage_gb: Optional[float] = None,
        max_concurrent_jobs: Optional[int] = None,
    ) -> Optional[Quota]:
        """Update user quota limits."""
        with self._lock:
            user = self.users.get(user_id)
            
            if not user:
                return None
            
            if max_jobs_per_day is not None:
                user.quota.max_jobs_per_day = max_jobs_per_day
            if max_compute_hours is not None:
                user.quota.max_compute_hours = max_compute_hours
            if max_storage_gb is not None:
                user.quota.max_storage_gb = max_storage_gb
            if max_concurrent_jobs is not None:
                user.quota.max_concurrent_jobs = max_concurrent_jobs
        
        self._save_data()
        
        return user.quota
    
    def record_job_usage(
        self,
        user_id: str,
        compute_hours: float = 0.0,
        storage_gb: float = 0.0,
    ) -> bool:
        """Record job usage for quota tracking."""
        with self._lock:
            user = self.users.get(user_id)
            
            if not user:
                return False
            
            user.quota.jobs_today += 1
            user.quota.compute_hours_used += compute_hours
            user.quota.storage_gb_used += storage_gb
        
        self._save_data()
        
        return True
    
    def can_submit_job(self, user_id: str) -> bool:
        """Check if user can submit a job based on quota."""
        with self._lock:
            user = self.users.get(user_id)
            
            if not user or not user.is_active:
                return False
            
            return user.quota.can_submit_job()
    
    # ========================================
    # Team Management
    # ========================================
    
    def create_team(self, name: str, owner_id: str) -> Team:
        """Create a new team."""
        with self._lock:
            owner = self.users.get(owner_id)
            
            if not owner:
                raise ValueError(f"Owner not found: {owner_id}")
            
            team_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            team = Team(
                team_id=team_id,
                name=name,
                owner_id=owner_id,
                member_ids=[owner_id],
                quota=Quota(),
                created_at=now,
            )
            
            self.teams[team_id] = team
            owner.team_id = team_id
        
        self._save_data()
        logger.info(f"Created team: {team_id} ({name})")
        
        return team
    
    def add_team_member(self, team_id: str, user_id: str) -> bool:
        """Add a user to a team."""
        with self._lock:
            team = self.teams.get(team_id)
            user = self.users.get(user_id)
            
            if not team or not user:
                return False
            
            if user_id not in team.member_ids:
                team.member_ids.append(user_id)
            
            user.team_id = team_id
        
        self._save_data()
        
        return True
    
    def remove_team_member(self, team_id: str, user_id: str) -> bool:
        """Remove a user from a team."""
        with self._lock:
            team = self.teams.get(team_id)
            user = self.users.get(user_id)
            
            if not team or not user:
                return False
            
            if user_id == team.owner_id:
                return False  # Cannot remove owner
            
            if user_id in team.member_ids:
                team.member_ids.remove(user_id)
            
            user.team_id = None
        
        self._save_data()
        
        return True
    
    # ========================================
    # Helpers
    # ========================================
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _hash_api_key(self, raw_key: str) -> str:
        """Hash an API key using SHA256."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def _save_data(self):
        """Persist data to disk."""
        try:
            data = {
                "users": {
                    uid: {
                        **u.to_dict(include_keys=True),
                        "api_keys": [
                            {
                                "key_id": k.key_id,
                                "key_hash": k.key_hash,
                                "name": k.name,
                                "created_at": k.created_at,
                                "last_used": k.last_used,
                                "expires_at": k.expires_at,
                                "is_active": k.is_active,
                            }
                            for k in u.api_keys
                        ],
                    }
                    for uid, u in self.users.items()
                },
                "teams": {
                    tid: t.to_dict()
                    for tid, t in self.teams.items()
                },
                "api_key_index": self.api_key_index,
            }
            
            path = self.storage_dir / "auth_data.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save auth data: {e}")
    
    def _load_data(self):
        """Load data from disk."""
        path = self.storage_dir / "auth_data.json"
        
        if not path.exists():
            return
        
        try:
            with open(path) as f:
                data = json.load(f)
            
            # Load users
            for uid, udata in data.get("users", {}).items():
                quota = Quota(**udata.get("quota", {}).get("usage", {}))
                limits = udata.get("quota", {}).get("limits", {})
                quota.max_jobs_per_day = limits.get("max_jobs_per_day", 100)
                quota.max_compute_hours = limits.get("max_compute_hours", 24.0)
                quota.max_storage_gb = limits.get("max_storage_gb", 10.0)
                quota.max_concurrent_jobs = limits.get("max_concurrent_jobs", 5)
                
                api_keys = [
                    APIKey(**kdata)
                    for kdata in udata.get("api_keys", [])
                ]
                
                self.users[uid] = User(
                    user_id=uid,
                    email=udata["email"],
                    name=udata["name"],
                    role=UserRole(udata["role"]),
                    team_id=udata.get("team_id"),
                    api_keys=api_keys,
                    quota=quota,
                    created_at=udata.get("created_at", ""),
                    last_login=udata.get("last_login"),
                    is_active=udata.get("is_active", True),
                )
            
            self.api_key_index = data.get("api_key_index", {})
            
            logger.info(f"Loaded {len(self.users)} users")
            
        except Exception as e:
            logger.warning(f"Failed to load auth data: {e}")


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get or create global auth service instance."""
    global _auth_service
    
    if _auth_service is None:
        _auth_service = AuthService()
    
    return _auth_service
