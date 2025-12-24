"""
Metrics middleware for FastAPI.

This module provides middleware to track application metrics
for Prometheus monitoring.
"""

import time
from typing import Callable, Any

from fastapi import Request

from src.services.metrics_service import metrics_collector


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Any]
) -> Any:
    """
    FastAPI middleware for tracking request metrics.

    This middleware tracks:
    - Request counts
    - Request durations
    - Request errors

    Args:
        request: FastAPI request
        call_next: Next middleware/callable in the chain

    Returns:
        Response from the next handler
    """
    # Skip metrics for non-API routes and metrics endpoint itself
    if not request.url.path.startswith("/api/") or request.url.path == "/api/v1/metrics":
        return await call_next(request)

    # Start timing
    start_time = time.time()

    # Process request
    try:
        response = await call_next(request)
        duration_seconds = time.time() - start_time

        # Record metrics
        error = response.status_code >= 400
        metrics_collector.record_request(duration_seconds, error=error)

        return response

    except Exception:
        # Record error metrics
        duration_seconds = time.time() - start_time
        metrics_collector.record_request(duration_seconds, error=True)
        raise
