"""
Unit tests for health check endpoint.

Tests the /health endpoint to verify it returns correct status.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self):
        """Test that health check returns 200 status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_returns_correct_structure(self):
        """Test that health check returns expected JSON structure."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            data = response.json()

            assert "status" in data
            assert "version" in data
            assert "environment" in data

    @pytest.mark.asyncio
    async def test_health_check_status_is_healthy(self):
        """Test that health check reports healthy status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            data = response.json()

            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_includes_version(self):
        """Test that health check includes version information."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            data = response.json()

            assert data["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_health_check_includes_environment(self):
        """Test that health check includes environment information."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            data = response.json()

            assert "environment" in data
            assert data["environment"] in ["development", "production", "testing"]
