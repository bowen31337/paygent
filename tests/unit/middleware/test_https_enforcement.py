"""Unit tests for HTTPS enforcement middleware."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.middleware.https_enforcement import https_enforcement_middleware, is_secure_request
from fastapi import HTTPException
from fastapi.responses import RedirectResponse


class TestHTTPSEnforcementMiddleware:
    @pytest.mark.asyncio
    async def test_skips_in_development(self):
        with patch("src.middleware.https_enforcement.settings") as mock_settings:
            mock_settings.is_production = False
            mock_request = MagicMock()
            mock_response = MagicMock()
            mock_call_next = AsyncMock(return_value=mock_response)

            response = await https_enforcement_middleware(mock_request, mock_call_next)
            assert response == mock_response

    @pytest.mark.asyncio
    async def test_redirects_http_to_https_in_production(self):
        with patch("src.middleware.https_enforcement.settings") as mock_settings:
            mock_settings.is_production = True
            mock_request = MagicMock()
            mock_request.headers = {"X-Forwarded-Proto": "http"}
            mock_request.url.replace.return_value = MagicMock(
                unicode_string=lambda: "https://example.com/api/test"
            )
            mock_call_next = AsyncMock()

            response = await https_enforcement_middleware(mock_request, mock_call_next)
            assert isinstance(response, RedirectResponse)
            assert response.status_code == 301

    @pytest.mark.asyncio
    async def test_adds_security_headers(self):
        with patch("src.middleware.https_enforcement.settings") as mock_settings:
            mock_settings.is_production = True
            mock_request = MagicMock()
            mock_request.headers = {"X-Forwarded-Proto": "https"}
            mock_request.url.path = "/api/test"
            mock_response = MagicMock()
            mock_response.headers = {}
            mock_call_next = AsyncMock(return_value=mock_response)

            response = await https_enforcement_middleware(mock_request, mock_call_next)
            assert "Strict-Transport-Security" in response.headers

    @pytest.mark.asyncio
    async def test_rejects_invalid_protocol(self):
        with patch("src.middleware.https_enforcement.settings") as mock_settings:
            mock_settings.is_production = True
            mock_request = MagicMock()
            mock_request.headers = {"X-Forwarded-Proto": "invalid"}
            mock_request.url.path = "/api/test"
            mock_call_next = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await https_enforcement_middleware(mock_request, mock_call_next)
            assert exc_info.value.status_code == 403


class TestIsSecureRequest:
    def test_allows_http_in_development(self):
        with patch("src.middleware.https_enforcement.settings") as mock_settings:
            mock_settings.is_production = False
            mock_request = MagicMock()
            mock_request.headers = {"X-Forwarded-Proto": "http"}
            assert is_secure_request(mock_request) is True

    def test_accepts_forwarded_https(self):
        with patch("src.middleware.https_enforcement.settings") as mock_settings:
            mock_settings.is_production = True
            mock_request = MagicMock()
            mock_request.headers = {"X-Forwarded-Proto": "https"}
            assert is_secure_request(mock_request) is True

    def test_rejects_http_in_production(self):
        with patch("src.middleware.https_enforcement.settings") as mock_settings:
            mock_settings.is_production = True
            mock_request = MagicMock()
            mock_request.headers = {"X-Forwarded-Proto": "http"}
            mock_request.url.scheme = "http"
            assert is_secure_request(mock_request) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
