"""
HTTPS enforcement tests (Feature 3).

Tests that HTTPS is enforced in production environments.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.responses import RedirectResponse

from src.core.config import settings
from src.middleware.https_enforcement import https_enforcement_middleware, is_secure_request


class TestHTTPSEnforcement:
    """Test HTTPS enforcement middleware (Feature 3)."""

    @pytest.mark.asyncio
    async def test_http_request_in_production_redirects_to_https(self):
        """
        Feature 3: HTTPS is enforced for all endpoints.

        Test that HTTP requests in production are redirected to HTTPS.
        """
        # Create a mock request with X-Forwarded-Proto=http
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-Proto": "http"}
        request.url = Mock()
        request.url.scheme = "http"

        # Mock the URL replacement that happens during redirect
        new_url = Mock()
        new_url.unicode_string = Mock(return_value="https://example.com/api")
        request.url.replace = Mock(return_value=new_url)

        # Mock call_next
        async def call_next(req):
            from fastapi import Response
            return Response(content="OK")

        # Temporarily set production mode by mocking environment
        with patch.object(settings, 'environment', 'production'):
            response = await https_enforcement_middleware(request, call_next)

        # Should redirect to HTTPS
        assert isinstance(response, RedirectResponse), "Should return RedirectResponse"
        assert response.status_code == 301, "Should use 301 permanent redirect"

    @pytest.mark.asyncio
    async def test_https_request_in_production_succeeds(self):
        """
        Test that HTTPS requests in production succeed.
        """
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-Proto": "https"}

        # Create a mock response object
        mock_response = Mock()
        mock_response.headers = {}

        async def call_next(req):
            return mock_response

        with patch.object(settings, 'environment', 'production'):
            response = await https_enforcement_middleware(request, call_next)

        # Should succeed with security headers
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains; preload"

    @pytest.mark.asyncio
    async def test_development_mode_allows_http(self):
        """
        Test that development mode allows HTTP.
        """
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-Proto": "http"}

        # Create a mock response
        mock_response = Mock()
        mock_response.headers = {}

        async def call_next(req):
            return mock_response

        with patch.object(settings, 'environment', 'development'):
            response = await https_enforcement_middleware(request, call_next)

        # Should not redirect in development
        assert not isinstance(response, RedirectResponse)

    def test_is_secure_request_in_production(self):
        """Test that is_secure_request correctly identifies secure requests."""
        request = Mock(spec=Request)
        request.headers = {}
        request.url = Mock()
        request.url.scheme = "https"

        with patch.object(settings, 'environment', 'production'):
            assert is_secure_request(request) is True

        request.url.scheme = "http"
        request.headers = {}

        with patch.object(settings, 'environment', 'production'):
            assert is_secure_request(request) is False

    def test_is_secure_request_in_development(self):
        """Test that is_secure_request allows HTTP in development."""
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-Proto": "http"}
        request.url = Mock()
        request.url.scheme = "http"

        with patch.object(settings, 'environment', 'development'):
            assert is_secure_request(request) is True, "Should allow HTTP in development"
