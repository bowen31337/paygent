"""
Vercel KV (Redis) cache implementation for serverless deployment.

Provides Redis-based caching with graceful fallback for local development.
"""
import json
import logging
import os
import time
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

# Import the base cache interface
from src.core.cache import CacheInterface, CacheMetrics

logger = logging.getLogger(__name__)


class VercelKVCache(CacheInterface):
    """
    Vercel KV (Redis) cache implementation with metrics tracking.

    Supports both Vercel environment and local development with fallback.
    """

    def __init__(self):
        self.metrics = CacheMetrics()
        self.redis_client: Optional[redis.Redis] = None
        self._is_connected = False

    async def initialize(self) -> bool:
        """
        Initialize Redis connection using Vercel environment variables.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Get Redis connection URL from Vercel environment
            kv_url = self._get_redis_url()
            if not kv_url:
                logger.warning("No Redis URL found, skipping KV cache initialization")
                return False

            # Parse URL and create connection pool
            url = urlparse(kv_url)

            # Create Redis client with connection pooling
            self.redis_client = redis.Redis(
                host=url.hostname,
                port=url.port or 6379,
                password=url.password,
                db=int(url.path[1:]) if url.path else 0,
                ssl=True if url.scheme == "rediss" else False,
                ssl_cert_reqs=None,  # Vercel KV doesn't require cert verification
                decode_responses=True,  # Automatically decode byte responses to strings
                health_check_interval=30,  # Health check every 30 seconds
                socket_connect_timeout=5,  # 5 second connection timeout
                socket_timeout=5,  # 5 second operation timeout
                retry_on_timeout=True,
                max_connections=50,  # Max connections for Vercel
            )

            # Test connection
            await self.redis_client.ping()
            self._is_connected = True

            logger.info(f"✓ Vercel KV cache initialized successfully: {url.hostname}")
            return True

        except Exception as e:
            logger.error(f"✗ Vercel KV cache initialization failed: {e}")
            return False

    def _get_redis_url(self) -> Optional[str]:
        """
        Get Redis URL from Vercel environment variables.

        Vercel provides these environment variables:
        - VERCEL_KV_URL: Direct KV URL
        - KV_URL: Alternative KV URL
        - VERCEL_KV_REST_API_URL: REST API URL
        - VERCEL_KV_REST_API_TOKEN: REST API token

        Returns:
            Optional[str]: Redis URL or None if not available
        """
        # Try Vercel KV URL first
        kv_url = os.getenv("VERCEL_KV_URL")
        if kv_url:
            logger.info("Found VERCEL_KV_URL")
            return kv_url

        # Try KV URL
        kv_url = os.getenv("KV_URL")
        if kv_url:
            logger.info("Found KV_URL")
            return kv_url

        # Try REST API URL + token combination
        rest_url = os.getenv("VERCEL_KV_REST_API_URL")
        rest_token = os.getenv("VERCEL_KV_REST_API_TOKEN")
        if rest_url and rest_token:
            # Convert REST API URL to Redis URL format
            # Vercel KV REST API format: https://<project-id>-<token>@api.vercel.com
            parsed = urlparse(rest_url)
            if parsed.scheme == "https" and parsed.hostname:
                # Extract project ID and token from URL
                hostname_parts = parsed.hostname.split(".")
                if len(hostname_parts) >= 2:
                    project_id = hostname_parts[0]
                    # Create Redis URL format
                    redis_url = f"rediss://:{rest_token}@{project_id}.upstash.io"
                    logger.info("Found VERCEL_KV_REST_API_URL and VERCEL_KV_REST_API_TOKEN")
                    return redis_url

        logger.debug("No Vercel KV environment variables found")
        return None

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with metrics tracking.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        start_time = time.time()

        try:
            if not self._is_connected or not self.redis_client:
                return None

            value = await self.redis_client.get(key)

            if value is not None:
                # Parse JSON value
                try:
                    parsed_value = json.loads(value)
                    self.metrics.record_hit()
                    logger.debug(f"Cache hit for key: {key}")
                    return parsed_value
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in cache for key: {key}")
                    return None
            else:
                self.metrics.record_miss()
                logger.debug(f"Cache miss for key: {key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.metrics.record_error()
            return None
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_get_time(elapsed)

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Time to live in seconds (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()

        try:
            if not self._is_connected or not self.redis_client:
                return False

            # Serialize value to JSON
            serialized_value = json.dumps(value)

            if ttl_seconds:
                await self.redis_client.setex(key, ttl_seconds, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)

            self.metrics.record_set()
            logger.debug(f"Cache set for key: {key}, TTL: {ttl_seconds}")
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self.metrics.record_error()
            return False
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_set_time(elapsed)

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()

        try:
            if not self._is_connected or not self.redis_client:
                return False

            result = await self.redis_client.delete(key)
            success = result > 0

            if success:
                self.metrics.record_delete()
                logger.debug(f"Cache delete for key: {key}")

            return success

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            self.metrics.record_error()
            return False
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_delete_time(elapsed)

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict of key-value pairs that were found
        """
        if not keys or not self._is_connected or not self.redis_client:
            return {}

        start_time = time.time()
        results = {}

        try:
            # Use MGET for efficient bulk retrieval
            values = await self.redis_client.mget(keys)

            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        parsed_value = json.loads(value)
                        results[key] = parsed_value
                        self.metrics.record_hit()
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in cache for key: {key}")
                        self.metrics.record_miss()
                else:
                    self.metrics.record_miss()

            logger.debug(f"Cache get_many: {len(results)}/{len(keys)} keys found")
            return results

        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            self.metrics.record_error()
            return {}
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_get_time(elapsed, count=len(keys))

    async def set_many(
        self,
        key_value_pairs: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Set multiple key-value pairs in cache.

        Args:
            key_value_pairs: Dict of key-value pairs
            ttl_seconds: Time to live in seconds (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        if not key_value_pairs or not self._is_connected or not self.redis_client:
            return False

        start_time = time.time()

        try:
            # Serialize values
            serialized_pairs = {
                key: json.dumps(value) for key, value in key_value_pairs.items()
            }

            # Use MSET for efficient bulk setting
            await self.redis_client.mset(serialized_pairs)

            # Set TTLs if specified
            if ttl_seconds:
                pipeline = self.redis_client.pipeline()
                for key in key_value_pairs.keys():
                    pipeline.expire(key, ttl_seconds)
                await pipeline.execute()

            self.metrics.record_set(count=len(key_value_pairs))
            logger.debug(
                f"Cache set_many: {len(key_value_pairs)} keys, TTL: {ttl_seconds}"
            )
            return True

        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            self.metrics.record_error()
            return False
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_set_time(elapsed, count=len(key_value_pairs))

    async def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys from cache.

        Args:
            keys: List of cache keys

        Returns:
            Number of keys deleted
        """
        if not keys or not self._is_connected or not self.redis_client:
            return 0

        start_time = time.time()

        try:
            result = await self.redis_client.delete(*keys)
            deleted_count = result if result is not None else 0

            if deleted_count > 0:
                self.metrics.record_delete(count=deleted_count)
                logger.debug(f"Cache delete_many: {deleted_count} keys deleted")

            return deleted_count

        except Exception as e:
            logger.error(f"Cache delete_many error: {e}")
            self.metrics.record_error()
            return 0
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_delete_time(elapsed, count=len(keys))

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get all keys matching pattern.

        Args:
            pattern: Redis pattern (default: "*")

        Returns:
            List of matching keys
        """
        if not self._is_connected or not self.redis_client:
            return []

        try:
            keys = await self.redis_client.keys(pattern)
            return keys
        except Exception as e:
            logger.error(f"Cache keys error: {e}")
            return []

    async def flush(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._is_connected or not self.redis_client:
            return False

        try:
            await self.redis_client.flushdb()
            logger.info("Cache flushed")
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Vercel KV cache connection closed")
            except Exception as e:
                logger.error(f"Error closing Vercel KV cache: {e}")
            finally:
                self.redis_client = None
                self._is_connected = False

    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """Get cache performance metrics."""
        return self.metrics.get_metrics()

    def get_info(self) -> Dict[str, Any]:
        """Get cache connection and configuration info."""
        try:
            if self._is_connected and self.redis_client:
                info = {
                    "type": "Vercel KV (Redis)",
                    "connected": self._is_connected,
                    "metrics": self.metrics.get_metrics(),
                    "redis_info": {
                        "host": self.redis_client.connection_pool.connection_kwargs.get(
                            "host", "unknown"
                        ),
                        "port": self.redis_client.connection_pool.connection_kwargs.get(
                            "port", "unknown"
                        ),
                        "db": self.redis_client.connection_pool.connection_kwargs.get(
                            "db", "unknown"
                        ),
                        "ssl": self.redis_client.connection_pool.connection_kwargs.get(
                            "ssl", False
                        ),
                    },
                }
            else:
                info = {
                    "type": "Vercel KV (Redis)",
                    "connected": False,
                    "reason": "Not initialized or connection lost",
                    "metrics": self.metrics.get_metrics(),
                }
            return info
        except Exception as e:
            return {
                "type": "Vercel KV (Redis)",
                "connected": False,
                "error": str(e),
                "metrics": self.metrics.get_metrics(),
            }