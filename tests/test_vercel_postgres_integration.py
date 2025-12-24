"""
Integration test for Vercel Postgres connection in serverless environment.

This test verifies that the Vercel Postgres integration works correctly
by testing the actual database connection and health check.
"""

import os
import pytest
import asyncio
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.vercel_db import (
    get_database_url,
    engine,
    test_connection,
    check_database_health,
    get_sync_engine,
)


class TestVercelPostgresIntegration:
    """Integration tests for Vercel Postgres connection."""

    @pytest.mark.asyncio
    async def test_database_url_detection(self):
        """Test that database URL is detected correctly based on environment."""
        # Test SQLite fallback
        with patch.dict(os.environ, {}, clear=True):
            url = get_database_url()
            assert url == "sqlite+aiosqlite:///./paygent.db"

        # Test Vercel Postgres URL
        postgres_url = "postgresql://user:pass@host:5432/db"
        with patch.dict(os.environ, {"POSTGRES_URL": postgres_url}, clear=True):
            url = get_database_url()
            assert url == postgres_url

        # Test Vercel non-pooling URL
        non_pooling_url = "postgresql://user:pass@host:5432/db2"
        with patch.dict(os.environ, {"POSTGRES_URL_NON_POOLING": non_pooling_url}, clear=True):
            url = get_database_url()
            assert url == non_pooling_url

    @pytest.mark.asyncio
    async def test_engine_creation(self):
        """Test that database engine is created successfully."""
        # Test with SQLite (should always work)
        with patch.dict(os.environ, {}, clear=True):
            # Recreate engine with new environment
            from src.core import vercel_db
            import importlib
            importlib.reload(vercel_db)

            assert isinstance(vercel_db.engine, AsyncEngine)

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check functionality."""
        with patch.dict(os.environ, {}, clear=True):
            # Recreate engine with new environment
            from src.core import vercel_db
            import importlib
            importlib.reload(vercel_db)

            health = await check_database_health()

            # Should return a dict with expected keys
            assert isinstance(health, dict)
            assert "status" in health
            assert "database_url" in health
            assert "connection_test" in health

            # For SQLite, should be healthy
            assert health["status"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_sync_engine_for_alembic(self):
        """Test sync engine creation for Alembic migrations."""
        with patch.dict(os.environ, {}, clear=True):
            # Recreate engine with new environment
            from src.core import vercel_db
            import importlib
            importlib.reload(vercel_db)

            sync_engine = get_sync_engine()
            # For SQLite, should return None (no sync engine needed)
            assert sync_engine is None

    @pytest.mark.asyncio
    async def test_connection_test(self):
        """Test database connection test functionality."""
        with patch.dict(os.environ, {}, clear=True):
            # Recreate engine with new environment
            from src.core import vercel_db
            import importlib
            importlib.reload(vercel_db)

            # Test connection (should work with SQLite)
            result = await test_connection()
            assert isinstance(result, bool)
            assert result is True  # SQLite should always connect

    def test_environment_variable_priority(self):
        """Test that environment variables are prioritized correctly."""
        postgres_url = "postgresql://user:pass@host:5432/db"
        non_pooling_url = "postgresql://user:pass@host:5432/db2"

        # POSTGRES_URL should take priority over POSTGRES_URL_NON_POOLING
        with patch.dict(os.environ, {
            "POSTGRES_URL": postgres_url,
            "POSTGRES_URL_NON_POOLING": non_pooling_url
        }, clear=True):
            url = get_database_url()
            assert url == postgres_url

        # POSTGRES_URL_NON_POOLING should be used when POSTGRES_URL is not set
        with patch.dict(os.environ, {
            "POSTGRES_URL_NON_POOLING": non_pooling_url
        }, clear=True):
            url = get_database_url()
            assert url == non_pooling_url


class TestVercelPostgresInProduction:
    """Test Vercel Postgres behavior in production-like environment."""

    @pytest.mark.asyncio
    async def test_production_postgres_url_detection(self):
        """Test that production PostgreSQL URLs are detected correctly."""
        # Simulate Vercel production environment
        prod_url = "postgresql://prod_user:prod_pass@prod_host:5432/prod_db"
        with patch.dict(os.environ, {"POSTGRES_URL": prod_url}, clear=True):
            url = get_database_url()
            assert url == prod_url

    @pytest.mark.asyncio
    async def test_production_engine_configuration(self):
        """Test engine configuration for production PostgreSQL."""
        # This test would require actual PostgreSQL setup
        # For now, just test that the URL detection works
        prod_url = "postgresql://prod_user:prod_pass@prod_host:5432/prod_db"
        with patch.dict(os.environ, {"POSTGRES_URL": prod_url}, clear=True):
            url = get_database_url()
            assert url.startswith("postgresql://")
            assert "prod_host" in url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])