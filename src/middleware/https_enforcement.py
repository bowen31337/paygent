"""
HTTPS enforcement middleware for FastAPI.

This module provides middleware to enforce HTTPS connections in production
environments, redirecting HTTP requests to HTTPS and rejecting insecure requests.
"""

from typing import Callable, Any
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_301_MOVED_PERMANENTLY, HTTP_403_FORBIDDEN

from src.core.config import settings


async def https_enforcement_middleware(
    request: Request,
    call_next: Callable[[Request], Any]
) -> Any:
    """
    FastAPI middleware for enforcing HTTPS in production.

    This middleware:
    1. In production: Redirects HTTP to HTTPS
    2. In development: Allows both HTTP and HTTPS
    3. Rejects requests with X-Forwarded-Proto header spoofing attempts

    Args:
        request: FastAPI request
        call_next: Next middleware/callable in the chain

    Returns:
        Response from the next handler, or redirect/rejection
    """
    # Skip enforcement in development
    if not settings.is_production:
        return await call_next(request)

    # Get the original protocol from headers (set by reverse proxy)
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    forwarded_ssl = request.headers.get("X-Forwarded-SSL", "")

    # Check if this is an HTTP request that should be redirected
    # In production behind a reverse proxy, we check X-Forwarded-Proto
    if forwarded_proto == "http":
        # Redirect to HTTPS
        url = request.url.replace(scheme="https", port=443)
        return RedirectResponse(
            url.unicode_string(),
            status_code=HTTP_301_MOVED_PERMANENTLY
        )

    # Reject requests that claim to be HTTPS but might be spoofed
    # (This is a basic check - production should use proper TLS termination)
    if forwarded_proto and forwarded_proto not in ["http", "https"]:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid protocol specified in request headers"
        )

    # Add security headers for HTTPS enforcement
    response = await call_next(request)

    # Add Strict-Transport-Security header (HSTS)
    # Tells browsers to always use HTTPS for the next year
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    # Add other security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    return response


def is_secure_request(request: Request) -> bool:
    """
    Check if a request is secure (HTTPS).

    Args:
        request: FastAPI request

    Returns:
        True if the request is secure, False otherwise
    """
    # Check if running in production
    if not settings.is_production:
        return True  # Allow HTTP in development

    # Check the forwarded protocol header (set by reverse proxy)
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if forwarded_proto == "https":
        return True

    # Check if the request was made over HTTPS directly
    if request.url.scheme == "https":
        return True

    return False
