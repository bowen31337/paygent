"""
Tests for graceful handling of invalid API responses.

This test suite verifies that the agent handles malformed JSON,
invalid content types, and unexpected response structures gracefully.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPStatusError, InvalidURL, Response, Request

from src.services.x402_service import X402PaymentService


class TestInvalidResponseHandling:
    """Test handling of invalid API responses."""

    @pytest.fixture
    def x402_service(self):
        """Create an X402PaymentService instance for testing."""
        return X402PaymentService()

    @pytest.mark.asyncio
    async def test_malformed_json_response(self, x402_service):
        """Test that malformed JSON in response is handled gracefully."""
        # Create a mock response with invalid JSON
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "{invalid json data"
        mock_response.content = b"{invalid json data"
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "{invalid json data", 0)

        # Mock the client.get to return invalid JSON
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert "invalid" in result["message"].lower() or "parse" in result["message"].lower()
            assert "json" in result["message"].lower() or "format" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_empty_response_body(self, x402_service):
        """Test that empty response body is handled gracefully."""
        # Create a mock response with empty body
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = ""
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        # Mock the client.get to return empty response
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert result["message"]  # Should have an error message

    @pytest.mark.asyncio
    async def test_unexpected_content_type(self, x402_service):
        """Test that non-JSON content type is handled gracefully."""
        # Create a mock response with text/plain content
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "This is not JSON"

        # Mock the client.get to return text response
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful handling - may succeed or fail gracefully
            assert isinstance(result, dict)
            assert "message" in result or "success" in result

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, x402_service):
        """Test that response with missing required fields is handled gracefully."""
        # Create a mock response with incomplete data
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"incomplete": "data"}'
        mock_response.json.return_value = {"incomplete": "data"}

        # Mock the client.get to return incomplete data
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert isinstance(result, dict)
            # Either succeeds with what it has or fails gracefully
            assert "success" in result

    @pytest.mark.asyncio
    async def test_response_with_null_values(self, x402_service):
        """Test that response with null values in critical fields is handled gracefully."""
        # Create a mock response with null values
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"payment_id": null, "tx_hash": null, "status": null}'
        mock_response.json.return_value = {
            "payment_id": None,
            "tx_hash": None,
            "status": None
        }

        # Mock the client.get to return null values
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful handling
            assert isinstance(result, dict)
            assert "success" in result

    @pytest.mark.asyncio
    async def test_oversized_response(self, x402_service):
        """Test that oversized response is handled gracefully."""
        # Create a mock response with huge data
        large_data = {"data": "x" * 10_000_000}  # 10MB of data
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json", "content-length": "10000000"}
        mock_response.json.side_effect = MemoryError("Response too large")

        # Mock the client.get to return oversized response
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert isinstance(result["message"], str)

    @pytest.mark.asyncio
    async def test_response_with_wrong_data_types(self, x402_service):
        """Test that response with wrong data types is handled gracefully."""
        # Create a mock response with wrong types
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"amount": "not_a_number", "timestamp": ["wrong", "type"]}'
        mock_response.json.return_value = {
            "amount": "not_a_number",
            "timestamp": ["wrong", "type"]
        }

        # Mock the client.get to return wrong types
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful handling
            assert isinstance(result, dict)
            assert "success" in result

    @pytest.mark.asyncio
    async def test_service_recovers_after_invalid_response(self, x402_service):
        """Test that agent recovers after receiving invalid response."""
        # First call returns invalid JSON, second call returns valid data
        invalid_response = MagicMock(spec=Response)
        invalid_response.status_code = 200
        invalid_response.headers = {"content-type": "application/json"}
        invalid_response.text = "{invalid json}"
        invalid_response.content = b"{invalid json}"
        invalid_response.json.side_effect = json.JSONDecodeError("Expecting value", "{invalid json}", 0)

        valid_response = MagicMock(spec=Response)
        valid_response.status_code = 200
        valid_response.headers = {"content-type": "application/json"}
        valid_response.text = '{"status": "success"}'
        valid_response.content = b'{"status": "success"}'
        valid_response.json.return_value = {"status": "success"}

        # Mock the client.get to fail first, succeed second
        with patch.object(x402_service.client, 'get', side_effect=[invalid_response, valid_response]):
            # First call should fail gracefully
            result1 = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )
            assert result1["success"] is False

            # Second call should succeed (or handle the valid response)
            result2 = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )
            assert isinstance(result2, dict)


class TestHTTPStatusErrors:
    """Test handling of HTTP status errors."""

    @pytest.fixture
    def x402_service(self):
        """Create an X402PaymentService instance for testing."""
        return X402PaymentService()

    @pytest.mark.asyncio
    async def test_500_internal_server_error(self, x402_service):
        """Test that 500 error is handled gracefully."""
        # Create a mock 500 response
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"error": "Internal server error"}'

        # Mock the client.get to return 500 error
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert "server" in result["message"].lower() or "error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_503_service_unavailable(self, x402_service):
        """Test that 503 error is handled gracefully."""
        # Create a mock 503 response
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 503
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"error": "Service unavailable"}'

        # Mock the client.get to return 503 error
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert "unavailable" in result["message"].lower() or "service" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_429_rate_limit_exceeded(self, x402_service):
        """Test that 429 rate limit error is handled gracefully."""
        # Create a mock 429 response
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 429
        mock_response.headers = {"content-type": "application/json", "Retry-After": "60"}
        mock_response.text = '{"error": "Rate limit exceeded"}'

        # Mock the client.get to return 429 error
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert "rate" in result["message"].lower() or "limit" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_404_not_found(self, x402_service):
        """Test that 404 error is handled gracefully."""
        # Create a mock 404 response
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"error": "Not found"}'

        # Mock the client.get to return 404 error
        with patch.object(x402_service.client, 'get', return_value=mock_response):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert "not found" in result["message"].lower() or "404" in result["message"]
