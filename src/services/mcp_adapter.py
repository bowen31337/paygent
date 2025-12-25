"""
LangChain MCP Adapter for Crypto.com Integration.

This module provides LangChain-compatible MCP adapters for seamless integration
with Crypto.com services using the MCP protocol.
"""

import logging
from typing import Any

# Import only what we need, avoid problematic dependencies
from pydantic import BaseModel, Field

from src.services.mcp_client import MCPServerClient, get_mcp_client

logger = logging.getLogger(__name__)


class MCPAdapterError(Exception):
    """MCP adapter specific error."""
    pass


class CryptoComMCPAdapter:
    """
    LangChain MCP Adapter for Crypto.com Market Data MCP Server.

    This adapter provides LangChain tools that integrate with the Crypto.com
    Market Data MCP Server for real-time cryptocurrency market data.
    """

    def __init__(self, mcp_client: MCPServerClient | None = None):
        """
        Initialize the MCP adapter.

        Args:
            mcp_client: Optional MCP client instance. If None, uses global client.
        """
        self.mcp_client = mcp_client or get_mcp_client()
        self.adapter_config = None
        self.tools = []

    async def initialize(self) -> None:
        """
        Initialize the MCP adapter with the server.

        This method establishes the connection to the MCP server and
        retrieves available capabilities.
        """
        try:
            # Test connection to MCP server
            is_healthy = await self.mcp_client.health_check()
            if not is_healthy:
                raise MCPAdapterError("MCP server is not healthy")

            # Create LangChain tools from MCP capabilities
            self.tools = await self._create_tools_from_mcp_capabilities()

            logger.info("Crypto.com MCP adapter initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MCP adapter: {e}")
            raise MCPAdapterError(f"Initialization failed: {e}")

    async def _create_tools_from_mcp_capabilities(self) -> list[Any]:
        """
        Create LangChain tools based on MCP server capabilities.

        Returns:
            List of LangChain tool objects
        """
        try:
            # Get market status to verify server capabilities
            market_status = await self.mcp_client.get_market_status()

            tools = []

            # Create price-related tools based on supported symbols
            supported_symbols = await self.mcp_client.get_supported_symbols()

            if supported_symbols:
                # Tool for getting single price
                from langchain.tools import BaseTool

                class GetPriceInput(BaseModel):
                    symbol: str = Field(..., description="Trading pair symbol (e.g., BTC_USDT)")

                class GetPriceTool(BaseTool):
                    name: str = "get_crypto_price"
                    description: str = "Get current price for a cryptocurrency trading pair"
                    args_schema: type[BaseModel] = GetPriceInput
                    mcp_client: MCPServerClient

                    def __init__(self, mcp_client: MCPServerClient, **kwargs):
                        super().__init__(**kwargs)
                        object.__setattr__(self, 'mcp_client', mcp_client)

                    async def _arun(self, symbol: str) -> dict[str, Any]:
                        """Async implementation of price retrieval."""
                        try:
                            price_data = await self.mcp_client.get_price(symbol)
                            return {
                                "symbol": price_data.symbol,
                                "price": price_data.price,
                                "volume_24h": price_data.volume_24h,
                                "change_24h": price_data.change_24h,
                                "timestamp": price_data.timestamp,
                                "success": True
                            }
                        except Exception as e:
                            return {
                                "error": str(e),
                                "success": False
                            }

                    def _run(self, symbol: str) -> dict[str, Any]:
                        """Synchronous wrapper for price retrieval."""
                        import asyncio
                        return asyncio.run(self._arun(symbol))

                # Create multiple price tool
                class GetPricesInput(BaseModel):
                    symbols: list[str] = Field(..., description="List of trading pair symbols")

                class GetPricesTool(BaseTool):
                    name: str = "get_crypto_prices"
                    description: str = "Get prices for multiple cryptocurrency trading pairs"
                    args_schema: type[BaseModel] = GetPricesInput
                    mcp_client: MCPServerClient

                    def __init__(self, mcp_client: MCPServerClient, **kwargs):
                        super().__init__(**kwargs)
                        object.__setattr__(self, 'mcp_client', mcp_client)

                    async def _arun(self, symbols: list[str]) -> dict[str, Any]:
                        """Async implementation of multiple price retrieval."""
                        try:
                            prices = await self.mcp_client.get_multiple_prices(symbols)
                            return {
                                "prices": [
                                    {
                                        "symbol": p.symbol,
                                        "price": p.price,
                                        "volume_24h": p.volume_24h,
                                        "change_24h": p.change_24h,
                                        "timestamp": p.timestamp
                                    }
                                    for p in prices
                                ],
                                "total_symbols": len(prices),
                                "success": True
                            }
                        except Exception as e:
                            return {
                                "error": str(e),
                                "success": False
                            }

                    def _run(self, symbols: list[str]) -> dict[str, Any]:
                        """Synchronous wrapper for multiple price retrieval."""
                        import asyncio
                        return asyncio.run(self._arun(symbols))

                # Create market status tool
                class GetMarketStatusTool(BaseTool):
                    name: str = "get_market_status"
                    description: str = "Get current market status and server information"
                    mcp_client: MCPServerClient

                    def __init__(self, mcp_client: MCPServerClient, **kwargs):
                        super().__init__(**kwargs)
                        object.__setattr__(self, 'mcp_client', mcp_client)

                    async def _arun(self) -> dict[str, Any]:
                        """Async implementation of market status retrieval."""
                        try:
                            status = await self.mcp_client.get_market_status()
                            return {
                                "market_status": status,
                                "success": True
                            }
                        except Exception as e:
                            return {
                                "error": str(e),
                                "success": False
                            }

                    def _run(self) -> dict[str, Any]:
                        """Synchronous wrapper for market status retrieval."""
                        import asyncio
                        return asyncio.run(self._arun())

                # Add tools to the list
                tools.extend([
                    GetPriceTool(self.mcp_client),
                    GetPricesTool(self.mcp_client),
                    GetMarketStatusTool(self.mcp_client)
                ])

            return tools

        except Exception as e:
            logger.error(f"Failed to create MCP tools: {e}")
            return []

    async def get_tools(self) -> list[Any]:
        """
        Get the list of available LangChain tools.

        Returns:
            List of LangChain tool objects
        """
        if not self.tools:
            await self.initialize()

        return self.tools

    async def is_healthy(self) -> bool:
        """
        Check if the MCP adapter is healthy and connected.

        Returns:
            True if healthy, False otherwise
        """
        try:
            return await self.mcp_client.health_check()
        except Exception:
            return False

    async def get_server_info(self) -> dict[str, Any]:
        """
        Get information about the MCP server.

        Returns:
            Dictionary containing server information
        """
        try:
            return await self.mcp_client.get_market_status()
        except Exception as e:
            return {"error": str(e), "success": False}


# Global MCP adapter instance
_mcp_adapter: CryptoComMCPAdapter | None = None


def get_mcp_adapter() -> CryptoComMCPAdapter:
    """
    Get the global MCP adapter instance.

    Returns:
        CryptoComMCPAdapter instance
    """
    global _mcp_adapter
    if _mcp_adapter is None:
        _mcp_adapter = CryptoComMCPAdapter()
    return _mcp_adapter


def create_mcp_adapter(mcp_client: MCPServerClient | None = None) -> CryptoComMCPAdapter:
    """
    Create a new MCP adapter instance.

    Args:
        mcp_client: Optional MCP client instance

    Returns:
        CryptoComMCPAdapter instance
    """
    return CryptoComMCPAdapter(mcp_client)
