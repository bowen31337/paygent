"""
Redis/KV cache connection and management.

This module provides Redis connection and cache operations for the Paygent application.
"""

import logging
from typing import Optional, Any
from functools import wraps

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from src.core.config import settings

logger = logging.getLogger(__name__)


class CacheClient:
    """Redis cache client wrapper for Paygent."""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._available = False

    async def connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available. Cache functionality disabled.")
            return False

        try:
            # Parse Redis URL
            redis_url = settings.effective_redis_url
            if redis_url.startswith("redis://"):
                # Convert to redis:// for aioredis
                pass

            self._client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

            # Test connection
            await self._client.ping()
            self._available = True
            logger.info(f"Redis connected successfully: {redis_url}")
            return True

        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}")
            self._available = False
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")

    @property
    def available(self) -> bool:
        """Check if Redis is available."""
        return self._available and self._client is not None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.available:
            return None
        try:
            value = await self._client.get(key)
            return value
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self.available:
            return False
        try:
            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.available:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.available:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False


# Global cache client instance
cache_client = CacheClient()


async def init_cache() -> None:
    """Initialize Redis cache connection."""
    await cache_client.connect()


async def close_cache() -> None:
    """Close Redis cache connection."""
    await cache_client.close()


def cache_result(ttl: int = 300):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds (default: 300 = 5 minutes)

    Example:
        @cache_result(ttl=60)
        async def expensive_operation():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cache_client.available:
                return await func(*args, **kwargs)

            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached = await cache_client.get(cache_key)
            if cached:
                return cached

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_client.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
