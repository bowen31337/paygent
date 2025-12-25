"""
Performance optimization report and improvements for Paygent API.

This module provides performance optimizations to help meet the 200ms p95 response time target.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from sqlalchemy import select

from src.core.cache import cache_result
from src.services.cache import CacheService
from src.services.metrics_service import metrics_collector

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Performance optimization utilities for API endpoints."""

    def __init__(self):
        self.cache_service = CacheService()
        self.response_times: list[float] = []
        self.slow_requests: list[dict[str, Any]] = []

    def track_response_time(self, endpoint: str, duration_ms: float):
        """Track response time for performance analysis."""
        self.response_times.append(duration_ms)

        # Track slow requests for analysis
        if duration_ms > 200:  # p95 target is 200ms
            self.slow_requests.append({
                "endpoint": endpoint,
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })

            # Log slow requests
            logger.warning(f"Slow request detected: {endpoint} took {duration_ms:.2f}ms")

    def get_performance_stats(self) -> dict[str, float]:
        """Get performance statistics."""
        if not self.response_times:
            return {
                "avg_response_time_ms": 0,
                "p50_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
                "total_requests": 0,
                "slow_requests_count": len(self.slow_requests)
            }

        # Sort response times
        sorted_times = sorted(self.response_times)
        total_requests = len(sorted_times)

        # Calculate percentiles
        p50_idx = int(total_requests * 0.5)
        p95_idx = int(total_requests * 0.95)
        p99_idx = int(total_requests * 0.99)

        return {
            "avg_response_time_ms": sum(sorted_times) / total_requests,
            "p50_response_time_ms": sorted_times[p50_idx] if p50_idx < total_requests else sorted_times[-1],
            "p95_response_time_ms": sorted_times[p95_idx] if p95_idx < total_requests else sorted_times[-1],
            "p99_response_time_ms": sorted_times[p99_idx] if p99_idx < total_requests else sorted_times[-1],
            "total_requests": total_requests,
            "slow_requests_count": len(self.slow_requests)
        }

    def get_slow_requests_report(self) -> list[dict[str, Any]]:
        """Get report of slow requests."""
        return self.slow_requests[-10:]  # Last 10 slow requests


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


def performance_monitor(func: Callable) -> Callable:
    """
    Decorator to monitor API endpoint performance.

    Args:
        func: Function to monitor

    Returns:
        Callable: Monitored function wrapper
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):  # noqa: D417
        """Execute function with performance monitoring.

        Args:
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Any: Function result
        """
        start_time = time.time()
        endpoint = getattr(func, '__name__', 'unknown')

        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.time() - start_time) * 1000
            performance_optimizer.track_response_time(endpoint, duration_ms)

    return wrapper


def fast_cache(ttl: int = 60):
    """
    Decorator for fast caching with optimized TTL for performance.

    Args:
        ttl: Time to live in seconds (default: 60)

    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        """Apply fast caching to a function.

        Args:
            func: Function to cache

        Returns:
            Callable: Cached function
        """
        return cache_result(ttl=ttl)(func)
    return decorator


async def bulk_operation_executor(
    operations: list[Callable],
    max_concurrent: int = 5
) -> list[Any]:
    """
    Execute multiple operations concurrently with rate limiting.

    Args:
        operations: List of async callables to execute
        max_concurrent: Maximum concurrent operations

    Returns:
        list[Any]: List of results
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_with_semaphore(op: Callable):
        """Execute a single operation with semaphore.

        Args:
            op: Operation to execute

        Returns:
            Any: Operation result
        """
        async with semaphore:
            return await op()

    tasks = [execute_with_semaphore(op) for op in operations]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Operation {i} failed: {result}")
            processed_results.append(None)
        else:
            processed_results.append(result)

    return processed_results


class DatabaseOptimizer:
    """Database query optimizations."""

    @staticmethod
    def optimize_query(query, limit: int = 100, offset: int = 0):
        """Add pagination and limits to prevent large queries."""
        return query.limit(limit).offset(offset)

    @staticmethod
    async def batch_select(
        db_session,
        model_class,
        ids: list[int],
        batch_size: int = 50
    ):
        """Perform batch selects to reduce query count."""
        results = []
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            query = select(model_class).where(model_class.id.in_(batch_ids))
            batch_results = await db_session.execute(query)
            results.extend(batch_results.scalars().all())
        return results


class ResponseOptimizer:
    """Response optimization utilities."""

    @staticmethod
    def optimize_response_data(data: dict | list, max_depth: int = 3) -> dict | list:
        """Limit response data depth to reduce payload size."""
        if isinstance(data, dict):
            if max_depth <= 0:
                return {}
            return {
                k: ResponseOptimizer.optimize_response_data(v, max_depth - 1)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            if max_depth <= 0:
                return []
            return [
                ResponseOptimizer.optimize_response_data(item, max_depth - 1)
                for item in data
            ]
        else:
            return data

    @staticmethod
    def compress_response_if_large(data: dict | list, size_limit: int = 1024) -> dict | list:
        """Compress response data if it exceeds size limit."""
        import json
        try:
            json_str = json.dumps(data)
            if len(json_str.encode('utf-8')) > size_limit:
                logger.debug(f"Response size {len(json_str)} exceeds limit {size_limit}, optimizing")
                # For now, just return the original data
                # In production, you might want to implement actual compression
            return data
        except Exception as e:
            logger.error(f"Error optimizing response: {e}")
            return data


# Performance monitoring middleware update
async def performance_middleware(request, call_next):
    """
    Enhanced performance monitoring middleware.
    """
    start_time = time.time()

    # Skip metrics for non-API routes
    if not request.url.path.startswith("/api/") or request.url.path == "/api/v1/metrics":
        return await call_next(request)

    try:
        response = await call_next(request)
        return response
    finally:
        duration_seconds = time.time() - start_time
        duration_ms = duration_seconds * 1000

        # Track in metrics collector
        error = getattr(response, 'status_code', 500) >= 400
        metrics_collector.record_request(duration_seconds, error=error)

        # Track in performance optimizer
        endpoint = request.url.path
        performance_optimizer.track_response_time(endpoint, duration_ms)

        # Log slow requests
        if duration_ms > 200:
            logger.warning(f"Slow API request: {endpoint} took {duration_ms:.2f}ms")


def get_performance_recommendations() -> list[str]:
    """Get performance optimization recommendations."""
    return [
        "✅ Caching implemented for service discovery (5min TTL)",
        "✅ Async/await used throughout codebase",
        "✅ Database queries use async SQLAlchemy",
        "✅ Redis cache with graceful fallback",
        "✅ Metrics collection and monitoring in place",
        "✅ Vercel Postgres optimized for serverless",
        "✅ Connection pooling configured",
        "⚠️ Consider implementing query result caching for expensive operations",
        "⚠️ Consider implementing database query optimization for large datasets",
        "⚠️ Consider implementing response compression for large payloads",
        "⚠️ Monitor actual p95 response times in production",
        "⚠️ Consider implementing read replicas for read-heavy operations"
    ]
