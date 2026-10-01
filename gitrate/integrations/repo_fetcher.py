"""Repository fetcher with caching support."""

import logging
from typing import Optional, Tuple

from gitrate.core.models import RepositoryData
from gitrate.integrations.github_api import GitHubFetcher
from gitrate.core.cache import RedisCache, CacheKeys

logger = logging.getLogger(__name__)


class CachedRepositoryFetcher:
    """Repository fetcher with Redis caching layer."""
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        cache: Optional[RedisCache] = None,
        cache_ttl_seconds: int = 86400,  # 24 hours default
    ):
        """
        Initialize cached fetcher.
        
        Args:
            github_token: GitHub API token
            cache: RedisCache instance (optional)
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.github_fetcher = GitHubFetcher(github_token)
        self.cache = cache
        self.cache_ttl_seconds = cache_ttl_seconds
    
    async def fetch_repository_data(
        self,
        owner: str,
        repo: str,
        bypass_cache: bool = False,
    ) -> Tuple[Optional[RepositoryData], Optional[str]]:
        """
        Fetch repository data with caching.
        
        Args:
            owner: Repository owner
            repo: Repository name
            bypass_cache: Skip cache and force fresh fetch
            
        Returns:
            Tuple of (RepositoryData, error_message)
        """
        
        cache_key = CacheKeys.repo_data(owner, repo)
        
        # Try cache first (unless bypassed)
        if not bypass_cache and self.cache and self.cache.connected:
            logger.debug(f"Checking cache for {owner}/{repo}")
            cached_data = await self.cache.get(cache_key)
            
            if cached_data is not None:
                logger.info(f"✅ Cache HIT for {owner}/{repo}")
                # Reconstruct RepositoryData from cached dict
                try:
                    from gitrate.core.models import RepositoryData
                    return RepositoryData(**cached_data), None
                except Exception as e:
                    logger.warning(f"Error reconstructing cached data: {e}")
                    # Fall through to fetch fresh
        
        # Cache miss or disabled - fetch from API
        logger.info(f"📡 Fetching fresh data for {owner}/{repo}")
        repo_data, error = await self.github_fetcher.fetch_repository_data(owner, repo)
        
        if error:
            logger.error(f"Failed to fetch {owner}/{repo}: {error}")
            return None, error
        
        # Cache the result
        if self.cache and self.cache.connected:
            try:
                cache_dict = repo_data.model_dump()
                # Convert datetime objects to ISO strings for JSON serialization
                cache_dict['fetched_at'] = str(repo_data.fetched_at)
                
                success = await self.cache.set(
                    cache_key,
                    cache_dict,
                    ttl_seconds=self.cache_ttl_seconds,
                )
                
                if success:
                    logger.debug(f"Cached {owner}/{repo} (TTL: {self.cache_ttl_seconds}s)")
                    
            except Exception as e:
                logger.warning(f"Failed to cache repository data: {e}")
        
        return repo_data, None
    
    async def fetch_with_partial_cache(
        self,
        owner: str,
        repo: str,
    ) -> Tuple[Optional[RepositoryData], Optional[str]]:
        """
        Fetch repository data with selective component caching.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Tuple of (RepositoryData, error_message)
        """
        
        logger.info(f"Fetching with partial caching for {owner}/{repo}")
        
        # For now, delegate to full cache mechanism
        # In future, could cache individual components separately
        return await self.fetch_repository_data(owner, repo)
    
    async def clear_cache(self, owner: str, repo: str) -> bool:
        """
        Clear cache for a specific repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            True if successful
        """
        
        if not self.cache or not self.cache.connected:
            return False
        
        cache_key = CacheKeys.repo_data(owner, repo)
        success = await self.cache.delete(cache_key)
        
        if success:
            logger.info(f"Cleared cache for {owner}/{repo}")
        
        return success
    
    async def clear_all_repo_cache(self) -> int:
        """
        Clear all repository-related cache entries.
        
        Returns:
            Number of keys deleted
        """
        
        if not self.cache or not self.cache.connected:
            return 0
        
        count = await self.cache.clear_pattern("repo:*")
        logger.info(f"Cleared {count} repository cache entries")
        return count
