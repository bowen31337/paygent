"""
Paygent - AI-Powered Multi-Agent Payment Orchestration Platform

Main FastAPI application entry point with OpenAPI documentation.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import init_db, close_db
from src.core.vercel_db import close_db as close_vercel_db
from src.core.cache import init_cache, close_cache
from src.core.errors import (
    http_exception_handler,
    general_exception_handler,
)
from src.api import router as api_router
from src.middleware.metrics import metrics_middleware
from src.middleware.rate_limiter import rate_limit_middleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠ Database initialization failed: {e}")

    # Initialize Redis cache
    logger.info("Initializing Redis cache...")
    try:
        await init_cache()
        logger.info("✓ Redis cache initialized successfully")
    except Exception as e:
        logger.warning(f"⚠ Redis cache initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    await close_vercel_db()
    await close_cache()
    logger.info("All connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
## AI-Powered Multi-Agent Payment Orchestration Platform

Paygent enables autonomous AI agents to discover, negotiate, and execute payments
seamlessly across the Cronos ecosystem using the x402 protocol.

### Key Features

- **Natural Language Commands**: Execute payments using plain English
- **x402 Payment Protocol**: Automatic HTTP 402 payment handling with EIP-712 signatures
- **Service Discovery**: MCP-compatible service registry and marketplace
- **DeFi Integration**: VVS Finance, Moonlander, and Delphi protocol support
- **Human-in-the-Loop**: Configurable approval workflows for sensitive operations
- **Non-Custodial**: Users maintain control of their wallets

### Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your-token>
```

### Rate Limiting

API requests are rate-limited to prevent abuse. Default: 100 requests/minute.
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.middleware("http")(metrics_middleware)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)


# Global exception handlers
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)


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
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")


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
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
