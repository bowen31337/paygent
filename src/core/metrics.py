"""
Performance monitoring API endpoints and middleware.

Provides endpoints for retrieving performance metrics and
middleware for automatic metrics collection.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import settings
from src.core.monitoring import Timer, performance_monitor

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic performance monitoring of API requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and record performance metrics."""
        start_time = time.perf_counter()
        endpoint = request.url.path
        method = request.method

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics
            performance_monitor.record_api_call(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            return response

        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics for failed requests
            performance_monitor.record_api_call(
                endpoint=endpoint,
                method=method,
                status_code=500,
                duration_ms=duration_ms
            )

            logger.error(f"Request failed: {method} {endpoint} - {e}")
            raise


async def get_performance_metrics(request: Request) -> JSONResponse:
    """
    Get current performance metrics.

    Returns comprehensive performance data including:
    - API call statistics
    - Agent execution metrics
    - Cache performance
    - System health indicators
    - Response time percentiles
    """
    metrics = performance_monitor.get_performance_report()

    # Add environment information
    metrics["environment"] = {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
    }

    return JSONResponse(content=metrics)


async def get_api_performance(request: Request) -> JSONResponse:
    """
    Get API-specific performance metrics.

    Returns detailed API performance data including:
    - Response time statistics
    - Request counts by endpoint
    - Error rates
    - P95/P99 latencies
    """
    metrics = performance_monitor.registry.get_all_metrics()

    api_metrics = {
        "timestamp": time.time(),
        "summary": {},
        "endpoints": {},
        "status_codes": {},
        "response_times": {},
    }

    # Collect API call metrics
    for key, count in metrics["counters"].items():
        if key.startswith("api.calls"):
            # Parse the key to extract endpoint and status code
            if "{" in key and "}" in key:
                labels_part = key[key.find("{") + 1:key.find("}")]
                labels = {}
                for label in labels_part.split(","):
                    if "=" in label:
                        k, v = label.split("=", 1)
                        labels[k.strip()] = v.strip()

                endpoint = labels.get("endpoint", "unknown")
                status_code = labels.get("status_code", "unknown")
                method = labels.get("method", "unknown")

                # Build summary
                if "total" in key:
                    api_metrics["summary"][f"{method} {endpoint}"] = count

                # Build status code breakdown
                if status_code != "unknown":
                    if endpoint not in api_metrics["status_codes"]:
                        api_metrics["status_codes"][endpoint] = {}
                    api_metrics["status_codes"][endpoint][status_code] = count

    # Collect timing metrics
    for key, stats in metrics["timers"].items():
        if key.startswith("api.calls.duration"):
            # Parse the key to extract endpoint and method
            if "{" in key and "}" in key:
                labels_part = key[key.find("{") + 1:key.find("}")]
                labels = {}
                for label in labels_part.split(","):
                    if "=" in label:
                        k, v = label.split("=", 1)
                        labels[k.strip()] = v.strip()

                endpoint = labels.get("endpoint", "unknown")
                method = labels.get("method", "unknown")

                if endpoint not in api_metrics["endpoints"]:
                    api_metrics["endpoints"][endpoint] = {}

                api_metrics["endpoints"][endpoint][method] = {
                    "count": stats["count"],
                    "avg_ms": stats["average"],
                    "min_ms": stats["min"],
                    "max_ms": stats["max"],
                    "p95_ms": stats["p95"],
                    "p99_ms": stats["p99"],
                }

    return JSONResponse(content=api_metrics)


async def get_agent_performance(request: Request) -> JSONResponse:
    """
    Get agent-specific performance metrics.

    Returns detailed agent execution data including:
    - Execution times by command type
    - Success/failure rates
    - Command type distribution
    """
    metrics = performance_monitor.registry.get_all_metrics()

    agent_metrics = {
        "timestamp": time.time(),
        "summary": {},
        "command_types": {},
        "success_rates": {},
        "execution_times": {},
    }

    # Collect agent execution metrics
    for key, count in metrics["counters"].items():
        if key.startswith("agent.executions"):
            if "{" in key and "}" in key:
                labels_part = key[key.find("{") + 1:key.find("}")]
                labels = {}
                for label in labels_part.split(","):
                    if "=" in label:
                        k, v = label.split("=", 1)
                        labels[k.strip()] = v.strip()

                session_id = labels.get("session_id", "unknown")
                command_type = labels.get("command_type", "unknown")

                # Build summary
                if "total" in key:
                    agent_metrics["summary"][command_type] = agent_metrics["summary"].get(command_type, 0) + count

    # Collect timing metrics
    for key, stats in metrics["timers"].items():
        if key.startswith("agent.executions.duration") and "{" in key and "}" in key:
            labels_part = key[key.find("{") + 1:key.find("}")]
            labels = {}
            for label in labels_part.split(","):
                if "=" in label:
                    k, v = label.split("=", 1)
                    labels[k.strip()] = v.strip()

            command_type = labels.get("command_type", "unknown")
            session_id = labels.get("session_id", "unknown")

            if command_type not in agent_metrics["execution_times"]:
                agent_metrics["execution_times"][command_type] = {}

            agent_metrics["execution_times"][command_type][session_id] = {
                "count": stats["count"],
                "avg_ms": stats["average"],
                "min_ms": stats["min"],
                "max_ms": stats["max"],
                "p95_ms": stats["p95"],
                "p99_ms": stats["p99"],
            }

    return JSONResponse(content=agent_metrics)


async def get_health_check(request: Request) -> JSONResponse:
    """
    Get system health status.

    Returns health check information including:
    - Service status
    - Performance thresholds
    - Critical system metrics
    - Recent error rates
    """
    metrics = performance_monitor.registry.get_all_metrics()

    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {},
        "warnings": [],
        "critical_issues": [],
    }

    # Check API performance
    avg_response_time = 0
    error_rate = 0
    total_calls = 0
    total_errors = 0

    for key, count in metrics["counters"].items():
        if key.startswith("api.calls.total"):
            total_calls += count
        elif key.startswith("api.calls.error"):
            total_errors += count

    if total_calls > 0:
        error_rate = (total_errors / total_calls) * 100

    # Analyze timing metrics
    for key, stats in metrics["timers"].items():
        if key.startswith("api.calls.duration"):
            avg_response_time = stats["average"]
            break

    # Check thresholds
    if error_rate > 5.0:  # More than 5% error rate
        health["critical_issues"].append(f"High error rate: {error_rate:.2f}%")

    if avg_response_time > 1000:  # More than 1 second average
        health["warnings"].append(f"High response time: {avg_response_time:.2f}ms")

    # Check system resources
    cpu_usage = metrics["gauges"].get("system.cpu.percent", 0)
    memory_usage = metrics["gauges"].get("system.memory.percent", 0)

    if cpu_usage > 80:
        health["warnings"].append(f"High CPU usage: {cpu_usage:.2f}%")

    if memory_usage > 80:
        health["warnings"].append(f"High memory usage: {memory_usage:.2f}%")

    # Determine overall status
    if health["critical_issues"]:
        health["status"] = "critical"
    elif health["warnings"]:
        health["status"] = "warning"

    health["checks"] = {
        "api_response_time_ms": avg_response_time,
        "api_error_rate_percent": error_rate,
        "cpu_usage_percent": cpu_usage,
        "memory_usage_percent": memory_usage,
        "total_api_calls": total_calls,
        "total_errors": total_errors,
    }

    return JSONResponse(content=health)


