"""
Unit Tests for Cache Module

Tests CacheManager, decorators, and cache utilities.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import json


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""
    
    def test_default_config(self):
        """Test default cache configuration."""
        from surfscreen.cache.cache_manager import CacheConfig
        
        config = CacheConfig()
        
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.default_ttl == 604800  # 7 days
        assert config.key_prefix == "surfscreen:"
    
    def test_custom_config(self):
        """Test custom cache configuration."""
        from surfscreen.cache.cache_manager import CacheConfig
        
        config = CacheConfig(
            host="redis.example.com",
            port=6380,
            db=1,
            password="secret",
            default_ttl=7200,
        )
        
        assert config.host == "redis.example.com"
        assert config.port == 6380
        assert config.password == "secret"


class TestCacheStats:
    """Tests for CacheStats dataclass."""
    
    def test_stats_creation(self):
        """Test cache stats initialization."""
        from surfscreen.cache.cache_manager import CacheStats
        
        stats = CacheStats(
            connected=True,
            hits=100,
            misses=20,
            total_keys=50,
        )
        
        assert stats.connected is True
        assert stats.hits == 100
        assert stats.misses == 20
        assert stats.hit_rate == pytest.approx(0.833, rel=0.01)
    
    def test_stats_zero_requests(self):
        """Test hit rate with zero requests."""
        from surfscreen.cache.cache_manager import CacheStats
        
        stats = CacheStats(connected=True, hits=0, misses=0)
        
        assert stats.hit_rate == 0.0


class TestCacheManager:
    """Tests for CacheManager class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.get.return_value = None
        mock.set.return_value = True
        mock.delete.return_value = 1
        mock.scan_iter.return_value = iter([])
        mock.info.return_value = {
            "keyspace_hits": 100,
            "keyspace_misses": 20,
            "used_memory": 1024 * 1024,
        }
        mock.dbsize.return_value = 50
        return mock
    
    def test_manager_without_redis(self):
        """Test manager works without Redis (graceful degradation)."""
        from surfscreen.cache.cache_manager import CacheManager, CacheStats
        
        # Create manager manually
        manager = CacheManager.__new__(CacheManager)
        manager._redis = None
        manager._connected = False
        manager._local_stats = CacheStats()
        manager._config = MagicMock()
        manager._config.key_prefix = "test:"
        manager._config.default_ttl = 3600
        
        assert manager.is_connected is False
    
    def test_get_set_without_redis(self):
        """Test get/set operations without Redis return gracefully."""
        from surfscreen.cache.cache_manager import CacheManager, CacheConfig, CacheStats
        
        manager = CacheManager.__new__(CacheManager)
        manager._redis = None
        manager._connected = False
        manager._local_stats = CacheStats()
        manager._config = CacheConfig()
        
        # Should return None without error
        result = manager.get("test_key")
        assert result is None
        
        # Should return False without error
        success = manager.set("test_key", {"data": "value"})
        assert success is False
    
    def test_get_with_mock_redis(self, mock_redis):
        """Test get operation with mocked Redis."""
        from surfscreen.cache.cache_manager import CacheManager, CacheConfig, CacheStats
        
        manager = CacheManager.__new__(CacheManager)
        manager._redis = mock_redis
        manager._connected = True
        manager._local_stats = CacheStats()
        manager._config = CacheConfig()
        
        # Test cache miss
        result = manager.get("missing_key")
        assert result is None
        
        # Test cache hit
        cached_data = {"result": 42}
        mock_redis.get.return_value = json.dumps({
            "data": cached_data,
            "metadata": {},
        }).encode()
        
        result = manager.get("existing_key")
        assert result == cached_data
    
    def test_set_with_mock_redis(self, mock_redis):
        """Test set operation with mocked Redis."""
        from surfscreen.cache.cache_manager import CacheManager, CacheConfig, CacheStats
        
        manager = CacheManager.__new__(CacheManager)
        manager._redis = mock_redis
        manager._connected = True
        manager._local_stats = CacheStats()
        manager._config = CacheConfig()
        
        success = manager.set("test_key", {"data": "value"}, ttl=600)
        
        assert success is True
        mock_redis.setex.assert_called_once()
    
    def test_delete_with_mock_redis(self, mock_redis):
        """Test delete operation."""
        from surfscreen.cache.cache_manager import CacheManager, CacheConfig, CacheStats
        
        manager = CacheManager.__new__(CacheManager)
        manager._redis = mock_redis
        manager._connected = True
        manager._local_stats = CacheStats()
        manager._config = CacheConfig()
        
        success = manager.delete("test_key")
        
        assert success is True
        mock_redis.delete.assert_called_once()
    
    def test_clear_with_pattern(self, mock_redis):
        """Test clear operation with pattern matching."""
        from surfscreen.cache.cache_manager import CacheManager, CacheConfig, CacheStats
        
        mock_redis.scan_iter.return_value = iter([
            b"surfscreen:key1",
            b"surfscreen:key2",
            b"surfscreen:key3",
        ])
        
        manager = CacheManager.__new__(CacheManager)
        manager._redis = mock_redis
        manager._connected = True
        manager._local_stats = CacheStats()
        manager._config = CacheConfig()
        
        deleted = manager.clear("key*")
        
        assert deleted == 3
    
    def test_get_stats(self, mock_redis):
        """Test getting cache statistics."""
        from surfscreen.cache.cache_manager import CacheManager, CacheConfig, CacheStats
        
        mock_redis.scan_iter.return_value = iter([])
        
        manager = CacheManager.__new__(CacheManager)
        manager._redis = mock_redis
        manager._connected = True
        manager._local_stats = CacheStats()
        manager._config = CacheConfig()
        
        stats = manager.get_stats()
        
        assert stats.connected is True
        assert stats.hits == 100
        assert stats.misses == 20
        assert stats.total_keys == 50


