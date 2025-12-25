"""Test agent tools functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tools import DiscoverServicesTool, X402PaymentTool
from src.models import Service
from src.services.service_registry import ServiceRegistryService
from src.services.x402_service import X402PaymentService


def test_x402_payment_tool_initialization():
    """Test X402PaymentTool initialization."""
    mock_payment_service = AsyncMock(spec=X402PaymentService)
    tool = X402PaymentTool(mock_payment_service)

    assert tool.name == "x402_payment"
    assert "x402 protocol" in tool.description
    assert tool.payment_service == mock_payment_service


def test_discover_services_tool_initialization():
    """Test DiscoverServicesTool initialization."""
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)
    tool = DiscoverServicesTool(mock_service_registry)

    assert tool.name == "discover_services"
    assert "MCP-compatible" in tool.description
    assert tool.service_registry == mock_service_registry


@pytest.mark.asyncio
async def test_x402_payment_tool_success():
    """Test successful x402 payment execution."""
    mock_payment_service = AsyncMock(spec=X402PaymentService)
    mock_payment_service.execute_payment = AsyncMock(return_value={
        "payment_id": "pay_123",
        "tx_hash": "0xabc123",
        "status": "completed"
    })

    tool = X402PaymentTool(mock_payment_service)

    result = await tool._arun(
        service_url="https://api.example.com/data",
        amount=0.1,
        token="USDC",
        description="Market data access"
    )

    assert result["success"] is True
    assert result["payment_id"] == "pay_123"
    assert result["tx_hash"] == "0xabc123"
    assert result["status"] == "completed"
    assert "successfully" in result["message"]


@pytest.mark.asyncio
async def test_x402_payment_tool_failure():
    """Test x402 payment execution failure."""
    mock_payment_service = AsyncMock(spec=X402PaymentService)
    mock_payment_service.execute_payment = AsyncMock(side_effect=Exception("Payment failed"))

    tool = X402PaymentTool(mock_payment_service)

    result = await tool._arun(
        service_url="https://api.example.com/data",
        amount=0.1,
        token="USDC"
    )

    assert result["success"] is False
    assert "Payment failed" in result["error"]
    assert "failed" in result["message"]


@pytest.mark.asyncio
async def test_x402_payment_tool_missing_description():
    """Test x402 payment with missing optional description."""
    mock_payment_service = AsyncMock(spec=X402PaymentService)
    mock_payment_service.execute_payment = AsyncMock(return_value={
        "payment_id": "pay_456",
        "tx_hash": "0xdef456",
        "status": "completed"
    })

    tool = X402PaymentTool(mock_payment_service)

    result = await tool._arun(
        service_url="https://api.example.com/data",
        amount=1.0,
        token="CRO"
        # No description provided
    )

    assert result["success"] is True
    assert result["payment_id"] == "pay_456"


@pytest.mark.asyncio
async def test_discover_services_tool_success():
    """Test successful service discovery."""
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)

    # Create mock services
    mock_service = MagicMock(spec=Service)
    mock_service.id = "service_123"
    mock_service.name = "Market Data API"
    mock_service.description = "Real-time market data"
    mock_service.endpoint = "https://marketdata.example.com"
    mock_service.pricing_model = "pay-per-call"
    mock_service.price_amount = 0.1
    mock_service.price_token = "USDC"
    mock_service.mcp_compatible = True
    mock_service.reputation_score = 4.5

    mock_service_registry.discover_services = AsyncMock(return_value=[mock_service])

    tool = DiscoverServicesTool(mock_service_registry)

    result = await tool._arun(
        query="market data",
        category="finance",
        max_results=5
    )

    assert result["success"] is True
    assert len(result["services"]) == 1
    service = result["services"][0]
    assert service["name"] == "Market Data API"
    assert service["description"] == "Real-time market data"
    assert service["endpoint"] == "https://marketdata.example.com"
    assert service["price_amount"] == 0.1
    assert service["price_token"] == "USDC"
    assert service["mcp_compatible"] is True
    assert service["reputation_score"] == 4.5


@pytest.mark.asyncio
async def test_discover_services_tool_no_results():
    """Test service discovery with no results."""
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)
    mock_service_registry.discover_services = AsyncMock(return_value=[])

    tool = DiscoverServicesTool(mock_service_registry)

    result = await tool._arun(
        query="nonexistent service",
        max_results=10
    )

    assert result["success"] is True
    assert result["services"] == []


@pytest.mark.asyncio
async def test_discover_services_tool_failure():
    """Test service discovery failure."""
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)
    mock_service_registry.discover_services = AsyncMock(side_effect=Exception("Database error"))

    tool = DiscoverServicesTool(mock_service_registry)

    result = await tool._arun(
        query="test query"
    )

    assert result["success"] is False
    assert "Database error" in result["error"]


@pytest.mark.asyncio
async def test_discover_services_tool_optional_parameters():
    """Test service discovery with optional parameters."""
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)
    mock_service_registry.discover_services = AsyncMock(return_value=[])

    tool = DiscoverServicesTool(mock_service_registry)

    # Test with only required parameter
    await tool._arun(query="test")

    # Test with all parameters
    await tool._arun(
        query="test",
        category="finance",
        max_results=20
    )

    # Verify the service registry was called correctly
    assert mock_service_registry.discover_services.call_count == 2


@pytest.mark.asyncio
async def test_x402_payment_tool_parameter_validation():
    """Test x402 payment parameter validation."""
    mock_payment_service = AsyncMock(spec=X402PaymentService)
    tool = X402PaymentTool(mock_payment_service)

    # Test with minimum required parameters
    result = await tool._arun(
        service_url="https://api.example.com",
        amount=1.0,
        token="USDC"
    )

    # Should work even with minimal parameters
    assert "success" in result


@pytest.mark.asyncio
async def test_tool_name_and_description():
    """Test that tool names and descriptions are correct."""
    mock_payment_service = AsyncMock(spec=X402PaymentService)
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)

    payment_tool = X402PaymentTool(mock_payment_service)
    discovery_tool = DiscoverServicesTool(mock_service_registry)

    assert payment_tool.name == "x402_payment"
    assert "HTTP 402" in payment_tool.description
    assert "x402 protocol" in payment_tool.description

    assert discovery_tool.name == "discover_services"
    assert "MCP-compatible" in discovery_tool.description
    assert "x402 payment protocol" in discovery_tool.description


@pytest.mark.asyncio
async def test_x402_payment_service_call():
    """Test that the payment service is called with correct parameters."""
    mock_payment_service = AsyncMock(spec=X402PaymentService)
    tool = X402PaymentTool(mock_payment_service)

    await tool._arun(
        service_url="https://api.example.com/data",
        amount=0.5,
        token="ETH",
        description="Premium API access"
    )

    mock_payment_service.execute_payment.assert_called_once_with(
        service_url="https://api.example.com/data",
        amount=0.5,
        token="ETH",
        description="Premium API access"
    )


@pytest.mark.asyncio
async def test_service_registry_call():
    """Test that the service registry is called with correct parameters."""
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)
    tool = DiscoverServicesTool(mock_service_registry)

    await tool._arun(
        query="market data",
        category="finance",
        max_results=10
    )

    mock_service_registry.discover_services.assert_called_once_with(
        query="market data",
        category="finance",
        limit=10
    )


@pytest.mark.asyncio
async def test_service_conversion():
    """Test that services are properly converted to dictionary format."""
    mock_service_registry = AsyncMock(spec=ServiceRegistryService)

    # Create mock service with all attributes
    mock_service = MagicMock(spec=Service)
    mock_service.id = "service_123"
    mock_service.name = "Test Service"
    mock_service.description = "Test Description"
    mock_service.endpoint = "https://test.example.com"
    mock_service.pricing_model = "subscription"
    mock_service.price_amount = 10.0
    mock_service.price_token = "CRO"
    mock_service.mcp_compatible = False
    mock_service.reputation_score = 3.5

    mock_service_registry.discover_services = AsyncMock(return_value=[mock_service])

    tool = DiscoverServicesTool(mock_service_registry)
    result = await tool._arun(query="test")

    assert result["success"] is True
    assert len(result["services"]) == 1

    service_data = result["services"][0]
    assert service_data["id"] == "service_123"
    assert service_data["name"] == "Test Service"
    assert service_data["description"] == "Test Description"
    assert service_data["endpoint"] == "https://test.example.com"
    assert service_data["pricing_model"] == "subscription"
    assert service_data["price_amount"] == 10.0
    assert service_data["price_token"] == "CRO"
    assert service_data["mcp_compatible"] is False
    assert service_data["reputation_score"] == 3.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
