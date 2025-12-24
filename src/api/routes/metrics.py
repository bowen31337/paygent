"""
Prometheus metrics API routes.

This module provides a Prometheus-compatible metrics endpoint
for monitoring and observability.
"""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from src.services.metrics_service import metrics_collector

router = APIRouter()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics endpoint",
    description="Exposes application metrics in Prometheus text format for monitoring.",
    include_in_schema=True,
)
async def get_metrics() -> Response:
    """
    Get Prometheus-formatted metrics.

    This endpoint exposes application metrics in the Prometheus text format,
    suitable for scraping by a Prometheus server or other monitoring tools.

    Metrics include:
    - Request counts and durations
    - Agent execution statistics
    - Payment metrics
    - Approval workflow metrics
    - WebSocket connection metrics
    - Session metrics
    - Cache performance metrics
    """
    metrics_text = metrics_collector.get_prometheus_metrics()
    return PlainTextResponse(metrics_text)
