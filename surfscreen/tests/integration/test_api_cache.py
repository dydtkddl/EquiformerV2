"""
Integration Tests for Cache API

Tests cache management API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_cache_manager():
    """Create a mock CacheManager."""
    mock = MagicMock()
    mock.is_connected.return_value = True
    mock.get_stats.return_value = MagicMock(
        connected=True,
        hits=100,
        misses=20,
        hit_rate=0.833,
        total_keys=50,
        memory_used_mb=10.5,
    )
    mock.list_keys.return_value = [
        MagicMock(key="key1", ttl=3600, size=100),
        MagicMock(key="key2", ttl=7200, size=200),
    ]
    mock.get.return_value = {"data": "cached_value"}
    mock.clear.return_value = 5
    mock.delete.return_value = True
    return mock


@pytest.fixture
def client(mock_cache_manager):
    """Create test client with mocked cache."""
    with patch("surfscreen.api.routers.cache.get_cache_manager", return_value=mock_cache_manager):
        from surfscreen.api.main import app
        
        with TestClient(app) as client:
            yield client


class TestCacheStats:
    """Tests for cache stats endpoint."""
    
    def test_get_stats(self, client, mock_cache_manager):
        """Test getting cache statistics."""
        response = client.get("/api/v1/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["connected"] is True
        assert data["hits"] == 100
        assert data["misses"] == 20
    
    def test_get_stats_disconnected(self, client, mock_cache_manager):
        """Test stats when cache is disconnected."""
        mock_cache_manager.get_stats.return_value = MagicMock(
            connected=False,
            hits=0,
            misses=0,
            hit_rate=0.0,
            total_keys=0,
        )
        
        response = client.get("/api/v1/cache/stats")
        
        assert response.status_code == 200
        assert response.json()["connected"] is False


class TestCacheKeys:
    """Tests for cache keys endpoint."""
    
    def test_list_keys(self, client, mock_cache_manager):
        """Test listing cache keys."""
        response = client.get("/api/v1/cache/keys")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "keys" in data
        assert len(data["keys"]) == 2
    
    def test_list_keys_with_pattern(self, client, mock_cache_manager):
        """Test listing keys with pattern filter."""
        response = client.get("/api/v1/cache/keys?pattern=job:*")
        
        assert response.status_code == 200
        mock_cache_manager.list_keys.assert_called()
    
    def test_list_keys_with_limit(self, client, mock_cache_manager):
        """Test listing keys with limit."""
        response = client.get("/api/v1/cache/keys?limit=10")
        
        assert response.status_code == 200


class TestCacheGet:
    """Tests for cache get endpoint."""
    
    def test_get_key(self, client, mock_cache_manager):
        """Test getting a cached value."""
        response = client.get("/api/v1/cache/keys/test_key")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["key"] == "test_key"
        assert data["value"] == {"data": "cached_value"}
    
    def test_get_key_not_found(self, client, mock_cache_manager):
        """Test getting non-existent key."""
        mock_cache_manager.get.return_value = None
        
        response = client.get("/api/v1/cache/keys/nonexistent")
        
        assert response.status_code == 404


class TestCacheClear:
    """Tests for cache clear endpoint."""
    
    def test_clear_all(self, client, mock_cache_manager):
        """Test clearing all cache."""
        response = client.delete("/api/v1/cache?confirm=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted"] == 5
        mock_cache_manager.clear.assert_called()
    
    def test_clear_without_confirm(self, client, mock_cache_manager):
        """Test clear without confirmation."""
        response = client.delete("/api/v1/cache")
        
        assert response.status_code == 400
    
    def test_clear_with_pattern(self, client, mock_cache_manager):
        """Test clearing keys with pattern."""
        response = client.delete("/api/v1/cache?pattern=job:*&confirm=true")
        
        assert response.status_code == 200


class TestCacheDelete:
    """Tests for cache delete endpoint."""
    
    def test_delete_key(self, client, mock_cache_manager):
        """Test deleting a specific key."""
        response = client.delete("/api/v1/cache/keys/test_key")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted"] is True
        mock_cache_manager.delete.assert_called_with("test_key")
    
    def test_delete_key_not_found(self, client, mock_cache_manager):
        """Test deleting non-existent key."""
        mock_cache_manager.delete.return_value = False
        
        response = client.delete("/api/v1/cache/keys/nonexistent")
        
        assert response.status_code == 404


class TestCacheHealth:
    """Tests for cache health endpoint."""
    
    def test_health_check_healthy(self, client, mock_cache_manager):
        """Test health check when cache is healthy."""
        response = client.get("/api/v1/cache/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["connected"] is True
    
    def test_health_check_unhealthy(self, client, mock_cache_manager):
        """Test health check when cache is unhealthy."""
        mock_cache_manager.is_connected.return_value = False
        
        response = client.get("/api/v1/cache/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["connected"] is False


class TestCacheWarmup:
    """Tests for cache warmup endpoint."""
    
    def test_warmup_success(self, client, mock_cache_manager):
        """Test cache warmup."""
        warmup_data = {
            "keys": [
                {"key": "key1", "loader": "screening_results"},
                {"key": "key2", "loader": "md_results"},
            ]
        }
        
        response = client.post("/api/v1/cache/warmup", json=warmup_data)
        
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
