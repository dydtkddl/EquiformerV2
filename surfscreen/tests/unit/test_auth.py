"""
Unit Tests for Auth Module

Tests AuthService, User models, API keys, and quotas.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json
import hashlib


class TestUserRole:
    """Tests for UserRole enum."""
    
    def test_role_values(self):
        """Test user role values."""
        from surfscreen.auth.user_models import UserRole
        
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.VIEWER.value == "viewer"
    
    def test_role_ordering(self):
        """Test role hierarchy."""
        from surfscreen.auth.user_models import UserRole
        
        # Admins have more privileges than users
        assert UserRole.ADMIN.value != UserRole.USER.value
        assert UserRole.VIEWER.value != UserRole.ADMIN.value


class TestUser:
    """Tests for User dataclass."""
    
    def test_user_creation(self):
        """Test user creation."""
        from surfscreen.auth.user_models import User, UserRole
        
        user = User(
            user_id="user-123",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )
        
        assert user.user_id == "user-123"
        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert user.is_active is True
    
    def test_user_to_dict(self):
        """Test user serialization."""
        from surfscreen.auth.user_models import User, UserRole
        
        user = User(
            user_id="user-123",
            username="testuser",
            email="test@example.com",
            role=UserRole.ADMIN,
            created_at="2026-01-01T00:00:00",
        )
        
        data = user.to_dict()
        
        assert data["user_id"] == "user-123"
        assert data["role"] == "admin"
        assert "password_hash" not in data  # Should not include password


class TestTeam:
    """Tests for Team dataclass."""
    
    def test_team_creation(self):
        """Test team creation."""
        from surfscreen.auth.user_models import Team
        
        team = Team(
            team_id="team-123",
            name="Research Team",
            description="Research group",
        )
        
        assert team.team_id == "team-123"
        assert team.name == "Research Team"
        assert team.members == []
    
    def test_team_with_members(self):
        """Test team with members."""
        from surfscreen.auth.user_models import Team
        
        team = Team(
            team_id="team-123",
            name="Research Team",
            members=["user-1", "user-2", "user-3"],
        )
        
        assert len(team.members) == 3
        assert "user-2" in team.members


class TestUserQuota:
    """Tests for UserQuota dataclass."""
    
    def test_quota_defaults(self):
        """Test default quota values."""
        from surfscreen.auth.user_models import UserQuota
        
        quota = UserQuota()
        
        assert quota.max_jobs_per_day == 100
        assert quota.max_compute_hours == 24
        assert quota.max_storage_mb == 10240
        assert quota.max_concurrent_jobs == 5
    
    def test_custom_quota(self):
        """Test custom quota values."""
        from surfscreen.auth.user_models import UserQuota
        
        quota = UserQuota(
            max_jobs_per_day=500,
            max_compute_hours=100,
            max_storage_mb=51200,
        )
        
        assert quota.max_jobs_per_day == 500
        assert quota.max_compute_hours == 100


class TestAPIKey:
    """Tests for APIKey dataclass."""
    
    def test_apikey_creation(self):
        """Test API key creation."""
        from surfscreen.auth.user_models import APIKey
        
        key = APIKey(
            key_id="key-123",
            user_id="user-123",
            name="My API Key",
            key_hash="hashed_key_value",
        )
        
        assert key.key_id == "key-123"
        assert key.is_active is True
        assert key.last_used is None
    
    def test_apikey_with_permissions(self):
        """Test API key with specific permissions."""
        from surfscreen.auth.user_models import APIKey
        
        key = APIKey(
            key_id="key-123",
            user_id="user-123",
            name="Limited Key",
            key_hash="hash",
            permissions=["read", "screening"],
        )
        
        assert "read" in key.permissions
        assert "write" not in key.permissions


class TestAuthService:
    """Tests for AuthService class."""
    
    @pytest.fixture
    def auth_service(self):
        """Create an AuthService instance with temp storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from surfscreen.auth.auth_service import AuthService
            
            service = AuthService(storage_dir=Path(tmpdir))
            yield service
    
    def test_service_creation(self):
        """Test auth service initialization."""
        from surfscreen.auth.auth_service import AuthService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = AuthService(storage_dir=Path(tmpdir))
            
            assert service.storage_dir == Path(tmpdir)
    
    def test_create_user(self, auth_service):
        """Test user creation."""
        from surfscreen.auth.user_models import UserRole
        
        user = auth_service.create_user(
            username="newuser",
            email="new@example.com",
            password="securepassword123",
            role=UserRole.USER,
        )
        
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.role == UserRole.USER
        assert user.user_id in auth_service.users
    
    def test_create_user_duplicate_username(self, auth_service):
        """Test duplicate username prevention."""
        from surfscreen.auth.user_models import UserRole
        
        auth_service.create_user(
            username="existinguser",
            email="first@example.com",
            password="password",
            role=UserRole.USER,
        )
        
        with pytest.raises(ValueError, match="already exists"):
            auth_service.create_user(
                username="existinguser",
                email="second@example.com",
                password="password",
                role=UserRole.USER,
            )
    
    def test_get_user(self, auth_service):
        """Test getting a user."""
        from surfscreen.auth.user_models import UserRole
        
        user = auth_service.create_user(
            username="getuser",
            email="get@example.com",
            password="password",
            role=UserRole.USER,
        )
        
        retrieved = auth_service.get_user(user.user_id)
        
        assert retrieved is user
        assert auth_service.get_user("nonexistent") is None
    
    def test_get_user_by_username(self, auth_service):
        """Test getting user by username."""
        from surfscreen.auth.user_models import UserRole
        
        user = auth_service.create_user(
            username="findme",
            email="find@example.com",
            password="password",
            role=UserRole.USER,
        )
        
        retrieved = auth_service.get_user_by_username("findme")
        
        assert retrieved.user_id == user.user_id
    
    def test_update_user(self, auth_service):
        """Test updating user."""
        from surfscreen.auth.user_models import UserRole
        
        user = auth_service.create_user(
            username="updateme",
            email="update@example.com",
            password="password",
            role=UserRole.USER,
        )
        
        updated = auth_service.update_user(
            user_id=user.user_id,
            email="newemail@example.com",
            role=UserRole.ADMIN,
        )
        
        assert updated.email == "newemail@example.com"
        assert updated.role == UserRole.ADMIN
    
    def test_delete_user(self, auth_service):
        """Test deleting user."""
        from surfscreen.auth.user_models import UserRole
        
        user = auth_service.create_user(
            username="deleteme",
            email="delete@example.com",
            password="password",
            role=UserRole.USER,
        )
        
        success = auth_service.delete_user(user.user_id)
        
        assert success is True
        assert auth_service.get_user(user.user_id) is None
    
    def test_list_users(self, auth_service):
        """Test listing users."""
        from surfscreen.auth.user_models import UserRole
        
        auth_service.create_user("user1", "u1@ex.com", "pw", UserRole.USER)
        auth_service.create_user("user2", "u2@ex.com", "pw", UserRole.ADMIN)
        auth_service.create_user("user3", "u3@ex.com", "pw", UserRole.USER)
        
        # List all
        all_users = auth_service.list_users()
        assert len(all_users) == 3
        
        # Filter by role
        admins = auth_service.list_users(role=UserRole.ADMIN)
        assert len(admins) == 1
    
    def test_verify_password(self, auth_service):
        """Test password verification."""
        from surfscreen.auth.user_models import UserRole
        
        user = auth_service.create_user(
            username="pwtest",
            email="pw@example.com",
            password="correctpassword",
            role=UserRole.USER,
        )
        
        # Correct password
        assert auth_service.verify_password(user.user_id, "correctpassword") is True
        
        # Wrong password
        assert auth_service.verify_password(user.user_id, "wrongpassword") is False


