"""
Cache API routes for testing and monitoring cache operations.

This module provides endpoints for testing cache functionality,
including set, get, delete operations, and metrics retrieval.
"""

import asyncio
import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.cache import cache_client, vercel_cache_client

router = APIRouter()


class CacheSetRequest(BaseModel):
    """Request model for cache set operation."""

    key: str = Field(..., description="Cache key")
    value: Any = Field(..., description="Value to cache (will be JSON serialized)")
    ttl_seconds: int | None = Field(
        None, description="Time to live in seconds (optional)"
    )


class CacheSetResponse(BaseModel):
    """Response model for cache set operation."""

    success: bool
    message: str
    key: str
    ttl_seconds: int | None
    backend: str


class CacheGetResponse(BaseModel):
    """Response model for cache get operation."""

    found: bool
    key: str
    value: Any | None
    backend: str


class CacheDeleteResponse(BaseModel):
    """Response model for cache delete operation."""

    success: bool
    message: str
    key: str
    backend: str


class CacheMetricsResponse(BaseModel):
    """Response model for cache metrics."""

    backend: str
    connected: bool
    metrics: dict[str, Any]
    info: dict[str, Any]


@router.post(
    "/test/set",
    response_model=CacheSetResponse,
    summary="Test cache set operation",
    description="Sets a value in the cache with optional TTL. Tests both Redis and Vercel KV backends.",
)
async def test_cache_set(request: CacheSetRequest) -> CacheSetResponse:
    """
    Test cache set operation.

    This endpoint tests setting a value in the cache. It will try:
    1. Vercel KV cache (if available)
    2. Standard Redis cache (if available)

    Args:
        request: Cache set request with key, value, and optional TTL

    Returns:
        CacheSetResponse with operation result
    """
    backend = "none"
    success = False
    message = "No cache backend available"

    # Try Vercel KV first
    if vercel_cache_client and vercel_cache_client._is_connected:
        try:
            success = await vercel_cache_client.set(
                request.key, request.value, request.ttl_seconds
            )
            backend = "vercel_kv"
            message = (
                f"Value set in Vercel KV with TTL: {request.ttl_seconds}"
                if request.ttl_seconds
                else "Value set in Vercel KV"
            )
        except Exception as e:
            message = f"Vercel KV set failed: {str(e)}"

    # Fallback to standard Redis
    elif cache_client.available:
        try:
            success = await cache_client.set(request.key, str(request.value), request.ttl_seconds)
            backend = "redis"
            message = (
                f"Value set in Redis with TTL: {request.ttl_seconds}"
                if request.ttl_seconds
                else "Value set in Redis"
            )
        except Exception as e:
            message = f"Redis set failed: {str(e)}"

    return CacheSetResponse(
        success=success,
        message=message,
        key=request.key,
        ttl_seconds=request.ttl_seconds,
        backend=backend,
    )


@router.get(
    "/test/get/{key}",
    response_model=CacheGetResponse,
    summary="Test cache get operation",
    description="Gets a value from the cache. Tests both Redis and Vercel KV backends.",
)
async def test_cache_get(key: str) -> CacheGetResponse:
    """
    Test cache get operation.

    This endpoint tests getting a value from the cache. It will try:
    1. Vercel KV cache (if available)
    2. Standard Redis cache (if available)

    Args:
        key: Cache key to retrieve

    Returns:
        CacheGetResponse with operation result
    """
    backend = "none"
    found = False
    value = None

    # Try Vercel KV first
    if vercel_cache_client and vercel_cache_client._is_connected:
        try:
            value = await vercel_cache_client.get(key)
            found = value is not None
            backend = "vercel_kv"
        except Exception:
            pass

    # Fallback to standard Redis
    elif cache_client.available:
        try:
            value = await cache_client.get(key)
            found = value is not None
            backend = "redis"
        except Exception:
            pass

    return CacheGetResponse(found=found, key=key, value=value, backend=backend)


