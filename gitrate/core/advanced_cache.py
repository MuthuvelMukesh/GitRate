"""Advanced caching system with multi-layer support and performance optimization."""

import json
import hashlib
import logging
from typing import Any, Optional, Dict, Callable, TypeVar, Awaitable
from datetime import datetime, timedelta
from functools import wraps
import pickle
from enum import Enum

from gitrate.core.cache import RedisCache
from gitrate.core.models import AcquisitionAuditResult, AuditFinding

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Cache configuration
DEFAULT_TTL_SECONDS = {
    "audit_result": 86400 * 7,      # 7 days
    "findings": 86400 * 7,           # 7 days
    "repository_data": 86400 * 3,    # 3 days
    "report": 86400 * 30,            # 30 days
    "roadmap": 86400 * 7,            # 7 days
    "score": 3600,                   # 1 hour
}


class CacheStrategy(str, Enum):
    """Caching strategies."""
    WRITE_THROUGH = "write_through"  # Write to cache and storage
    WRITE_BACK = "write_back"        # Write to cache, later to storage
    WRITE_AROUND = "write_around"    # Write only to storage
    TTL_BASED = "ttl_based"          # Expiring entries


class CacheLayer:
    """Multi-layer caching system with Redis and in-memory support."""
    
    def __init__(self, redis_cache: Optional[RedisCache] = None):
        """Initialize cache layer.
        
        Args:
            redis_cache: Redis cache instance (optional)
        """
        self.redis = redis_cache
        self.memory_cache: Dict[str, Dict[str, Any]] = {}  # In-memory fallback
        self.cache_hits = 0
        self.cache_misses = 0
        logger.debug("Initialized advanced cache layer")
    
    async def get(self, key: str, cache_type: str = "default") -> Optional[Any]:
        """Get value from cache with fallback chain.
        
        Args:
            key: Cache key
            cache_type: Type of cache for TTL selection
        
        Returns:
            Cached value or None
        """
        # Try Redis first
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    self.cache_hits += 1
                    logger.debug(f"Cache HIT (Redis): {key}")
                    return self._deserialize(value)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fallback to memory cache
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            
            # Check TTL
            if datetime.utcnow() < entry["expires_at"]:
                self.cache_hits += 1
                logger.debug(f"Cache HIT (Memory): {key}")
                return entry["value"]
            else:
                # Remove expired entry
                del self.memory_cache[key]
        
        self.cache_misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None
    
    async def set(self, key: str, value: Any, 
                  ttl_seconds: Optional[int] = None,
                  cache_type: str = "default") -> None:
        """Set value in cache with automatic TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live (uses default if not specified)
            cache_type: Type of cache for default TTL
        """
        ttl = ttl_seconds or DEFAULT_TTL_SECONDS.get(cache_type, 3600)
        
        # Store in Redis
        if self.redis:
            try:
                serialized = self._serialize(value)
                await self.redis.set(key, serialized, ttl=ttl)
                logger.debug(f"Cached to Redis: {key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Always store in memory as fallback
        self.memory_cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
            "created_at": datetime.utcnow(),
        }
        logger.debug(f"Cached to memory: {key} (TTL: {ttl}s)")
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if deleted, False if not found
        """
        deleted = False
        
        # Delete from Redis
        if self.redis:
            try:
                result = await self.redis.delete(key)
                deleted = deleted or bool(result)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        # Delete from memory
        if key in self.memory_cache:
            del self.memory_cache[key]
            deleted = True
        
        if deleted:
            logger.debug(f"Deleted from cache: {key}")
        
        return deleted
    
    async def clear(self) -> None:
        """Clear all caches."""
        self.memory_cache.clear()
        if self.redis:
            try:
                await self.redis.flush()
            except Exception as e:
                logger.warning(f"Redis flush failed: {e}")
        logger.info("Cleared all caches")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict with hit rate, miss rate, memory usage
        """
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0
        
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total_requests": total,
            "hit_rate": hit_rate,
            "memory_entries": len(self.memory_cache),
            "memory_size_kb": sum(
                len(str(e["value"])) for e in self.memory_cache.values()
            ) / 1024,
        }
    
    @staticmethod
    def _serialize(value: Any) -> str:
        """Serialize value for storage.
        
        Args:
            value: Value to serialize
        
        Returns:
            JSON string or pickled data
        """
        try:
            # Try JSON first (more portable)
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            # Fall back to pickle
            return pickle.dumps(value).hex()
    
    @staticmethod
    def _deserialize(value: str) -> Any:
        """Deserialize cached value.
        
        Args:
            value: Serialized value
        
        Returns:
            Deserialized value
        """
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                return pickle.loads(bytes.fromhex(value))
            except Exception:
                return value


