"""
Rate limiting middleware for FastAPI.

This module provides rate limiting functionality using Redis as the backend.
It supports per-IP and per-user rate limiting.
"""

import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status

try:
    from redis import Redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    Redis = None
    REDIS_AVAILABLE = False

from src.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using Redis as the backend with in-memory fallback.

    Supports:
    - Per-IP rate limiting
    - Per-user rate limiting (when authenticated)
    - Configurable limits per endpoint
    - In-memory fallback when Redis unavailable
    """

    # In-memory storage for rate limits (thread-safe)
    _in_memory_counts: dict = defaultdict(lambda: {"count": 0, "reset_time": 0})
    _lock = threading.Lock()

    def __init__(
        self,
        requests_per_minute: int = 100,
        redis_client: Redis | None = None
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            redis_client: Optional Redis client (will create one if not provided)
        """
        self.requests_per_minute = requests_per_minute
        self.redis = redis_client
        self.window_seconds = 60
        self._redis_available = False

        # Try to get Redis client if not provided
        if self.redis is None and REDIS_AVAILABLE:
            try:
                # Try to connect to Redis
                self.redis = Redis.from_url(
                    settings.effective_redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                # Test connection
                self.redis.ping()
                self._redis_available = True
            except Exception as e:
                logger.warning(f"Redis not available for rate limiting: {e}, using in-memory fallback")
                self.redis = None
        elif self.redis is not None:
            self._redis_available = True
        else:
            logger.warning("Redis library not available for rate limiting, using in-memory fallback")

    def _get_key(self, request: Request, user_id: str | None = None) -> str:
        """
        Generate a rate limit key based on user or IP.

        Args:
            request: FastAPI request
            user_id: Optional authenticated user ID

        Returns:
            Redis key string
        """
        if user_id:
            return f"rate_limit:user:{user_id}"

        # Use client IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"rate_limit:ip:{client_ip}"

    def _get_count(self, key: str) -> int:
        """Get current request count for the key."""
        if self._redis_available:
            try:
                count = self.redis.get(key)
                return int(count) if count else 0
            except RedisError as e:
                logger.error(f"Error getting rate limit count from Redis: {e}")
                # Fall through to in-memory

        # In-memory fallback
        with self._lock:
            now = int(time.time())
            data = self._in_memory_counts[key]

            # Reset if window expired
            if now >= data["reset_time"]:
                data["count"] = 0
                data["reset_time"] = now + self.window_seconds

            return data["count"]

    def _increment_count(self, key: str, ttl: int) -> None:
        """Increment request count and set TTL."""
        if self._redis_available:
            try:
                pipe = self.redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl)
                pipe.execute()
                return
            except RedisError as e:
                logger.error(f"Error incrementing rate limit in Redis: {e}")
                # Fall through to in-memory

        # In-memory fallback
        with self._lock:
            now = int(time.time())
            data = self._in_memory_counts[key]

            # Reset if window expired
            if now >= data["reset_time"]:
                data["count"] = 1
                data["reset_time"] = now + self.window_seconds
            else:
                data["count"] += 1

    def check_limit(self, request: Request, user_id: str | None = None) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            request: FastAPI request
            user_id: Optional authenticated user ID

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time)
        """
        key = self._get_key(request, user_id)

        current_count = self._get_count(key)
        is_allowed = current_count < self.requests_per_minute
        remaining = max(0, self.requests_per_minute - current_count)

        # Increment the count for this request
        self._increment_count(key, self.window_seconds)

        # Calculate reset time
        if self._redis_available:
            try:
                ttl = self.redis.ttl(key)
                if ttl <= 0:
                    ttl = self.window_seconds
                reset_time = int(time.time()) + ttl
            except RedisError:
                reset_time = int(time.time()) + self.window_seconds
        else:
            # Use in-memory reset time
            with self._lock:
                reset_time = self._in_memory_counts[key]["reset_time"]

        return is_allowed, remaining, reset_time

    def get_headers(self, remaining: int, reset_time: int) -> dict:
        """Generate rate limit headers."""
        return {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_minute=settings.rate_limit_requests_per_minute)


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Any]
) -> Any:
    """
    FastAPI middleware for rate limiting.

    This middleware applies rate limiting to all API endpoints.
    It uses the client IP address for anonymous users and user ID for authenticated users.

    Args:
        request: FastAPI request
        call_next: Next middleware/callable in the chain

    Returns:
        Response with rate limit headers or 429 error
    """
    # Skip rate limiting for non-API routes
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # Get user ID from request if authenticated
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        from src.core.auth import verify_token
        token_data = verify_token(token)
        if token_data and token_data.user_id:
            user_id = token_data.user_id

    # Check rate limit
    is_allowed, remaining, reset_time = _rate_limiter.check_limit(request, user_id)

    # Get headers
    headers = _rate_limiter.get_headers(remaining, reset_time)

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers=headers
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers to response
    for key, value in headers.items():
        response.headers[key] = value

    return response


def rate_limit(
    requests_per_minute: int,
    key_func: Callable[[Request], str] | None = None
):
    """
    Decorator for rate limiting specific endpoints.

    Usage:
        @app.get("/endpoint")
        @rate_limit(requests_per_minute=10)
        async def my_endpoint():
            ...

    Args:
        requests_per_minute: Maximum requests per minute
        key_func: Function to generate rate limit key (defaults to IP)
    """
    def decorator(func):  # noqa: D417
        """Apply rate limiting to a function.

        Args:
            func: Function to rate limit

        Returns:
            Callable: Rate-limited function wrapper
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):  # noqa: D417
            """Execute function with rate limiting.

            Args:
                *args: Function arguments
                **kwargs: Function keyword arguments

            Returns:
                Any: Function result
            """
            # Get request from kwargs or args
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                # No request found, skip rate limiting
                return await func(*args, **kwargs)

            # Create custom limiter for this endpoint
            limiter = RateLimiter(requests_per_minute=requests_per_minute)
            user_id = kwargs.get("user_id")

            is_allowed, remaining, reset_time = limiter.check_limit(request, user_id)

            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Endpoint rate limit exceeded ({requests_per_minute}/min)",
                    headers=limiter.get_headers(remaining, reset_time)
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
