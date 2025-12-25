"""Unit tests for metrics middleware."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.middleware.metrics import metrics_middleware


class TestMetricsMiddleware:
    @pytest.mark.asyncio
    async def test_skips_non_api_routes(self):
        mock_request = MagicMock()
        mock_request.url.path = "/health"
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await metrics_middleware(mock_request, mock_call_next)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_skips_metrics_endpoint(self):
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/metrics"
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await metrics_middleware(mock_request, mock_call_next)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_tracks_metrics_for_api_routes(self):
        with patch("src.middleware.metrics.metrics_collector") as mock_collector:
            mock_request = MagicMock()
            mock_request.url.path = "/api/v1/execute"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_call_next = AsyncMock(return_value=mock_response)

            response = await metrics_middleware(mock_request, mock_call_next)
            assert response == mock_response
            mock_collector.record_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_tracks_error_metrics(self):
        with patch("src.middleware.metrics.metrics_collector") as mock_collector:
            mock_request = MagicMock()
            mock_request.url.path = "/api/v1/execute"
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_call_next = AsyncMock(return_value=mock_response)

            await metrics_middleware(mock_request, mock_call_next)
            call_args = mock_collector.record_request.call_args
            assert call_args[1]["error"] is True

    @pytest.mark.asyncio
    async def test_tracks_exception_metrics(self):
        with patch("src.middleware.metrics.metrics_collector") as mock_collector:
            mock_request = MagicMock()
            mock_request.url.path = "/api/v1/execute"
            mock_call_next = AsyncMock(side_effect=ValueError("Test error"))

            with pytest.raises(ValueError):
                await metrics_middleware(mock_request, mock_call_next)

            call_args = mock_collector.record_request.call_args
            assert call_args[1]["error"] is True

    @pytest.mark.asyncio
    async def test_timing_accuracy(self):
        with patch("src.middleware.metrics.metrics_collector") as mock_collector:
            mock_request = MagicMock()
            mock_request.url.path = "/api/v1/execute"

            async def slow_call_next(req):
                await asyncio.sleep(0.01)
                mock_response = MagicMock()
                mock_response.status_code = 200
                return mock_response

            await metrics_middleware(mock_request, slow_call_next)
            call_args = mock_collector.record_request.call_args
            duration = call_args[0][0]
            assert duration >= 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
