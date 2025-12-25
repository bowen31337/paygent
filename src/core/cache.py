"""
Redis/KV cache connection and management.

This module provides Redis connection and cache operations for the Paygent application.
"""

import logging
import os
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

try:
    from fakeredis import FakeAsyncRedis
    FAKEREDIS_AVAILABLE = True
except ImportError:
    FAKEREDIS_AVAILABLE = False
    FakeAsyncRedis = None

from src.core.config import settings

logger = logging.getLogger(__name__)


# Cache Interface and Metrics Classes
class CacheMetrics:
    """Track cache performance metrics."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_get_time = 0
        self.total_set_time = 0
        self.total_delete_time = 0
        self.get_count = 0
        self.set_count = 0
        self.delete_count = 0

    def record_hit(self):
        """Record a cache hit."""
        self.hits += 1

    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1

    def record_error(self):
        """Record a cache error."""
        self.errors += 1

    def record_get_time(self, elapsed_ms: float, count: int = 1):
        """Record GET operation time."""
        self.total_get_time += elapsed_ms
        self.get_count += count

    def record_set_time(self, elapsed_ms: float, count: int = 1):
        """Record SET operation time."""
        self.total_set_time += elapsed_ms
        self.set_count += count

    def record_delete_time(self, elapsed_ms: float, count: int = 1):
        """Record DELETE operation time."""
        self.total_delete_time += elapsed_ms
        self.delete_count += count

    def record_get(self, count: int = 1):
        """Record GET operations."""
        self.get_count += count

    def record_set(self, count: int = 1):
        """Record SET operations."""
        self.set_count += count

    def record_delete(self, count: int = 1):
        """Record DELETE operations."""
        self.delete_count += count

    def get_metrics(self) -> dict[str, int | float]:
        """Get cache performance metrics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        avg_get_time = (self.total_get_time / self.get_count) if self.get_count > 0 else 0
        avg_set_time = (self.total_set_time / self.set_count) if self.set_count > 0 else 0
        avg_delete_time = (self.total_delete_time / self.delete_count) if self.delete_count > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "avg_get_time_ms": round(avg_get_time, 2),
            "avg_set_time_ms": round(avg_set_time, 2),
            "avg_delete_time_ms": round(avg_delete_time, 2),
        }


class CacheInterface(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Set value in cache with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from cache."""
        pass

    @abstractmethod
    async def set_many(
        self,
        key_value_pairs: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        """Set multiple key-value pairs in cache."""
        pass

    @abstractmethod
    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys from cache."""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching pattern."""
        pass

    @abstractmethod
    async def flush(self) -> bool:
        """Clear all cache entries."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close cache connection."""
        pass

    @abstractmethod
    def get_metrics(self) -> dict[str, int | float]:
        """Get cache performance metrics."""
        pass

    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        """Get cache connection and configuration info."""
        pass


class CacheClient:
    """Redis cache client wrapper for Paygent."""

    def __init__(self):
        self._client: Any | None = None
        self._available = False

    async def connect(self) -> bool:
        """
        Connect to Redis server.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        # Check for test mode - use fakeredis
        use_mock = os.environ.get("USE_MOCK_REDIS", "false").lower() == "true"

        if use_mock and FAKEREDIS_AVAILABLE:
            logger.info("Using FakeAsyncRedis for testing")
            self._client = FakeAsyncRedis()
            self._available = True
            return True

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

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self.available:
            return None
        try:
            value = await self._client.get(key)
            return value
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
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
vercel_cache_client = None


async def init_cache() -> None:
    """Initialize Redis cache connection."""
    await cache_client.connect()

    # Try to initialize Vercel KV cache as well
    try:
        from src.core.vercel_kv import VercelKVCache
        global vercel_cache_client
        vercel_cache_client = VercelKVCache()
        success = await vercel_cache_client.initialize()
        if success:
            logger.info("✓ Vercel KV cache initialized successfully")
        else:
            logger.warning("⚠ Vercel KV cache initialization failed")
    except ImportError:
        logger.debug("Vercel KV cache not available (vercel_kv module not found)")


async def close_cache() -> None:
    """Close Redis cache connection."""
    await cache_client.close()

    # Close Vercel KV cache if available
    if vercel_cache_client:
        await vercel_cache_client.close()


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