class TestAPIKeyManagement:
    """Tests for API key management."""
    
    @pytest.fixture
    def auth_service_with_user(self):
        """Create auth service with a test user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from surfscreen.auth.auth_service import AuthService
            from surfscreen.auth.user_models import UserRole
            
            service = AuthService(storage_dir=Path(tmpdir))
            user = service.create_user(
                username="apiuser",
                email="api@example.com",
                password="password",
                role=UserRole.USER,
            )
            
            yield service, user
    
    def test_create_api_key(self, auth_service_with_user):
        """Test API key creation."""
        service, user = auth_service_with_user
        
        key, secret = service.create_api_key(
            user_id=user.user_id,
            name="Test Key",
        )
        
        assert key.user_id == user.user_id
        assert key.name == "Test Key"
        assert secret is not None
        assert len(secret) > 20  # Should be a reasonably long key
    
    def test_verify_api_key(self, auth_service_with_user):
        """Test API key verification."""
        service, user = auth_service_with_user
        
        key, secret = service.create_api_key(
            user_id=user.user_id,
            name="Verify Key",
        )
        
        # Valid key
        verified_user = service.verify_api_key(secret)
        assert verified_user is not None
        assert verified_user.user_id == user.user_id
        
        # Invalid key
        assert service.verify_api_key("invalid-key-12345") is None
    
    def test_revoke_api_key(self, auth_service_with_user):
        """Test API key revocation."""
        service, user = auth_service_with_user
        
        key, secret = service.create_api_key(
            user_id=user.user_id,
            name="Revoke Key",
        )
        
        # Revoke key
        success = service.revoke_api_key(key.key_id)
        assert success is True
        
        # Key should no longer work
        assert service.verify_api_key(secret) is None
    
    def test_list_api_keys(self, auth_service_with_user):
        """Test listing user's API keys."""
        service, user = auth_service_with_user
        
        service.create_api_key(user.user_id, "Key 1")
        service.create_api_key(user.user_id, "Key 2")
        service.create_api_key(user.user_id, "Key 3")
        
        keys = service.list_api_keys(user.user_id)
        
        assert len(keys) == 3
        assert all(k.user_id == user.user_id for k in keys)


