"""
Unit tests for OpenAPI documentation endpoints.

Tests /docs, /redoc, and /openapi.json endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


class TestOpenAPI:
    """Test OpenAPI documentation endpoints."""

    @pytest.mark.asyncio
    async def test_openapi_json_returns_200(self):
        """Test that /openapi.json returns 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/openapi.json")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json_is_valid_json(self):
        """Test that /openapi.json returns valid JSON."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/openapi.json")
            data = response.json()

            assert "openapi" in data
            assert "info" in data
            assert "paths" in data
            assert "components" in data

    @pytest.mark.asyncio
    async def test_openapi_has_correct_info(self):
        """Test that OpenAPI spec has correct metadata."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/openapi.json")
            data = response.json()

            assert data["info"]["title"] == "Paygent"
            assert data["info"]["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_openapi_has_health_endpoint(self):
        """Test that OpenAPI spec includes health endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/openapi.json")
            data = response.json()

            assert "/health" in data["paths"]

    @pytest.mark.asyncio
    async def test_openapi_has_api_v1_endpoints(self):
        """Test that OpenAPI spec includes API v1 endpoints."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/openapi.json")
            data = response.json()

            # Check for key API endpoints
            assert "/api/v1/agent/execute" in data["paths"]
            assert "/api/v1/services/discover" in data["paths"]
            assert "/api/v1/payments/history" in data["paths"]

    @pytest.mark.asyncio
    async def test_swagger_docs_returns_200(self):
        """Test that /docs returns 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/docs")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_swagger_docs_contains_swagger_ui(self):
        """Test that /docs contains Swagger UI HTML."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/docs")
            content = response.text

            assert "swagger" in content.lower()

    @pytest.mark.asyncio
    async def test_redoc_returns_200(self):
        """Test that /redoc returns 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/redoc")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_contains_redoc_ui(self):
        """Test that /redoc contains ReDoc UI HTML."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/redoc")
            content = response.text

            assert "redoc" in content.lower()

    @pytest.mark.asyncio
    async def test_root_endpoint_returns_api_info(self):
        """Test that root endpoint returns API information."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/")
            data = response.json()

            assert data["name"] == "Paygent"
            assert data["version"] == "0.1.0"
            assert data["docs"] == "/docs"
            assert data["redoc"] == "/redoc"
            assert data["openapi"] == "/openapi.json"