def cache_audit_result(ttl_seconds: int = DEFAULT_TTL_SECONDS["audit_result"]):
    """Decorator for caching audit results.
    
    Args:
        ttl_seconds: Time to live in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, owner: str, repo: str, *args, **kwargs) -> tuple[Optional[AcquisitionAuditResult], Optional[str]]:
            # Create cache key
            key = f"audit:{owner}/{repo}"
            
            # Try cache
            cached = await self.cache.get(key, cache_type="audit_result")
            if cached:
                logger.info(f"Returning cached audit result: {key}")
                return cached, None
            
            # Execute function
            result, error = await func(self, owner, repo, *args, **kwargs)
            
            # Cache result
            if result and not error:
                await self.cache.set(key, result, ttl_seconds=ttl_seconds, cache_type="audit_result")
            
            return result, error
        
        return wrapper
    
    return decorator


def cache_with_key(key_generator: Callable, 
                   ttl_seconds: int = 3600,
                   cache_type: str = "default"):
    """Decorator for caching with custom key generation.
    
    Args:
        key_generator: Function to generate cache key
        ttl_seconds: Time to live
        cache_type: Type of cache
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(self, *args, **kwargs) -> T:
            # Generate key
            key = key_generator(*args, **kwargs)
            
            # Try cache
            cached = await self.cache.get(key, cache_type=cache_type)
            if cached is not None:
                logger.debug(f"Cache hit: {key}")
                return cached
            
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Cache result
            if result is not None:
                await self.cache.set(key, result, ttl_seconds=ttl_seconds, cache_type=cache_type)
            
            return result
        
        return wrapper
    
    return decorator


class AuditResultCache:
    """Specialized cache for audit results with domain-specific operations."""
    
    def __init__(self, cache_layer: CacheLayer):
        """Initialize audit result cache.
        
        Args:
            cache_layer: Base cache layer
        """
        self.cache = cache_layer
        self.audit_index: Dict[str, str] = {}  # repo -> audit_id mapping
    
    async def cache_audit(self, result: AcquisitionAuditResult,
                         ttl_seconds: int = DEFAULT_TTL_SECONDS["audit_result"]) -> None:
        """Cache an audit result.
        
        Args:
            result: Audit result to cache
            ttl_seconds: TTL for cache
        """
        key = f"audit:{result.repository}"
        await self.cache.set(key, result, ttl_seconds=ttl_seconds, cache_type="audit_result")
        self.audit_index[result.repository] = result.audit_id
        logger.info(f"Cached audit for {result.repository}: {result.audit_id}")
    
    async def get_audit(self, owner: str, repo: str) -> Optional[AcquisitionAuditResult]:
        """Get cached audit result.
        
        Args:
            owner: Repository owner
            repo: Repository name
        
        Returns:
            Cached audit result or None
        """
        repo_path = f"{owner}/{repo}"
        key = f"audit:{repo_path}"
        return await self.cache.get(key, cache_type="audit_result")
    
    async def cache_findings(self, audit_id: str, findings: list[AuditFinding],
                            ttl_seconds: int = DEFAULT_TTL_SECONDS["findings"]) -> None:
        """Cache findings for an audit.
        
        Args:
            audit_id: Audit identifier
            findings: List of findings
            ttl_seconds: TTL for cache
        """
        key = f"findings:{audit_id}"
        await self.cache.set(key, findings, ttl_seconds=ttl_seconds, cache_type="findings")
        logger.debug(f"Cached {len(findings)} findings for {audit_id}")
    
    async def get_findings(self, audit_id: str) -> Optional[list[AuditFinding]]:
        """Get cached findings.
        
        Args:
            audit_id: Audit identifier
        
        Returns:
            List of findings or None
        """
        key = f"findings:{audit_id}"
        return await self.cache.get(key, cache_type="findings")
    
    async def cache_report(self, audit_id: str, report_bytes: bytes,
                          report_type: str = "pdf",
                          ttl_seconds: int = DEFAULT_TTL_SECONDS["report"]) -> None:
        """Cache generated report.
        
        Args:
            audit_id: Audit identifier
            report_bytes: Report PDF bytes
            report_type: Type of report (pdf, certificate)
            ttl_seconds: TTL for cache
        """
        key = f"report:{audit_id}:{report_type}"
        # Store as base64 for JSON compatibility
        import base64
        encoded = base64.b64encode(report_bytes).decode()
        await self.cache.set(key, encoded, ttl_seconds=ttl_seconds, cache_type="report")
        logger.debug(f"Cached {report_type} report for {audit_id}")
    
    async def get_report(self, audit_id: str, report_type: str = "pdf") -> Optional[bytes]:
        """Get cached report.
        
        Args:
            audit_id: Audit identifier
            report_type: Type of report
        
        Returns:
            Report bytes or None
        """
        key = f"report:{audit_id}:{report_type}"
        cached = await self.cache.get(key, cache_type="report")
        if cached:
            import base64
            return base64.b64decode(cached)
        return None
    
    async def invalidate_audit(self, owner: str, repo: str) -> bool:
        """Invalidate cached audit and related data.
        
        Args:
            owner: Repository owner
            repo: Repository name
        
        Returns:
            True if invalidated
        """
        repo_path = f"{owner}/{repo}"
        key = f"audit:{repo_path}"
        
        # Get audit ID to invalidate findings
        cached = await self.cache.get(key, cache_type="audit_result")
        if cached and hasattr(cached, 'audit_id'):
            await self.cache.delete(f"findings:{cached.audit_id}")
            await self.cache.delete(f"report:{cached.audit_id}:pdf")
            await self.cache.delete(f"report:{cached.audit_id}:certificate")
        
        deleted = await self.cache.delete(key)
        if repo_path in self.audit_index:
            del self.audit_index[repo_path]
        
        logger.info(f"Invalidated audit cache for {repo_path}")
        return deleted
