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
            name="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )
        
        assert user.user_id == "user-123"
        assert user.name == "testuser"
        assert user.role == UserRole.USER
        assert user.is_active is True
    
    def test_user_to_dict(self):
        """Test user serialization."""
        from surfscreen.auth.user_models import User, UserRole
        
        user = User(
            user_id="user-123",
            name="testuser",
            email="test@example.com",
            role=UserRole.ADMIN,
            created_at="2026-01-01T00:00:00",
        )
        
        data = user.to_dict()
        
        assert data["user_id"] == "user-123"
        assert data["role"] == "admin"


class TestTeam:
    """Tests for Team dataclass."""
    
    def test_team_creation(self):
        """Test team creation."""
        from surfscreen.auth.user_models import Team
        
        team = Team(
            team_id="team-123",
            name="Research Team",
            owner_id="owner-123",
        )
        
        assert team.team_id == "team-123"
        assert team.name == "Research Team"
        assert team.member_ids == []
    
    def test_team_with_members(self):
        """Test team with members."""
        from surfscreen.auth.user_models import Team
        
        team = Team(
            team_id="team-123",
            name="Research Team",
            owner_id="owner-123",
            member_ids=["user-1", "user-2", "user-3"],
        )
        
        assert len(team.member_ids) == 3
        assert "user-2" in team.member_ids


class TestQuota:
    """Tests for Quota dataclass."""
    
    def test_quota_defaults(self):
        """Test default quota values."""
        from surfscreen.auth.user_models import Quota
        
        quota = Quota()
        
        assert quota.max_jobs_per_day == 100
        assert quota.max_compute_hours == 24.0
        assert quota.max_storage_gb == 10.0
        assert quota.max_concurrent_jobs == 5
    
    def test_custom_quota(self):
        """Test custom quota values."""
        from surfscreen.auth.user_models import Quota
        
        quota = Quota(
            max_jobs_per_day=500,
            max_compute_hours=100,
            max_storage_gb=51.2,
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
            name="My API Key",
            key_hash="hashed_key_value",
            created_at="2026-01-01T00:00:00",
        )
        
        assert key.key_id == "key-123"
        assert key.is_active is True
        assert key.last_used is None
    
    def test_apikey_to_dict(self):
        """Test API key serialization."""
        from surfscreen.auth.user_models import APIKey
        
        key = APIKey(
            key_id="key-123",
            name="Limited Key",
            key_hash="hash",
            created_at="2026-01-01T00:00:00",
        )
        
        data = key.to_dict()
        assert data["key_id"] == "key-123"
        assert "key_hash" not in data  # Should not expose hash


class TestUserCreateModel:
    """Tests for UserCreate Pydantic model."""
    
    def test_user_create_valid(self):
        """Test valid user creation request."""
        from surfscreen.auth.user_models import UserCreate
        
        user = UserCreate(
            email="test@example.com",
            name="Test User",
            password="SecurePass123",
        )
        
        assert user.email == "test@example.com"
        assert user.name == "Test User"
    
    def test_user_create_invalid_password(self):
        """Test password validation."""
        from surfscreen.auth.user_models import UserCreate
        import pydantic
        
        # Password without uppercase
        with pytest.raises(pydantic.ValidationError):
            UserCreate(
                email="test@example.com",
                name="Test User",
                password="nocapshere123",
            )


class TestGenerateAPIKey:
    """Tests for API key generation utility."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        from surfscreen.auth.user_models import generate_api_key
        
        key = generate_api_key()
        
        assert key.startswith("sk-")
        assert len(key) > 20
    
    def test_generate_key_id(self):
        """Test key ID generation."""
        from surfscreen.auth.user_models import generate_key_id
        
        key_id = generate_key_id()
        
        assert key_id.startswith("key_")
        assert len(key_id) > 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
