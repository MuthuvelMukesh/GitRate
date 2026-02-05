"""Rate limiting and API robustness features."""

import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "FIXED_WINDOW"
    SLIDING_WINDOW = "SLIDING_WINDOW"
    TOKEN_BUCKET = "TOKEN_BUCKET"


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, 
                 requests_per_minute: int = 60,
                 strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Request limit per minute
            strategy: Rate limiting strategy
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        self.strategy = strategy
        
        # Track requests per client
        self.requests: Dict[str, list[float]] = defaultdict(list)
        self.tokens: Dict[str, float] = defaultdict(float)
        
        logger.info(f"Initialized RateLimiter ({requests_per_minute} req/min, {strategy.value})")
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """Check if request is allowed for client.
        
        Args:
            client_id: Client identifier (IP, API key, etc)
        
        Returns:
            Tuple of (allowed, headers) where headers contain rate limit info
        """
        if self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._check_sliding_window(client_id)
        elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._check_token_bucket(client_id)
        else:
            return self._check_fixed_window(client_id)
    
    def _check_fixed_window(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """Check fixed window rate limit.
        
        Args:
            client_id: Client identifier
        
        Returns:
            Tuple of (allowed, headers)
        """
        now = time.time()
        minute_ago = now - 60
        
        # Get requests in current minute
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests
        self.requests[client_id] = [r for r in self.requests[client_id] if r > minute_ago]
        
        count = len(self.requests[client_id])
        allowed = count < self.requests_per_minute
        
        if allowed:
            self.requests[client_id].append(now)
        
        return allowed, {
            "X-RateLimit-Limit": self.requests_per_minute,
            "X-RateLimit-Remaining": max(0, self.requests_per_minute - count - 1),
            "X-RateLimit-Reset": int(now + 60),
        }
    
    def _check_sliding_window(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """Check sliding window rate limit.
        
        Args:
            client_id: Client identifier
        
        Returns:
            Tuple of (allowed, headers)
        """
        now = time.time()
        minute_ago = now - 60
        
        # Get requests in last minute
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove requests outside window
        self.requests[client_id] = [r for r in self.requests[client_id] if r > minute_ago]
        
        count = len(self.requests[client_id])
        allowed = count < self.requests_per_minute
        
        if allowed:
            self.requests[client_id].append(now)
        
        # Calculate reset time (when oldest request leaves the window)
        reset_time = (self.requests[client_id][0] + 60) if self.requests[client_id] else int(now + 60)
        
        return allowed, {
            "X-RateLimit-Limit": self.requests_per_minute,
            "X-RateLimit-Remaining": max(0, self.requests_per_minute - count - 1),
            "X-RateLimit-Reset": int(reset_time),
        }
    
    def _check_token_bucket(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """Check token bucket rate limit.
        
        Args:
            client_id: Client identifier
        
        Returns:
            Tuple of (allowed, headers)
        """
        now = time.time()
        
        if client_id not in self.tokens:
            self.tokens[client_id] = self.requests_per_minute
        
        # Add tokens based on elapsed time
        if hasattr(self, '_last_check'):
            elapsed = now - self._last_check.get(client_id, now)
            tokens_to_add = elapsed * self.requests_per_second
            self.tokens[client_id] = min(self.requests_per_minute, self.tokens[client_id] + tokens_to_add)
        
        if not hasattr(self, '_last_check'):
            self._last_check = {}
        self._last_check[client_id] = now
        
        # Check if token available
        allowed = self.tokens[client_id] >= 1.0
        
        if allowed:
            self.tokens[client_id] -= 1.0
        
        # Calculate refill time
        refill_time = (1.0 - self.tokens[client_id]) / self.requests_per_second if self.tokens[client_id] < 1 else 0
        
        return allowed, {
            "X-RateLimit-Limit": self.requests_per_minute,
            "X-RateLimit-Remaining": int(self.tokens[client_id]),
            "X-RateLimit-Reset": int(now + refill_time),
        }
    
    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for client.
        
        Args:
            client_id: Client identifier
        """
        if client_id in self.requests:
            del self.requests[client_id]
        if client_id in self.tokens:
            del self.tokens[client_id]
        logger.info(f"Reset rate limit for client: {client_id}")
    
    def get_status(self, client_id: str) -> Dict[str, any]:
        """Get rate limit status for client.
        
        Args:
            client_id: Client identifier
        
        Returns:
            Status dict
        """
        now = time.time()
        minute_ago = now - 60
        
        if client_id in self.requests:
            recent = [r for r in self.requests[client_id] if r > minute_ago]
        else:
            recent = []
        
        return {
            "client_id": client_id,
            "strategy": self.strategy.value,
            "limit": self.requests_per_minute,
            "requests_in_window": len(recent),
            "remaining": max(0, self.requests_per_minute - len(recent)),
            "reset_in_seconds": 60 - (now - min(recent)) if recent else 0,
        }


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        logger.info(f"Initialized CircuitBreaker (threshold={failure_threshold}, timeout={recovery_timeout}s)")
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception if circuit is open
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker OPEN for {self.expected_exception.__name__}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= 2:
                self.state = "CLOSED"
                self.success_count = 0
                logger.info("Circuit breaker CLOSED")
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPEN (failures: {self.failure_count})")
    
    def _should_attempt_reset(self) -> bool:
        """Check if should attempt recovery.
        
        Returns:
            True if recovery timeout elapsed
        """
        if not self.last_failure_time:
            return True
        
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def get_state(self) -> Dict[str, any]:
        """Get circuit breaker state.
        
        Returns:
            State dict
        """
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout,
        }


class Retry:
    """Retry logic with exponential backoff."""
    
    def __init__(self,
                 max_attempts: int = 3,
                 initial_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0):
        """Initialize retry logic.
        
        Args:
            max_attempts: Maximum retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Exponential backoff factor
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    async def execute(self, func, *args, **kwargs):
        """Execute function with retries.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception if all retries failed
        """
        delay = self.initial_delay
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(self.max_delay, delay * self.backoff_factor)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed")
        
        raise last_exception


import asyncio
