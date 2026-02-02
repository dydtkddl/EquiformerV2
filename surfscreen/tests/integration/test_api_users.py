"""
Integration Tests for Users API

Tests user management API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_auth_service():
    """Create a mock AuthService."""
    mock = MagicMock()
    
    # Mock user
    mock_user = MagicMock()
    mock_user.user_id = "user-123"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.role.value = "user"
    mock_user.is_active = True
    mock_user.created_at = "2026-01-01T00:00:00"
    mock_user.to_dict.return_value = {
        "user_id": "user-123",
        "username": "testuser",
        "email": "test@example.com",
        "role": "user",
        "is_active": True,
    }
    
    # Mock API key
    mock_key = MagicMock()
    mock_key.key_id = "key-123"
    mock_key.name = "Test Key"
    mock_key.is_active = True
    mock_key.created_at = "2026-01-01T00:00:00"
    
    # Mock quota
    mock_quota = MagicMock()
    mock_quota.max_jobs_per_day = 100
    mock_quota.max_compute_hours = 24
    mock_quota.max_storage_mb = 10240
    mock_quota.to_dict.return_value = {
        "max_jobs_per_day": 100,
        "max_compute_hours": 24,
        "max_storage_mb": 10240,
    }
    
    mock.create_user.return_value = mock_user
    mock.get_user.return_value = mock_user
    mock.get_user_by_username.return_value = mock_user
    mock.list_users.return_value = [mock_user]
    mock.update_user.return_value = mock_user
    mock.delete_user.return_value = True
    mock.create_api_key.return_value = (mock_key, "sk_test_secret_key_123")
    mock.list_api_keys.return_value = [mock_key]
    mock.revoke_api_key.return_value = True
    mock.get_quota.return_value = mock_quota
    mock.get_usage.return_value = {"jobs": 10, "compute_hours": 2.5}
    mock.get_usage_summary.return_value = {
        "jobs": {"used": 10, "limit": 100, "remaining": 90},
    }
    
    return mock


@pytest.fixture
def client(mock_auth_service):
    """Create test client with mocked auth service."""
    with patch("surfscreen.api.routers.users.get_auth_service", return_value=mock_auth_service):
        from surfscreen.api.main import app
        
        with TestClient(app) as client:
            yield client


class TestUserCreate:
    """Tests for user creation endpoint."""
    
    def test_create_user(self, client, mock_auth_service):
        """Test creating a user."""
        request_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepassword123",
            "role": "user",
        }
        
        response = client.post("/api/v1/users", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user_id" in data
        mock_auth_service.create_user.assert_called_once()
    
    def test_create_user_duplicate_username(self, client, mock_auth_service):
        """Test creating user with duplicate username."""
        mock_auth_service.create_user.side_effect = ValueError("Username already exists")
        
        request_data = {
            "username": "existing",
            "email": "new@example.com",
            "password": "password",
        }
        
        response = client.post("/api/v1/users", json=request_data)
        
        assert response.status_code == 400


class TestUserList:
    """Tests for user list endpoint."""
    
    def test_list_users(self, client, mock_auth_service):
        """Test listing users."""
        response = client.get("/api/v1/users")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
    
    def test_list_users_with_role_filter(self, client, mock_auth_service):
        """Test listing with role filter."""
        response = client.get("/api/v1/users?role=admin")
        
        assert response.status_code == 200


class TestUserGet:
    """Tests for user get endpoint."""
    
    def test_get_user(self, client, mock_auth_service):
        """Test getting a user."""
        response = client.get("/api/v1/users/user-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == "user-123"
    
    def test_get_user_not_found(self, client, mock_auth_service):
        """Test getting non-existent user."""
        mock_auth_service.get_user.return_value = None
        
        response = client.get("/api/v1/users/nonexistent")
        
        assert response.status_code == 404


class TestUserUpdate:
    """Tests for user update endpoint."""
    
    def test_update_user(self, client, mock_auth_service):
        """Test updating a user."""
        request_data = {
            "email": "newemail@example.com",
            "role": "admin",
        }
        
        response = client.put("/api/v1/users/user-123", json=request_data)
        
        assert response.status_code == 200


class TestUserDelete:
    """Tests for user delete endpoint."""
    
    def test_delete_user(self, client, mock_auth_service):
        """Test deleting a user."""
        response = client.delete("/api/v1/users/user-123")
        
        assert response.status_code == 200
        mock_auth_service.delete_user.assert_called_with("user-123")
    
    def test_delete_user_not_found(self, client, mock_auth_service):
        """Test deleting non-existent user."""
        mock_auth_service.delete_user.return_value = False
        mock_auth_service.get_user.return_value = None
        
        response = client.delete("/api/v1/users/nonexistent")
        
        assert response.status_code == 404


class TestAPIKeyManagement:
    """Tests for API key management endpoints."""
    
    def test_create_api_key(self, client, mock_auth_service):
        """Test creating an API key."""
        request_data = {
            "name": "My API Key",
            "permissions": ["read", "write"],
        }
        
        response = client.post("/api/v1/users/user-123/api-keys", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "key_id" in data
        assert "secret" in data  # Secret is returned only on creation
    
    def test_list_api_keys(self, client, mock_auth_service):
        """Test listing API keys."""
        response = client.get("/api/v1/users/user-123/api-keys")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "keys" in data
    
    def test_revoke_api_key(self, client, mock_auth_service):
        """Test revoking an API key."""
        response = client.delete("/api/v1/users/user-123/api-keys/key-123")
        
        assert response.status_code == 200
        mock_auth_service.revoke_api_key.assert_called()


class TestQuotaManagement:
    """Tests for quota management endpoints."""
    
    def test_get_quota(self, client, mock_auth_service):
        """Test getting user quota."""
        response = client.get("/api/v1/users/user-123/quota")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "max_jobs_per_day" in data
    
    def test_update_quota(self, client, mock_auth_service):
        """Test updating user quota."""
        request_data = {
            "max_jobs_per_day": 500,
            "max_compute_hours": 100,
        }
        
        mock_auth_service.update_quota.return_value = mock_auth_service.get_quota.return_value
        
        response = client.put("/api/v1/users/user-123/quota", json=request_data)
        
        assert response.status_code == 200
    
    def test_get_usage(self, client, mock_auth_service):
        """Test getting user usage."""
        response = client.get("/api/v1/users/user-123/usage")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data or "usage" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
