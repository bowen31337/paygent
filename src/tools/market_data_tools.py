"""
Market data tools for Paygent.

This module provides tools for querying cryptocurrency market data
via the Crypto.com Market Data MCP Server.
"""

import asyncio
import logging
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.services.mcp_client import MCPServerError, PriceData, get_mcp_client

logger = logging.getLogger(__name__)


class GetPriceInput(BaseModel):
    """Input schema for get_price tool."""

    symbol: str = Field(
        ...,
        description="Trading pair symbol (e.g., 'BTC_USDT', 'ETH_USDC')"
    )


class GetPriceTool(BaseTool):
    """Tool for getting cryptocurrency prices from MCP server."""

    name: str = "get_crypto_price"
    description: str = """
    Get current cryptocurrency price from Crypto.com Market Data MCP Server.

    Use this tool when users want to:
    - Check current crypto prices
    - Get market data for trading decisions
    - Query specific trading pairs

    Supports major pairs like BTC_USDT, ETH_USDC, etc.
    Returns price, volume, and 24h change information.
    """
    args_schema: type[BaseModel] = GetPriceInput

    def _run(self, symbol: str) -> dict[str, Any]:
        """
        Get cryptocurrency price synchronously.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict containing price information
        """
        try:
            # Run async method synchronously
            return asyncio.run(self._get_price_async(symbol))
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return {
                "error": str(e),
                "symbol": symbol,
                "timestamp": asyncio.run(asyncio.sleep(0)) or 0  # Fallback timestamp
            }

    async def _get_price_async(self, symbol: str) -> dict[str, Any]:
        """
        Get cryptocurrency price asynchronously.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict containing price information
        """
        logger.info(f"Getting price for {symbol}")

        client = get_mcp_client()

        try:
            # Test connection first
            is_healthy = await client.health_check()
            if not is_healthy:
                logger.warning("MCP server health check failed")

            # Get price data
            price_data: PriceData = await client.get_price(symbol)

            result = {
                "symbol": price_data.symbol,
                "price": price_data.price,
                "volume_24h": price_data.volume_24h,
                "change_24h": price_data.change_24h,
                "timestamp": price_data.timestamp,
                "success": True,
                "source": "Crypto.com Market Data MCP Server"
            }

            logger.info(f"Price for {symbol}: ${price_data.price}")
            return result

        except MCPServerError as e:
            error_msg = f"MCP server error: {e}"
            logger.error(error_msg)
            return {
                "symbol": symbol,
                "error": error_msg,
                "success": False,
                "timestamp": int(asyncio.get_event_loop().time())
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            return {
                "symbol": symbol,
                "error": error_msg,
                "success": False,
                "timestamp": int(asyncio.get_event_loop().time())
            }


class GetPricesInput(BaseModel):
    """Input schema for get_prices tool."""

    symbols: list[str] = Field(
        ...,
        description="List of trading pair symbols to query"
    )


class GetPricesTool(BaseTool):
    """Tool for getting multiple cryptocurrency prices."""

    name: str = "get_crypto_prices"
    description: str = """
    Get multiple cryptocurrency prices from Crypto.com Market Data MCP Server.

    Use this tool when users want to:
    - Check prices for multiple pairs at once
    - Compare different cryptocurrencies
    - Get market overview

    Returns prices for all requested symbols with volume and change data.
    More efficient than multiple single price requests.
    """
    args_schema: type[BaseModel] = GetPricesInput

    def _run(self, symbols: list[str]) -> dict[str, Any]:
        """
        Get multiple cryptocurrency prices synchronously.

        Args:
            symbols: List of trading pair symbols

        Returns:
            Dict containing price information for all symbols
        """
        try:
            return asyncio.run(self._get_prices_async(symbols))
        except Exception as e:
            logger.error(f"Failed to get prices for {symbols}: {e}")
            return {
                "symbols": symbols,
                "error": str(e),
                "success": False,
                "timestamp": 0
            }

    async def _get_prices_async(self, symbols: list[str]) -> dict[str, Any]:
        """
        Get multiple cryptocurrency prices asynchronously.

        Args:
            symbols: List of trading pair symbols

        Returns:
            Dict containing price information for all symbols
        """
        logger.info(f"Getting prices for {len(symbols)} symbols: {symbols}")

        if not symbols:
            return {"error": "No symbols provided", "success": False}

        client = get_mcp_client()

        try:
            # Test connection first
            is_healthy = await client.health_check()
            if not is_healthy:
                logger.warning("MCP server health check failed")

            # Get prices for all symbols
            price_data_list = await client.get_multiple_prices(symbols)

            # Convert to result format
            prices = {}
            for price_data in price_data_list:
                prices[price_data.symbol] = {
                    "price": price_data.price,
                    "volume_24h": price_data.volume_24h,
                    "change_24h": price_data.change_24h,
                    "timestamp": price_data.timestamp
                }

            result = {
                "symbols": symbols,
                "prices": prices,
                "total_symbols": len(prices),
                "success": True,
                "source": "Crypto.com Market Data MCP Server",
                "timestamp": int(asyncio.get_event_loop().time())
            }

            logger.info(f"Retrieved prices for {len(prices)} symbols")
            return result

        except MCPServerError as e:
            error_msg = f"MCP server error: {e}"
            logger.error(error_msg)
            return {
                "symbols": symbols,
                "error": error_msg,
                "success": False,
                "timestamp": int(asyncio.get_event_loop().time())
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            return {
                "symbols": symbols,
                "error": error_msg,
                "success": False,
                "timestamp": int(asyncio.get_event_loop().time())
            }


class GetMarketStatusInput(BaseModel):
    """Input schema for get_market_status tool."""

    pass


class GetMarketStatusTool(BaseTool):
    """Tool for getting market status and server information."""

    name: str = "get_market_status"
    description: str = """
    Get market status and MCP server information.

    Use this tool when users want to:
    - Check if market data service is available
    - Get server status and health
    - Query API limits and capabilities
    - Get list of supported trading pairs

    Returns server status, supported symbols, and API information.
    Useful for debugging connectivity issues.
    """
    args_schema: type[BaseModel] = GetMarketStatusInput

    def _run(self) -> dict[str, Any]:
        """Get market status synchronously."""
        try:
            return asyncio.run(self._get_market_status_async())
        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            return {
                "error": str(e),
                "success": False,
                "timestamp": 0
            }

    async def _get_market_status_async(self) -> dict[str, Any]:
        """
        Get market status asynchronously.

        Returns:
            Dict containing market status information
        """
        logger.info("Getting market status")

        client = get_mcp_client()

        try:
            # Test health first
            is_healthy = await client.health_check()

            # Get detailed status
            status_data = await client.get_market_status()

            result = {
                "server_health": is_healthy,
                "server_time": status_data.get("server_time"),
                "market_status": status_data.get("market_status"),
                "supported_symbols": status_data.get("supported_symbols", 0),
                "api_version": status_data.get("api_version"),
                "rate_limit": status_data.get("rate_limit", {}),
                "success": True,
                "source": "Crypto.com Market Data MCP Server",
                "timestamp": int(asyncio.get_event_loop().time())
            }

            logger.info("Market status retrieved successfully")
            return result

        except MCPServerError as e:
            error_msg = f"MCP server error: {e}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "success": False,
                "timestamp": int(asyncio.get_event_loop().time())
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "success": False,
                "timestamp": int(asyncio.get_event_loop().time())
            }


def get_market_data_tools() -> list[BaseTool]:
    """Get all market data tools."""
    return [
        GetPriceTool(),
        GetPricesTool(),
        GetMarketStatusTool(),
    ]
