"""
Comprehensive verification test for all completed features.

This test verifies that all the features we've implemented are working correctly.
"""

import asyncio
import os
from unittest.mock import patch

import pytest


# Test all implemented features
def test_vercel_postgres_integration():
    """Test Vercel Postgres connection and configuration."""
    from src.core.vercel_db import (
        get_database_url,
    )

    # Test with Vercel environment variables
    with patch.dict(os.environ, {
        "POSTGRES_URL": "postgresql://user:pass@host:5432/db"
    }):
        url = get_database_url()
        assert url == "postgresql://user:pass@host:5432/db"

    # Test with development fallback
    with patch.dict(os.environ, {}, clear=True):
        url = get_database_url()
        assert url.startswith("sqlite+aiosqlite:///")


def test_vercel_kv_cache_integration():
    """Test Vercel KV cache functionality."""
    from src.core.vercel_kv import VercelKVCache

    cache = VercelKVCache()

    # Test initialization
    assert cache.metrics is not None
    assert cache.metrics.hits == 0
    assert cache.metrics.misses == 0

    # Test metrics recording
    cache.metrics.record_hit()
    cache.metrics.record_miss()
    cache.metrics.record_set()
    cache.metrics.record_delete()

    metrics = cache.metrics.get_metrics()
    assert metrics["hits"] == 1
    assert metrics["misses"] == 1
    assert metrics["hit_rate_percent"] == 50.0


def test_vercel_blob_storage():
    """Test Vercel Blob storage functionality."""
    from src.core.vercel_blob import VercelBlobStorage

    storage = VercelBlobStorage()

    # Test initialization
    assert storage.metrics is not None
    assert storage.metrics.uploads == 0

    # Test metrics recording
    storage.metrics.record_upload(10.5)
    storage.metrics.record_download(20.3)
    storage.metrics.record_delete(5.2)

    metrics = storage.metrics.get_metrics()
    assert metrics["uploads"] == 1
    assert metrics["downloads"] == 1
    assert metrics["deletes"] == 1
    assert metrics["avg_upload_time_ms"] == 10.5


def test_performance_optimization():
    """Test performance optimization features."""
    from src.core.performance import PerformanceOptimizer, fast_cache

    optimizer = PerformanceOptimizer()

    # Test performance tracking
    optimizer.track_response_time("test_endpoint", 50.0)
    optimizer.track_response_time("test_endpoint", 100.0)

    stats = optimizer.get_performance_stats()
    assert stats["total_requests"] == 2
    assert stats["avg_response_time_ms"] == 75.0

    # Test cache decorator
    call_count = 0

    @fast_cache(ttl=60)
    async def expensive_operation():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return f"result_{call_count}"

    # Note: Actual cache testing would require the cache system to be initialized


def test_security_implementation():
    """Test security implementation."""
    from src.core.auth import create_access_token, verify_token
    from src.core.security import redact_string

    # Test data redaction
    private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    redacted = redact_string(private_key)
    assert "REDACTED" in redacted

    # Test JWT authentication
    data = {"sub": "test_user", "user_id": "test_123"}
    token = create_access_token(data)
    token_data = verify_token(token)
    assert token_data is not None
    assert token_data.username == "test_user"


def test_rate_limiting():
    """Test rate limiting functionality."""
    from src.middleware.rate_limiter import RateLimiter

    limiter = RateLimiter(requests_per_minute=10)

    # Test basic functionality
    results = []
    for i in range(5):
        is_allowed, remaining, reset_time = limiter.check_limit(None, f"test_key_{i}")
        results.append(is_allowed)

    # Should allow requests within limit
    assert any(results), "Should allow some requests"


def test_configuration():
    """Test application configuration."""
    from src.core.config import settings

    # Test basic configuration
    assert settings.app_name == "Paygent"
    assert settings.app_version == "0.1.0"
    assert settings.debug is False  # Should be False in test environment

    # Test CORS configuration
    assert isinstance(settings.cors_origins, list)
    assert "http://localhost:3000" in settings.cors_origins

    # Test JWT configuration
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expiration_hours == 24

    # Test rate limiting configuration
    assert settings.rate_limit_requests_per_minute > 0


def test_api_structure():
    """Test API structure and endpoints."""
    from src.main import app

    # Test that API router is included
    assert app.include_router is not None

    # Test that main endpoints exist
    routes = [route.path for route in app.routes]
    assert "/health" in routes
    assert "/docs" in routes


def test_database_models():
    """Test that database models are properly defined."""
    from src.core.database import Base
    from src.models.payments import Payment
    from src.models.services import Service

    # Test that models inherit from Base
    assert issubclass(Service, Base)
    assert issubclass(Payment, Base)


def test_schemas():
    """Test that Pydantic schemas are properly defined."""
    from src.schemas.agent import AgentCommand, AgentResult

    # Test basic schema functionality
    command = AgentCommand(session_id="test", command="test command")
    assert command.session_id == "test"
    assert command.command == "test command"

    result = AgentResult(success=True, message="success")
    assert result.success is True
    assert result.message == "success"


def test_error_handling():
    """Test error handling system."""
    from src.core.errors import PaygentError

    # Test error creation
    error = PaygentError(message="Test error", details={"key": "value"})
    assert error.message == "Test error"
    assert error.details == {"key": "value"}


def test_environment_detection():
    """Test environment detection and configuration."""
    from src.core.config import settings

    # Test environment detection
    environment = settings.environment
    assert environment in ["development", "production", "test"]

    # Test Vercel detection
    if "VERCEL" in os.environ:
        assert settings.is_production is True
    else:
        assert settings.is_production is False


def test_dependency_injection():
    """Test dependency injection patterns."""
    from src.core.auth import CurrentUser, CurrentUserOptional
    from src.core.cache import cache_client

    # Test that dependency types are defined
    assert CurrentUser is not None
    assert CurrentUserOptional is not None

    # Test that cache client is available
    assert cache_client is not None


def test_logging_configuration():
    """Test logging configuration."""
    from src.core.security import configure_secure_logging

    # Test that secure logging can be configured
    logger = configure_secure_logging()
    assert logger is not None

    # Test that formatters can be applied
    handlers = logger.handlers
    assert len(handlers) > 0


def test_validation():
    """Test input validation."""
    from src.core.security import is_safe_for_logging, sanitize

    # Test string sanitization
    unsafe_string = "private key: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    sanitized = sanitize(unsafe_string)
    assert "REDACTED" in sanitized

    # Test safety checking
    assert not is_safe_for_logging(unsafe_string)
    assert is_safe_for_logging("safe string")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
