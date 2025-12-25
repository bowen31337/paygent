"""
Simplified Paygent Main Application.

This module provides a simplified FastAPI application that works without
pydantic dependencies, allowing basic functionality when pydantic_core has issues.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from src.core.simple_config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """
    Application lifespan handler for startup and shutdown events.

    Args:
        app: The FastAPI application instance

    Yields:
        None: Control back to FastAPI after startup
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
## AI-Powered Multi-Agent Payment Orchestration Platform

Simplified version - basic functionality without pydantic dependencies.

**Note**: This is a simplified version for when pydantic dependencies fail.
Some advanced features may not be available.
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    response_description="Application health status",
)
async def health_check() -> dict[str, Any]:
    """
    Check application health status.

    Returns basic health information including version and environment.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "note": "Simplified mode - pydantic dependencies not available",
    }


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API root",
    include_in_schema=False,
)
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "mode": "simplified",
        "note": "pydantic dependencies not available",
    }


# Settings endpoint for debugging
@app.get(
    "/settings",
    tags=["Settings"],
    summary="Get application settings",
    response_description="Current application settings",
)
async def get_settings() -> dict[str, Any]:
    """
    Get current application settings.

    Returns current configuration values for debugging purposes.
    """
    return settings.to_dict()


# Validation endpoint
@app.get(
    "/validate",
    tags=["Settings"],
    summary="Validate configuration",
    response_description="Configuration validation results",
)
async def validate_config() -> dict[str, Any]:
    """
    Validate application configuration.

    Returns any configuration issues that need to be addressed.
    """
    issues = settings.validate()
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "settings": settings.to_dict(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main_simple:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )