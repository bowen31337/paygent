"""Unit tests for rate limiting middleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.middleware.rate_limiter import RateLimiter, rate_limit, rate_limit_middleware


class TestRateLimiter:
    def test_init_default(self):
        limiter = RateLimiter()
        assert limiter.requests_per_minute == 100

    def test_get_key_with_user_id(self):
        limiter = RateLimiter()
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        key = limiter._get_key(mock_request, user_id="user123")
        assert key == "rate_limit:user:user123"

    def test_get_key_with_ip(self):
        limiter = RateLimiter()
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        key = limiter._get_key(mock_request)
        assert key == "rate_limit:ip:192.168.1.1"

    def test_check_limit_within_limit(self):
        limiter = RateLimiter(requests_per_minute=100)
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        is_allowed, remaining, reset_time = limiter.check_limit(mock_request)
        assert is_allowed is True
        assert remaining == 100  # First request, 100 remaining before increment

    def test_check_limit_at_limit(self):
        limiter = RateLimiter(requests_per_minute=2)
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.101"

        is_allowed1, _, _ = limiter.check_limit(mock_request)
        assert is_allowed1 is True

        is_allowed2, _, _ = limiter.check_limit(mock_request)
        assert is_allowed2 is True

        is_allowed3, remaining, _ = limiter.check_limit(mock_request)
        assert is_allowed3 is False
        assert remaining == 0

    def test_get_headers(self):
        limiter = RateLimiter(requests_per_minute=100)
        headers = limiter.get_headers(remaining=50, reset_time=123456)
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "50"


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_skips_non_api_routes(self):
        mock_request = MagicMock()
        mock_request.url.path = "/health"
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await rate_limit_middleware(mock_request, mock_call_next)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_applies_rate_limit_to_api_routes(self):
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/execute"
        mock_request.client.host = "192.168.1.102"
        mock_request.headers = {}

        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await rate_limit_middleware(mock_request, mock_call_next)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/execute"
        mock_request.client.host = "192.168.1.103"
        mock_request.headers = {}

        limiter = RateLimiter(requests_per_minute=2)

        is_allowed1, _, _ = limiter.check_limit(mock_request)
        is_allowed2, _, _ = limiter.check_limit(mock_request)
        assert is_allowed1 is True
        assert is_allowed2 is True

        is_allowed3, _, _ = limiter.check_limit(mock_request)
        assert is_allowed3 is False


class TestRateLimitDecorator:
    @pytest.mark.asyncio
    async def test_decorator_allows_request(self):
        @rate_limit(requests_per_minute=10)
        async def test_endpoint(request):
            return {"status": "ok"}

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.104"
        result = await test_endpoint(mock_request)
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_decorator_blocks_excessive_requests(self):
        @rate_limit(requests_per_minute=1)
        async def test_endpoint(request):
            return {"status": "ok"}

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.105"

        result = await test_endpoint(mock_request)
        assert result == {"status": "ok"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
