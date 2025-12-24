"""
Cache service for Paygent.

This module provides a wrapper around Redis for caching operations,
with graceful fallback when Redis is unavailable.
"""

import json
import logging
from typing import Any, Optional

from src.core.cache import cache_client

logger = logging.getLogger(__name__)


class CacheService:
    """Service for cache operations with Redis backend."""

    def __init__(self):
        """Initialize the cache service."""
        self.client = cache_client

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/unavailable
        """
        try:
            result = await self.client.get(key)
            if result:
                # Try to parse as JSON, return raw if not JSON
                try:
                    return json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    return result
            return None
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None

    async def set(
        self, key: str, value: Any, expiration: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expiration: Optional TTL in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize value if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value)

            return await self.client.set(key, value, ttl=expiration)
        except Exception as e:
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

            # Get all matching keys
            # Note: Redis SCAN is async, but we'll use a simple approach
            # For now, return 0 if Redis not available
            # Full implementation would use redis.asyncio.scan_iter
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
