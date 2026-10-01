"""Redis caching layer for audit operations."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError

from gitrate.utils.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client with TTL support."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (defaults to settings.redis_url)
        """
        self.redis_url = redis_url or settings.redis_url
        self.client: Optional[redis.Redis] = None
        self.connected = False
    
    async def connect(self):
        """Establish Redis connection."""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf8",
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            
            # Test connection
            await self.client.ping()
            self.connected = True
            logger.info("✅ Redis connected successfully")
            
        except ConnectionError as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ Redis error: {e}")
            self.connected = False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.connected = False
            logger.info("Redis disconnected")
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 86400,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON-serialized)
            ttl_seconds: Time-to-live in seconds (default 24h)
            
        Returns:
            True if successful
        """
        
        if not self.connected:
            logger.debug(f"Cache disabled: skipping set for key {key}")
            return False
        
        try:
            # Serialize value to JSON
            json_value = json.dumps(value, default=str)
            
            # Store with TTL
            await self.client.setex(
                key,
                ttl_seconds,
                json_value,
            )
            
            logger.debug(f"Cache SET {key} (ttl={ttl_seconds}s)")
            return True
            
        except RedisError as e:
            logger.warning(f"Cache SET error for {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        
        if not self.connected:
            logger.debug(f"Cache disabled: returning None for key {key}")
            return None
        
        try:
            value = await self.client.get(key)
            
            if value is None:
                logger.debug(f"Cache MISS {key}")
                return None
            
            # Deserialize JSON
            result = json.loads(value)
            logger.debug(f"Cache HIT {key}")
            return result
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache GET error for {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted
        """
        
        if not self.connected:
            return False
        
        try:
            result = await self.client.delete(key)
            if result:
                logger.debug(f"Cache DELETE {key}")
            return bool(result)
            
        except RedisError as e:
            logger.warning(f"Cache DELETE error for {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists
        """
        
        if not self.connected:
            return False
        
        try:
            result = await self.client.exists(key)
            return bool(result)
        except RedisError:
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL in seconds.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds (-1 if no expiry, -2 if not found)
        """
        
        if not self.connected:
            return -2
        
        try:
            return await self.client.ttl(key)
        except RedisError:
            return -2
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "audit:*")
            
        Returns:
            Count of deleted keys
        """
        
        if not self.connected:
            return 0
        
        try:
            keys = await self.client.keys(pattern)
            if not keys:
                return 0
            
            result = await self.client.delete(*keys)
            logger.debug(f"Cache CLEAR pattern '{pattern}' ({result} keys)")
            return result
            
        except RedisError as e:
            logger.warning(f"Cache CLEAR error: {e}")
            return 0
    
    async def flush_all(self) -> bool:
        """
        Clear entire cache.
        
        Returns:
            True if successful
        """
        
        if not self.connected:
            return False
        
        try:
            await self.client.flushdb()
            logger.info("Cache FLUSH all")
            return True
        except RedisError as e:
            logger.warning(f"Cache FLUSH error: {e}")
            return False


# ===== CACHE KEY BUILDERS =====

class CacheKeys:
    """Cache key templates."""
    
    @staticmethod
    def repo_data(owner: str, repo: str) -> str:
        """Repository data cache key."""
        return f"repo:{owner}/{repo}:data"
    
    @staticmethod
    def repo_commits(owner: str, repo: str, window: str = "90d") -> str:
        """Repository commit data cache key."""
        return f"repo:{owner}/{repo}:commits:{window}"
    
    @staticmethod
    def repo_contributors(owner: str, repo: str) -> str:
        """Repository contributors cache key."""
        return f"repo:{owner}/{repo}:contributors"
    
    @staticmethod
    def repo_dependencies(owner: str, repo: str) -> str:
        """Repository dependencies cache key."""
        return f"repo:{owner}/{repo}:dependencies"
    
    @staticmethod
    def repo_testing(owner: str, repo: str) -> str:
        """Repository testing info cache key."""
        return f"repo:{owner}/{repo}:testing"
    
    @staticmethod
    def repo_documentation(owner: str, repo: str) -> str:
        """Repository documentation cache key."""
        return f"repo:{owner}/{repo}:documentation"
    
    @staticmethod
    def audit_result(audit_id: str) -> str:
        """Audit result cache key."""
        return f"audit:{audit_id}:result"
    
    @staticmethod
    def vulnerability(cve_id: str) -> str:
        """Vulnerability data cache key."""
        return f"vulnerability:{cve_id}"
    
    @staticmethod
    def github_rate_limit() -> str:
        """GitHub API rate limit cache key."""
        return "github:rate_limit"


# ===== CACHE DECORATOR =====

def cached(ttl_seconds: int = 86400):
    """
    Decorator for caching async function results.
    
    Args:
        ttl_seconds: Time-to-live in seconds
        
    Example:
        @cached(ttl_seconds=3600)
        async def get_user(user_id: str):
            return await fetch_user_from_db(user_id)
    """
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            if cache and cache.connected:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache HIT for {func.__name__}")
                    return cached_value
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS for {func.__name__}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            if cache and cache.connected:
                await cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    
    return decorator


# ===== GLOBAL CACHE INSTANCE =====

cache: Optional[RedisCache] = None


async def init_cache():
    """Initialize global cache instance."""
    global cache
    cache = RedisCache()
    await cache.connect()


async def shutdown_cache():
    """Shutdown cache connection."""
    global cache
    if cache:
        await cache.disconnect()