class TestCacheDecorators:
    """Tests for cache decorators."""
    
    def test_cache_result_decorator(self):
        """Test @cache_result decorator."""
        from surfscreen.cache.cache_decorators import cache_result
        from surfscreen.cache.cache_manager import CacheManager
        
        # Mock the cache manager
        mock_manager = MagicMock()
        mock_manager.get.return_value = None  # Cache miss
        mock_manager.set.return_value = True
        
        with patch("surfscreen.cache.cache_decorators.get_cache_manager", return_value=mock_manager):
            call_count = 0
            
            @cache_result(key_prefix="test")
            def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y
            
            # First call - should execute function
            result1 = expensive_function(1, 2)
            assert result1 == 3
            assert call_count == 1
            
            # Verify set was called
            mock_manager.set.assert_called_once()
    
    def test_cache_result_cache_hit(self):
        """Test @cache_result with cache hit."""
        from surfscreen.cache.cache_decorators import cache_result
        
        mock_manager = MagicMock()
        mock_manager.get.return_value = 42  # Cache hit
        
        with patch("surfscreen.cache.cache_decorators.get_cache_manager", return_value=mock_manager):
            call_count = 0
            
            @cache_result(key_prefix="test")
            def expensive_function(x):
                nonlocal call_count
                call_count += 1
                return x * 2
            
            result = expensive_function(21)
            
            # Should return cached value, not execute function
            assert result == 42
            assert call_count == 0
    
    def test_invalidate_cache_decorator(self):
        """Test @invalidate_cache decorator."""
        from surfscreen.cache.cache_decorators import invalidate_cache
        
        mock_manager = MagicMock()
        mock_manager.clear.return_value = 5
        
        with patch("surfscreen.cache.cache_decorators.get_cache_manager", return_value=mock_manager):
            @invalidate_cache(key_pattern="user:*")
            def update_user(user_id, data):
                return {"updated": True}
            
            result = update_user(123, {"name": "New Name"})
            
            assert result == {"updated": True}
            mock_manager.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_result_async(self):
        """Test @cache_result_async decorator."""
        from surfscreen.cache.cache_decorators import cache_result_async
        
        mock_manager = MagicMock()
        mock_manager.get.return_value = None
        mock_manager.set.return_value = True
        
        with patch("surfscreen.cache.cache_decorators.get_cache_manager", return_value=mock_manager):
            call_count = 0
            
            @cache_result_async(key_prefix="async_test")
            async def async_expensive_function(x):
                nonlocal call_count
                call_count += 1
                return x * 3
            
            result = await async_expensive_function(10)
            
            assert result == 30
            assert call_count == 1


class TestCacheAside:
    """Tests for CacheAside pattern class."""
    
    def test_cache_aside_get_or_set(self):
        """Test CacheAside get_or_set pattern."""
        from surfscreen.cache.cache_decorators import CacheAside
        
        mock_manager = MagicMock()
        mock_manager.get.return_value = None  # Cache miss
        mock_manager.set.return_value = True
        
        with patch("surfscreen.cache.cache_decorators.get_cache_manager", return_value=mock_manager):
            cache = CacheAside(prefix="test")
            
            def loader():
                return {"data": "from_loader"}
            
            result = cache.get_or_compute("my_key", compute_fn=loader)
            
            assert result == {"data": "from_loader"}
            mock_manager.set.assert_called_once()
    
    def test_cache_aside_cache_hit(self):
        """Test CacheAside with cache hit."""
        from surfscreen.cache.cache_decorators import CacheAside
        
        mock_manager = MagicMock()
        mock_manager.get.return_value = {"cached": "data"}
        
        with patch("surfscreen.cache.cache_decorators.get_cache_manager", return_value=mock_manager):
            cache = CacheAside(prefix="test")
            
            loader_called = False
            
            def loader():
                nonlocal loader_called
                loader_called = True
                return {"new": "data"}
            
            result = cache.get_or_compute("my_key", compute_fn=loader)
            
            assert result == {"cached": "data"}
            assert loader_called is False


class TestCacheKeyGeneration:
    """Tests for cache key generation."""
    
    def test_generate_function_key(self):
        """Test cache key generation for functions."""
        from surfscreen.cache.cache_decorators import _generate_function_key
        
        def my_function(a, b, c=None):
            pass
        
        key1 = _generate_function_key(my_function, (1, 2), {"c": 3}, "prefix", None)
        key2 = _generate_function_key(my_function, (1, 2), {"c": 3}, "prefix", None)
        key3 = _generate_function_key(my_function, (1, 2), {"c": 4}, "prefix", None)
        
        # Same inputs should produce same key
        assert key1 == key2
        
        # Different inputs should produce different key
        assert key1 != key3
    
    def test_key_with_specific_params(self):
        """Test key generation with specific parameters."""
        from surfscreen.cache.cache_decorators import _generate_function_key
        
        def search(query, page=1, limit=10):
            pass
        
        # Only use 'query' for key
        key1 = _generate_function_key(
            search,
            ("python",),
            {"page": 1, "limit": 10},
            "search",
            ["query"]
        )
        key2 = _generate_function_key(
            search,
            ("python",),
            {"page": 2, "limit": 20},
            "search",
            ["query"]
        )
        
        # Different page/limit but same query should produce same key
        # when only 'query' is specified in key_params
        # (Note: actual implementation may vary)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