@router.delete(
    "/test/delete/{key}",
    response_model=CacheDeleteResponse,
    summary="Test cache delete operation",
    description="Deletes a value from the cache. Tests both Redis and Vercel KV backends.",
)
async def test_cache_delete(key: str) -> CacheDeleteResponse:
    """
    Test cache delete operation.

    This endpoint tests deleting a value from the cache. It will try:
    1. Vercel KV cache (if available)
    2. Standard Redis cache (if available)

    Args:
        key: Cache key to delete

    Returns:
        CacheDeleteResponse with operation result
    """
    backend = "none"
    success = False
    message = "No cache backend available"

    # Try Vercel KV first
    if vercel_cache_client and vercel_cache_client._is_connected:
        try:
            success = await vercel_cache_client.delete(key)
            backend = "vercel_kv"
            message = "Key deleted from Vercel KV" if success else "Key not found in Vercel KV"
        except Exception as e:
            message = f"Vercel KV delete failed: {str(e)}"

    # Fallback to standard Redis
    elif cache_client.available:
        try:
            success = await cache_client.delete(key)
            backend = "redis"
            message = "Key deleted from Redis" if success else "Key not found in Redis"
        except Exception as e:
            message = f"Redis delete failed: {str(e)}"

    return CacheDeleteResponse(success=success, message=message, key=key, backend=backend)


@router.get(
    "/test/metrics",
    response_model=CacheMetricsResponse,
    summary="Get cache metrics",
    description="Returns cache performance metrics and connection info for all backends.",
)
async def get_cache_metrics() -> CacheMetricsResponse:
    """
    Get cache metrics.

    This endpoint returns performance metrics and connection information
    for the available cache backend.

    Returns:
        CacheMetricsResponse with cache metrics
    """
    # Prioritize Vercel KV
    if vercel_cache_client and vercel_cache_client._is_connected:
        return CacheMetricsResponse(
            backend="vercel_kv",
            connected=True,
            metrics=vercel_cache_client.get_metrics(),
            info=vercel_cache_client.get_info(),
        )

    # Fallback to standard Redis
    elif cache_client.available:
        return CacheMetricsResponse(
            backend="redis",
            connected=True,
            metrics={"status": "available"},
            info={"client": "standard_redis"},
        )

    # No cache available
    else:
        return CacheMetricsResponse(
            backend="none",
            connected=False,
            metrics={},
            info={"message": "No cache backend available"},
        )


@router.post(
    "/test/ttl",
    response_model=CacheGetResponse,
    summary="Test cache TTL expiration",
    description="Sets a value with a short TTL, then retrieves it to verify expiration works.",
)
async def test_cache_ttl(ttl_seconds: int = 2) -> CacheGetResponse:
    """
    Test cache TTL expiration.

    This endpoint tests that TTL expiration works correctly by:
    1. Setting a value with a short TTL
    2. Immediately retrieving it (should exist)
    3. Waiting for TTL to expire
    4. Retrieving again (should be gone)

    Args:
        ttl_seconds: TTL in seconds (default: 2)

    Returns:
        CacheGetResponse with test results
    """
    test_key = f"__test_ttl_{int(time.time())}"
    test_value = {"test": "data", "timestamp": time.time()}

    backend = "none"
    found_before = False
    found_after = False
    value = None

    # Try Vercel KV first
    if vercel_cache_client and vercel_cache_client._is_connected:
        backend = "vercel_kv"

        # Set value with TTL
        await vercel_cache_client.set(test_key, test_value, ttl_seconds)

        # Get immediately (should exist)
        value = await vercel_cache_client.get(test_key)
        found_before = value is not None

        # Wait for TTL to expire
        await asyncio.sleep(ttl_seconds + 1)

        # Get again (should be gone)
        value_after = await vercel_cache_client.get(test_key)
        found_after = value_after is not None

    # Fallback to standard Redis
    elif cache_client.available:
        backend = "redis"

        # Set value with TTL
        await cache_client.set(test_key, str(test_value), ttl_seconds)

        # Get immediately (should exist)
        value = await cache_client.get(test_key)
        found_before = value is not None

        # Wait for TTL to expire
        await asyncio.sleep(ttl_seconds + 1)

        # Get again (should be gone)
        value_after = await cache_client.get(test_key)
        found_after = value_after is not None

    return CacheGetResponse(
        found=found_before and not found_after,
        key=test_key,
        value={
            "found_immediately": found_before,
            "found_after_ttl": found_after,
            "ttl_test_passed": found_before and not found_after,
            "ttl_seconds": ttl_seconds,
        },
        backend=backend,
    )
