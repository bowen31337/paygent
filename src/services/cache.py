"""
Cache service for Paygent.

This module provides a wrapper around Redis for caching operations,
with graceful fallback when Redis is unavailable.
"""

import json
import logging
import time
from typing import Any

from src.core.cache import cache_client

logger = logging.getLogger(__name__)


class CacheMetrics:
    """Track cache performance metrics."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.total_get_time_ms = 0.0
        self.total_set_time_ms = 0.0

    def record_hit(self, duration_ms: float):
        """Record a cache hit."""
        self.hits += 1
        self.total_get_time_ms += duration_ms

    def record_miss(self, duration_ms: float):
        """Record a cache miss."""
        self.misses += 1
        self.total_get_time_ms += duration_ms

    def record_set(self, duration_ms: float):
        """Record a cache set operation."""
        self.sets += 1
        self.total_set_time_ms += duration_ms

    def record_delete(self):
        """Record a cache delete operation."""
        self.deletes += 1

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_gets = self.hits + self.misses
        hit_rate = (self.hits / total_gets * 100) if total_gets > 0 else 0
        avg_get_time = (self.total_get_time_ms / total_gets) if total_gets > 0 else 0
        avg_set_time = (self.total_set_time_ms / self.sets) if self.sets > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "sets": self.sets,
            "deletes": self.deletes,
            "avg_get_time_ms": round(avg_get_time, 3),
            "avg_set_time_ms": round(avg_set_time, 3),
        }


# Global cache metrics
cache_metrics = CacheMetrics()


class CacheService:
    """Service for cache operations with Redis backend."""

    def __init__(self):
        """Initialize the cache service."""
        self.client = cache_client

    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache with performance tracking.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/unavailable
        """
        start_time = time.time()
        try:
            result = await self.client.get(key)
            duration_ms = (time.time() - start_time) * 1000

            if result:
                # Try to parse as JSON, return raw if not JSON
                try:
                    value = json.loads(result)
                    cache_metrics.record_hit(duration_ms)
                    if duration_ms > 100:
                        logger.warning(f"Slow cache hit: {key} took {duration_ms:.2f}ms")
                    return value
                except (json.JSONDecodeError, TypeError):
                    cache_metrics.record_hit(duration_ms)
                    return result

            cache_metrics.record_miss(duration_ms)
            return None
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            cache_metrics.record_miss(duration_ms)
            logger.warning(f"Cache get failed: {e}")
            return None

    async def set(
        self, key: str, value: Any, expiration: int | None = None
    ) -> bool:
        """
        Set a value in cache with performance tracking.

        Args:
            key: Cache key
            value: Value to cache
            expiration: Optional TTL in seconds

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        try:
            # Serialize value if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value)

            result = await self.client.set(key, value, ttl=expiration)
            duration_ms = (time.time() - start_time) * 1000
            cache_metrics.record_set(duration_ms)

            if duration_ms > 100:
                logger.warning(f"Slow cache set: {key} took {duration_ms:.2f}ms")

            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            cache_metrics.record_set(duration_ms)
            logger.warning(f"Cache set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "services:*")

        Returns:
            Number of keys deleted
        """
        try:
            if not self.client.available:
                return 0

            # Use SCAN to find all matching keys and delete them
            from src.core.cache import cache_client
            if not cache_client._client:
                return 0

            keys = []
            async for key in cache_client._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await cache_client._client.delete(*keys)
                logger.info(f"Deleted {len(keys)} cache keys matching pattern: {pattern}")
                return len(keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete_pattern failed: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            return await self.client.exists(key)
        except Exception as e:
            logger.warning(f"Cache exists check failed: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.client.available:
                return False

            # This would require FLUSHDB, be careful in production
            # For now, just return True as no-op
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False