async def get_cache_performance(request: Request) -> JSONResponse:
    """
    Get cache performance metrics.

    Returns cache-specific performance data including:
    - Hit/miss rates
    - Cache operation times
    - Cache type performance
    """
    metrics = performance_monitor.registry.get_all_metrics()

    cache_metrics = {
        "timestamp": time.time(),
        "summary": {},
        "cache_types": {},
        "operations": {},
    }

    # Collect cache metrics
    cache_hits = 0
    cache_misses = 0

    for key, count in metrics["counters"].items():
        if key.startswith("cache.operations"):
            if "hit" in key:
                cache_hits += count
            elif "miss" in key:
                cache_misses += count

    total_cache_ops = cache_hits + cache_misses
    hit_rate = (cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0

    cache_metrics["summary"] = {
        "total_operations": total_cache_ops,
        "hits": cache_hits,
        "misses": cache_misses,
        "hit_rate_percent": round(hit_rate, 2),
    }

    # Collect timing metrics
    for key, stats in metrics["timers"].items():
        if key.startswith("cache.operations.duration") and "{" in key and "}" in key:
            labels_part = key[key.find("{") + 1:key.find("}")]
            labels = {}
            for label in labels_part.split(","):
                if "=" in label:
                    k, v = label.split("=", 1)
                    labels[k.strip()] = v.strip()

            operation = labels.get("operation", "unknown")
            cache_type = labels.get("cache_type", "unknown")

            if cache_type not in cache_metrics["cache_types"]:
                cache_metrics["cache_types"][cache_type] = {}

            cache_metrics["cache_types"][cache_type][operation] = {
                "count": stats["count"],
                "avg_ms": stats["average"],
                "min_ms": stats["min"],
                "max_ms": stats["max"],
                "p95_ms": stats["p95"],
                "p99_ms": stats["p99"],
            }

    return JSONResponse(content=cache_metrics)


# Timer utility function for manual timing
def time_operation(operation_name: str, labels: dict | None = None) -> Timer:
    """
    Create a timer for manual operation timing.

    Usage:
        with time_operation("database_query", {"table": "users"}):
            # Your operation here
            pass
    """
    return Timer(performance_monitor.registry, operation_name, labels)


# Performance decorator for functions
def track_performance(operation_name: str | None = None):
    """
    Decorator to automatically track function performance.

    Usage:
        @track_performance("api_call")
        async def my_function():
            pass
    """
    def decorator(func):  # noqa: D417
        """Wrap a function with performance tracking.

        Args:
            func: Async function to track

        Returns:
            Callable: Tracked function wrapper
        """
        async def wrapper(*args, **kwargs):  # noqa: D417
            """Execute function with performance tracking.

            Args:
                *args: Function arguments
                **kwargs: Function keyword arguments

            Returns:
                Any: Function result
            """
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            with time_operation(op_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