class TestQuotaManagement:
    """Tests for quota management."""
    
    @pytest.fixture
    def auth_service_with_user(self):
        """Create auth service with a test user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from surfscreen.auth.auth_service import AuthService
            from surfscreen.auth.user_models import UserRole
            
            service = AuthService(storage_dir=Path(tmpdir))
            user = service.create_user(
                username="quotauser",
                email="quota@example.com",
                password="password",
                role=UserRole.USER,
            )
            
            yield service, user
    
    def test_get_default_quota(self, auth_service_with_user):
        """Test getting default quota."""
        service, user = auth_service_with_user
        
        quota = service.get_quota(user.user_id)
        
        assert quota is not None
        assert quota.max_jobs_per_day == 100
    
    def test_update_quota(self, auth_service_with_user):
        """Test updating user quota."""
        service, user = auth_service_with_user
        
        service.update_quota(
            user_id=user.user_id,
            max_jobs_per_day=500,
            max_compute_hours=100,
        )
        
        quota = service.get_quota(user.user_id)
        
        assert quota.max_jobs_per_day == 500
        assert quota.max_compute_hours == 100
    
    def test_check_quota_within_limits(self, auth_service_with_user):
        """Test quota check when within limits."""
        service, user = auth_service_with_user
        
        # Should be within quota by default
        allowed = service.check_quota(user.user_id, "jobs")
        
        assert allowed is True
    
    def test_check_quota_exceeded(self, auth_service_with_user):
        """Test quota check when exceeded."""
        service, user = auth_service_with_user
        
        # Set very low quota
        service.update_quota(user.user_id, max_jobs_per_day=2)
        
        # Record usage up to limit
        service.record_usage(user.user_id, "jobs", 2)
        
        # Should be at quota now
        allowed = service.check_quota(user.user_id, "jobs")
        
        assert allowed is False
    
    def test_record_usage(self, auth_service_with_user):
        """Test recording usage."""
        service, user = auth_service_with_user
        
        service.record_usage(user.user_id, "jobs", 5)
        service.record_usage(user.user_id, "jobs", 3)
        
        usage = service.get_usage(user.user_id)
        
        assert "jobs" in usage
        assert usage["jobs"] == 8
    
    def test_get_usage_summary(self, auth_service_with_user):
        """Test getting usage summary."""
        service, user = auth_service_with_user
        
        service.record_usage(user.user_id, "jobs", 10)
        service.record_usage(user.user_id, "compute_hours", 5.5)
        
        summary = service.get_usage_summary(user.user_id)
        
        assert summary["jobs"]["used"] == 10
        assert summary["jobs"]["limit"] == 100
        assert summary["jobs"]["remaining"] == 90


class TestTeamManagement:
    """Tests for team management."""
    
    @pytest.fixture
    def auth_service_with_users(self):
        """Create auth service with test users."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from surfscreen.auth.auth_service import AuthService
            from surfscreen.auth.user_models import UserRole
            
            service = AuthService(storage_dir=Path(tmpdir))
            users = []
            for i in range(3):
                user = service.create_user(
                    username=f"teamuser{i}",
                    email=f"team{i}@example.com",
                    password="password",
                    role=UserRole.USER,
                )
                users.append(user)
            
            yield service, users
    
    def test_create_team(self, auth_service_with_users):
        """Test team creation."""
        service, users = auth_service_with_users
        
        team = service.create_team(
            name="Test Team",
            description="A test team",
            owner_id=users[0].user_id,
        )
        
        assert team.name == "Test Team"
        assert team.team_id in service.teams
    
    def test_add_member_to_team(self, auth_service_with_users):
        """Test adding member to team."""
        service, users = auth_service_with_users
        
        team = service.create_team(
            name="Test Team",
            owner_id=users[0].user_id,
        )
        
        service.add_team_member(team.team_id, users[1].user_id)
        service.add_team_member(team.team_id, users[2].user_id)
        
        assert len(team.members) == 2
        assert users[1].user_id in team.members
    
    def test_remove_member_from_team(self, auth_service_with_users):
        """Test removing member from team."""
        service, users = auth_service_with_users
        
        team = service.create_team(
            name="Test Team",
            owner_id=users[0].user_id,
        )
        
        service.add_team_member(team.team_id, users[1].user_id)
        service.remove_team_member(team.team_id, users[1].user_id)
        
        assert users[1].user_id not in team.members


class TestPasswordHashing:
    """Tests for password hashing utilities."""
    
    def test_hash_password(self):
        """Test password hashing."""
        from surfscreen.auth.auth_service import AuthService
        
        password = "mysecurepassword"
        hashed = AuthService._hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) == 64  # SHA256 hex digest
    
    def test_verify_hashed_password(self):
        """Test password verification."""
        from surfscreen.auth.auth_service import AuthService
        
        password = "testpassword"
        hashed = AuthService._hash_password(password)
        
        # Correct password
        assert AuthService._verify_password(password, hashed) is True
        
        # Wrong password
        assert AuthService._verify_password("wrongpassword", hashed) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
