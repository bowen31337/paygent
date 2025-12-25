"""
Crypto.com Market Data MCP Server Client.

This module provides a client for interacting with the Crypto.com Market Data MCP Server
to get real-time cryptocurrency prices and market data.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Price data structure for market data responses."""
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    timestamp: int


class MCPServerError(Exception):
    """MCP server specific error."""
    pass


class MCPServerClient:
    """
    Client for Crypto.com Market Data MCP Server.

    This client handles:
    - Connecting to the MCP server
    - Querying market data
    - Handling MCP protocol responses
    - Rate limiting and error handling
    """

    def __init__(self, server_url: str | None = None):
        """
        Initialize the MCP server client.

        Args:
            server_url: URL of the MCP server. If None, uses settings.crypto_com_mcp_url
        """
        self.server_url = server_url or settings.crypto_com_mcp_url
        self.api_key = settings.crypto_com_api_key
        self.session = httpx.AsyncClient(timeout=30.0)
        self.last_request_time = 0
        self.rate_limit_delay = 0.1  # 100ms between requests

    async def __aenter__(self) -> "MCPServerClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP session."""
        await self.session.aclose()

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time: float = time.time()
        time_since_last: float = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)

        self.last_request_time = time.time()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """
        Make an authenticated request to the MCP server.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request arguments

        Returns:
            Response JSON data

        Raises:
            MCPServerError: If the request fails
        """
        await self._rate_limit()

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.server_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            response = await self.session.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()

            data = response.json()

            # Log response time for performance monitoring
            response_time = response.elapsed.total_seconds() * 1000
            logger.info(f"MCP request to {endpoint} completed in {response_time:.2f}ms")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"MCP server HTTP error: {e.response.status_code} - {e.response.text}")
            raise MCPServerError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"MCP server request error: {e}")
            raise MCPServerError(f"Request failed: {e}")
        except Exception as e:
            logger.error(f"MCP server unexpected error: {e}")
            raise MCPServerError(f"Unexpected error: {e}")

    async def get_price(self, symbol: str) -> PriceData:
        """
        Get current price for a cryptocurrency symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC_USDT', 'ETH_USDC')

        Returns:
            PriceData with current market information

        Example:
            price = await client.get_price("BTC_USDT")
            print(f"BTC/USDT: ${price.price}")
        """
        logger.info(f"Getting price for {symbol}")

        # MCP protocol endpoint for market data
        # Note: This is a mock implementation - real MCP endpoints would be different
        endpoint = f"market-data/price/{symbol.upper()}"

        try:
            data = await self._make_request("GET", endpoint)

            # Parse MCP response format
            # Expected format: {"symbol": "BTC_USDT", "price": 50000.0, "volume": 1000.0, "change": 2.5, "timestamp": 1234567890}
            price_data = PriceData(
                symbol=data["symbol"],
                price=float(data["price"]),
                volume_24h=float(data.get("volume", 0)),
                change_24h=float(data.get("change", 0)),
                timestamp=int(data.get("timestamp", int(datetime.now().timestamp())))
            )

            logger.info(f"Price data for {symbol}: {price_data.price}")
            return price_data

        except KeyError as e:
            raise MCPServerError(f"Invalid response format - missing field: {e}")
        except Exception as e:
            raise MCPServerError(f"Failed to parse price data: {e}")

    async def get_multiple_prices(self, symbols: list[str]) -> list[PriceData]:
        """
        Get prices for multiple symbols in a single request.

        Args:
            symbols: List of trading pair symbols

        Returns:
            List of PriceData objects
        """
        logger.info(f"Getting prices for {len(symbols)} symbols")

        # MCP batch endpoint
        endpoint = "market-data/prices/batch"

        try:
            response = await self._make_request(
                "POST",
                endpoint,
                json={"symbols": symbols}
            )

            prices = []
            for symbol_data in response.get("prices", []):
                price_data = PriceData(
                    symbol=symbol_data["symbol"],
                    price=float(symbol_data["price"]),
                    volume_24h=float(symbol_data.get("volume", 0)),
                    change_24h=float(symbol_data.get("change", 0)),
                    timestamp=int(symbol_data.get("timestamp", int(datetime.now().timestamp())))
                )
                prices.append(price_data)

            logger.info(f"Retrieved {len(prices)} prices successfully")
            return prices

        except Exception as e:
            raise MCPServerError(f"Failed to get multiple prices: {e}")

    async def get_supported_symbols(self) -> list[str]:
        """
        Get list of supported trading symbols.

        Returns:
            List of available trading pair symbols
        """
        logger.info("Getting supported symbols")

        try:
            data = await self._make_request("GET", "market-data/symbols")

            symbols = data.get("symbols", [])
            logger.info(f"Found {len(symbols)} supported symbols")
            return symbols

        except Exception as e:
            raise MCPServerError(f"Failed to get supported symbols: {e}")

    async def get_market_status(self) -> dict[str, Any]:
        """
        Get market status and server information.

        Returns:
            Dict containing market status information
        """
        logger.info("Getting market status")

        try:
            data = await self._make_request("GET", "market-data/status")

            status = {
                "server_time": data.get("server_time"),
                "market_status": data.get("market_status"),
                "supported_symbols": data.get("supported_symbols", 0),
                "api_version": data.get("api_version"),
                "rate_limit": data.get("rate_limit", {}),
                "timestamp": int(datetime.now().timestamp())
            }

            logger.info(f"Market status: {status}")
            return status

        except Exception as e:
            raise MCPServerError(f"Failed to get market status: {e}")

    async def health_check(self) -> bool:
        """
        Perform a health check on the MCP server connection.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            await self.get_market_status()
            return True
        except MCPServerError:
            return False


# Global MCP client instance
_mcp_client: MCPServerClient | None = None


def get_mcp_client() -> MCPServerClient:
    """
    Get the global MCP client instance.

    Returns:
        MCPServerClient instance
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPServerClient()
    return _mcp_client


def create_mcp_client(server_url: str | None = None) -> MCPServerClient:
    """
    Create a new MCP client instance.

    Args:
        server_url: Optional custom server URL

    Returns:
        MCPServerClient instance
    """
    return MCPServerClient(server_url)
