"""Unit tests for cache layer."""

import pytest
import json
from datetime import datetime, timedelta

from gitrate.core.cache import RedisCache, CacheKeys


class TestCacheKeys:
    """Tests for CacheKeys template class."""
    
    def test_repo_data_key(self):
        """Test repository data cache key."""
        key = CacheKeys.repo_data("pytorch", "pytorch")
        assert key == "repo:pytorch/pytorch:data"
    
    def test_repo_commits_key(self):
        """Test repository commits cache key."""
        key = CacheKeys.repo_commits("pytorch", "pytorch", "90d")
        assert "repo:pytorch/pytorch:commits" in key
        assert "90d" in key
    
    def test_audit_result_key(self):
        """Test audit result cache key."""
        key = CacheKeys.audit_result("a1b2c3d4")
        assert "a1b2c3d4" in key
    
    def test_vulnerability_key(self):
        """Test vulnerability cache key."""
        key = CacheKeys.vulnerability("CVE-2021-12345")
        assert "CVE-2021-12345" in key


class TestRedisCacheMock:
    """Tests for Redis cache operations using mock."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, mock_redis_cache):
        """Test setting and getting value."""
        key = "test:key"
        value = {"data": "test_value"}
        
        result = await mock_redis_cache.set(key, value)
        assert result is True
        
        retrieved = await mock_redis_cache.get(key)
        assert retrieved == value
    
    @pytest.mark.asyncio
    async def test_delete(self, mock_redis_cache):
        """Test deleting value."""
        key = "test:delete"
        await mock_redis_cache.set(key, {"data": "test"})
        
        result = await mock_redis_cache.delete(key)
        assert result is True
        
        retrieved = await mock_redis_cache.get(key)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, mock_redis_cache):
        """Test getting non-existent key."""
        retrieved = await mock_redis_cache.get("nonexistent:key")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_exists(self, mock_redis_cache):
        """Test checking key existence."""
        key = "test:exists"
        await mock_redis_cache.set(key, {"data": "test"})
        
        exists = await mock_redis_cache.exists(key)
        assert exists is True
        
        not_exists = await mock_redis_cache.exists("nonexistent")
        assert not_exists is False
    
    @pytest.mark.asyncio
    async def test_json_serialization(self, mock_redis_cache):
        """Test JSON serialization of complex objects."""
        complex_data = {
            "repo": {
                "owner": "pytorch",
                "stars": 65000,
            },
            "timestamp": datetime(2025, 2, 4).isoformat(),
            "items": [1, 2, 3, 4, 5],
        }
        
        key = "test:complex"
        await mock_redis_cache.set(key, complex_data)
        
        retrieved = await mock_redis_cache.get(key)
        assert retrieved["repo"]["owner"] == "pytorch"
        assert retrieved["items"] == [1, 2, 3, 4, 5]


class TestCacheDisabled:
    """Tests for cache when disabled."""
    
    @pytest.mark.asyncio
    async def test_cache_disabled_set(self):
        """Test set when cache is disabled."""
        cache = RedisCache(redis_url="redis://localhost:6379/0")
        cache.connected = False
        
        result = await cache.set("key", {"data": "value"})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cache_disabled_get(self):
        """Test get when cache is disabled."""
        cache = RedisCache(redis_url="redis://localhost:6379/0")
        cache.connected = False
        
        result = await cache.get("key")
        assert result is None


class TestCachePatternMatching:
    """Tests for pattern-based cache operations."""
    
    @pytest.mark.asyncio
    async def test_clear_pattern(self, mock_redis_cache):
        """Test clearing keys by pattern."""
        # Set multiple keys
        await mock_redis_cache.set("repo:pytorch/pytorch:data", {"data": "1"})
        await mock_redis_cache.set("repo:pytorch/pytorch:commits:90d", {"data": "2"})
        await mock_redis_cache.set("audit:a1b2c3d4:result", {"data": "3"})
        
        # Clear all repo keys
        count = await mock_redis_cache.clear_pattern("repo:*")
        
        # Verify repo keys are deleted
        retrieved = await mock_redis_cache.get("repo:pytorch/pytorch:data")
        assert retrieved is None
        
        # Verify other keys remain
        audit_retrieved = await mock_redis_cache.get("audit:a1b2c3d4:result")
        assert audit_retrieved == {"data": "3"}


class TestCacheTypePreservation:
    """Tests for preserving data types in cache."""
    
    @pytest.mark.asyncio
    async def test_preserve_dict(self, mock_redis_cache):
        """Test preserving dictionary type."""
        data = {"key1": "value1", "key2": 123}
        await mock_redis_cache.set("test:dict", data)
        
        retrieved = await mock_redis_cache.get("test:dict")
        assert isinstance(retrieved, dict)
        assert retrieved["key2"] == 123
    
    @pytest.mark.asyncio
    async def test_preserve_list(self, mock_redis_cache):
        """Test preserving list type."""
        data = ["item1", "item2", "item3"]
        await mock_redis_cache.set("test:list", data)
        
        retrieved = await mock_redis_cache.get("test:list")
        assert isinstance(retrieved, list)
        assert len(retrieved) == 3
    
    @pytest.mark.asyncio
    async def test_preserve_numbers(self, mock_redis_cache):
        """Test preserving numeric types."""
        data = {"int": 42, "float": 3.14}
        await mock_redis_cache.set("test:numbers", data)
        
        retrieved = await mock_redis_cache.get("test:numbers")
        assert retrieved["int"] == 42
        assert abs(retrieved["float"] - 3.14) < 0.01


@pytest.mark.asyncio
async def test_cache_operations_sequence(mock_redis_cache):
    """Test sequence of cache operations."""
    # Set
    await mock_redis_cache.set("test:sequence", {"version": 1})
    
    # Verify exists
    exists = await mock_redis_cache.exists("test:sequence")
    assert exists is True
    
    # Get
    data = await mock_redis_cache.get("test:sequence")
    assert data["version"] == 1
    
    # Update
    await mock_redis_cache.set("test:sequence", {"version": 2})
    data = await mock_redis_cache.get("test:sequence")
    assert data["version"] == 2
    
    # Delete
    deleted = await mock_redis_cache.delete("test:sequence")
    assert deleted is True
    
    # Verify deleted
    data = await mock_redis_cache.get("test:sequence")
    assert data is None
