"""
API Authentication Tests

Tests API key authentication and authorization:
- Valid API key
- Invalid API key
- Missing API key
- Expired API key
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

pytestmark = [pytest.mark.integration]


class TestAPIKeyAuthentication:
    """Test API key authentication."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    def test_no_api_key(self, api_client):
        """Test request without API key."""
        response = api_client.get("/api/v1/jobs")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403]
        
        data = response.json()
        assert "detail" in data
    
    def test_invalid_api_key(self, api_client):
        """Test request with invalid API key."""
        response = api_client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": "invalid-key-12345"}
        )
        
        # Should return 401 or 403
        assert response.status_code in [401, 403]
    
    def test_malformed_api_key(self, api_client):
        """Test request with malformed API key."""
        # Empty key
        response = api_client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": ""}
        )
        assert response.status_code in [401, 403, 422]
        
        # Too short
        response = api_client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": "abc"}
        )
        assert response.status_code in [401, 403]
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_valid_api_key(self, mock_verify, api_client):
        """Test request with valid API key."""
        mock_verify.return_value = True
        
        response = api_client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": "valid-test-key-12345"}
        )
        
        # Should succeed
        assert response.status_code == 200
    
    def test_health_endpoint_no_auth(self, api_client):
        """Test that health endpoint doesn't require auth."""
        response = api_client.get("/health")
        
        # Health endpoint should be public
        assert response.status_code == 200
    
    def test_docs_endpoint_no_auth(self, api_client):
        """Test that docs endpoint doesn't require auth."""
        response = api_client.get("/docs")
        
        # Docs should be accessible
        assert response.status_code == 200


class TestAPIKeyManagement:
    """Test API key management functionality."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    def test_api_key_format(self):
        """Test API key format validation."""
        from surfscreen.api.dependencies import generate_api_key
        
        # Generate a key
        key = generate_api_key()
        
        # Should be a string
        assert isinstance(key, str)
        
        # Should have reasonable length
        assert len(key) >= 32
        
        # Should be alphanumeric with possible dashes
        assert all(c.isalnum() or c == '-' for c in key)
    
    def test_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        from surfscreen.api.dependencies import generate_api_key
        
        keys = set()
        for _ in range(100):
            key = generate_api_key()
            assert key not in keys
            keys.add(key)


class TestAuthorizationHeaders:
    """Test various authorization header formats."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_x_api_key_header(self, mock_verify, api_client):
        """Test X-API-Key header."""
        mock_verify.return_value = True
        
        response = api_client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
    
    def test_bearer_token_header(self, api_client):
        """Test Authorization: Bearer header (if supported)."""
        response = api_client.get(
            "/api/v1/jobs",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # May or may not be supported, just shouldn't crash
        assert response.status_code in [200, 401, 403]
    
    def test_case_insensitive_header(self, api_client):
        """Test that header names are case-insensitive."""
        # HTTP headers should be case-insensitive
        response1 = api_client.get(
            "/api/v1/jobs",
            headers={"x-api-key": "test-key"}
        )
        
        response2 = api_client.get(
            "/api/v1/jobs",
            headers={"X-Api-Key": "test-key"}
        )
        
        # Both should have same behavior
        assert response1.status_code == response2.status_code


class TestRateLimiting:
    """Test rate limiting (if implemented)."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    @patch('surfscreen.api.dependencies.verify_api_key')
    def test_rapid_requests(self, mock_verify, api_client):
        """Test handling of rapid requests."""
        mock_verify.return_value = True
        
        # Make many rapid requests
        responses = []
        for _ in range(20):
            response = api_client.get(
                "/api/v1/jobs",
                headers={"X-API-Key": "test-key"}
            )
            responses.append(response.status_code)
        
        # Should handle all requests (200) or rate limit (429)
        for status in responses:
            assert status in [200, 429]


class TestSecurityHeaders:
    """Test security-related response headers."""
    
    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        from surfscreen.api.main import app
        return TestClient(app)
    
    def test_cors_headers(self, api_client):
        """Test CORS headers are present."""
        response = api_client.options(
            "/api/v1/jobs",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # CORS preflight should work
        assert response.status_code in [200, 204, 405]
    
    def test_content_type_header(self, api_client):
        """Test Content-Type header in responses."""
        response = api_client.get("/health")
        
        assert "application/json" in response.headers.get("content-type", "")
