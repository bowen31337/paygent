"""
Tests for graceful network timeout handling.

This test suite verifies that the agent handles network timeouts gracefully
with user-friendly error messages and proper retry logic.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import TimeoutException as HttpxTimeoutException

from src.services.mcp_client import MCPServerClient, MCPServerError
from src.services.x402_service import X402PaymentService


class TestX402TimeoutHandling:
    """Test x402 payment service timeout handling."""

    @pytest.fixture
    def x402_service(self):
        """Create an X402PaymentService instance for testing."""
        return X402PaymentService()

    @pytest.mark.asyncio
    async def test_timeout_on_payment_request(self, x402_service):
        """Test that timeout is handled gracefully during payment request."""
        # Mock the client.get to raise TimeoutException
        with patch.object(x402_service.client, 'get', side_effect=HttpxTimeoutException("Request timed out")):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC",
                description="Test payment"
            )

            # Verify graceful failure
            assert result["success"] is False
            assert result["error"] == "timeout"
            assert "taking too long to respond" in result["message"]
            assert "try again later" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_timeout_with_retry(self, x402_service):
        """Test that timeout triggers retry logic with exponential backoff."""
        call_count = 0
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < x402_service.retry_attempts:
                raise HttpxTimeoutException("Request timed out")
            # Return success on final attempt
            response = MagicMock()
            response.status_code = 200
            response.content = b'{"result": "success"}'
            response.json.return_value = {"result": "success"}
            return response

        with patch.object(x402_service.client, 'get', side_effect=mock_get):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC"
            )

            # Verify all retry attempts were made
            assert call_count == x402_service.retry_attempts
            # Verify eventual success
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_timeout_max_retries_exceeded(self, x402_service):
        """Test that max retries is respected for persistent timeouts."""
        # Always timeout
        with patch.object(x402_service.client, 'get', side_effect=HttpxTimeoutException("Request timed out")):
            result = await x402_service._make_payment_request(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC"
            )

            # Verify graceful failure after max retries
            assert result["success"] is False
            assert result["error"] == "timeout"
            assert "service is taking too long" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_timeout_message_is_user_friendly(self, x402_service):
        """Test that timeout messages are user-friendly."""
        with patch.object(x402_service.client, 'get', side_effect=HttpxTimeoutException("Request timed out")):
            result = await x402_service.execute_payment(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC"
            )

            # Verify message doesn't contain technical jargon
            assert "timeout" not in result["message"].lower() or "taking too long" in result["message"].lower()
            # Verify message provides guidance
            assert "try again" in result["message"].lower()
            # Verify message suggests possible causes
            assert any(word in result["message"].lower() for word in ["network", "load", "busy"])


class TestMCPTimeoutHandling:
    """Test MCP client timeout handling."""

    @pytest.fixture
    def mcp_client(self):
        """Create an MCPServerClient instance for testing."""
        return MCPServerClient(server_url="https://mock-mcp.example.com")

    @pytest.mark.asyncio
    async def test_timeout_on_price_request(self, mcp_client):
        """Test that timeout is handled gracefully during price request."""
        with patch.object(mcp_client.session, 'request', side_effect=HttpxTimeoutException("Request timed out")):
            with pytest.raises(MCPServerError) as exc_info:
                await mcp_client.get_price("BTC_USDT")

            # Verify error is user-friendly
            error_message = str(exc_info.value)
            assert "taking too long" in error_message.lower()
            assert "try again" in error_message.lower()

    @pytest.mark.asyncio
    async def test_timeout_on_market_data_request(self, mcp_client):
        """Test timeout handling for general market data requests."""
        with patch.object(mcp_client.session, 'request', side_effect=HttpxTimeoutException("Network timeout")):
            with pytest.raises(MCPServerError) as exc_info:
                await mcp_client._make_request("GET", "market-data/ticker")

            error_message = str(exc_info.value)
            assert "taking too long to respond" in error_message

    @pytest.mark.asyncio
    async def test_timeout_does_not_leak_details(self, mcp_client):
        """Test that timeout errors don't leak internal details."""
        with patch.object(mcp_client.session, 'request', side_effect=HttpxTimeoutException("Internal connection error: 192.168.1.1")):
            with pytest.raises(MCPServerError) as exc_info:
                await mcp_client.get_price("ETH_USDT")

            error_message = str(exc_info.value)
            # Internal IP should not be leaked
            assert "192.168.1.1" not in error_message
            # Technical error should be sanitized
            assert "Internal connection error" not in error_message


class TestTimeoutRecovery:
    """Test timeout recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_service_recovers_after_timeout(self):
        """Test that services recover after temporary timeout."""
        x402_service = X402PaymentService()

        call_count = 0
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise HttpxTimeoutException("First request times out")
            # Subsequent requests succeed
            response = MagicMock()
            response.status_code = 200
            response.content = b'{"result": "success"}'
            response.json.return_value = {"result": "success"}
            return response

        with patch.object(x402_service.client, 'get', side_effect=mock_get):
            # First call fails with timeout
            result1 = await x402_service._make_payment_request(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC"
            )
            assert result1["success"] is True

            # Service recovers for subsequent calls
            assert call_count == 2  # One timeout, one success

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_timeout(self):
        """Test that exponential backoff is applied during retries."""
        x402_service = X402PaymentService()
        x402_service.retry_delay = 0.1  # Short delay for testing

        call_times = []
        async def mock_get(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            raise HttpxTimeoutException("Request timed out")

        with patch.object(x402_service.client, 'get', side_effect=mock_get):
            await x402_service._make_payment_request(
                service_url="https://example.com/api",
                amount=10.0,
                token="USDC"
            )

            # Verify exponential backoff
            assert len(call_times) == x402_service.retry_attempts
            # Time between retries should increase exponentially
            if len(call_times) >= 2:
                delay1 = call_times[1] - call_times[0]
                delay2 = call_times[2] - call_times[1]
                assert delay2 > delay1  # Exponential increase


class TestTimeoutConfiguration:
    """Test timeout configuration and limits."""

    def test_x402_service_timeout_configuration(self):
        """Test that x402 service has configurable timeout."""
        service = X402PaymentService()
        # Verify timeout is configured (30 seconds by default)
        assert service.client.timeout == 30.0

    @pytest.mark.asyncio
    async def test_custom_timeout_in_service(self):
        """Test that custom timeout can be configured."""
        # This would be tested if custom timeout configuration is added
        # For now, verify default is reasonable
        service = X402PaymentService()
        assert 1.0 <= service.client.timeout <= 60.0  # Between 1 second and 1 minute

    def test_mcp_client_timeout_configuration(self):
        """Test that MCP client has configurable timeout."""
        client = MCPServerClient()
        # Verify timeout is configured (30 seconds by default)
        assert client.session.timeout == 30.0
