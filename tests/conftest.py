"""
Pytest configuration and shared fixtures.

This module provides common test fixtures for database sessions,
test clients, and mock services.
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import Base
from src.main import app


# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain provider."""
    mock = MagicMock()
    mock.get_balance.return_value = 1000000000000000000  # 1 ETH in wei
    mock.get_chain_id.return_value = 338  # Cronos testnet
    return mock


@pytest.fixture
def mock_x402_client():
    """Create a mock x402 payment client."""
    mock = MagicMock()
    mock.execute_payment.return_value = {
        "success": True,
        "tx_hash": "0x" + "a" * 64,
        "status": "confirmed",
    }
    return mock


@pytest.fixture
def sample_service_data():
    """Sample service data for testing."""
    return {
        "name": "Test Market Data API",
        "description": "Test API for market data",
        "endpoint": "https://api.test.com/v1/market",
        "pricing_model": "pay-per-call",
        "price_amount": 0.01,
        "price_token": "0x" + "0" * 40,
        "mcp_compatible": True,
    }


@pytest.fixture
def sample_payment_data():
    """Sample payment data for testing."""
    return {
        "service_url": "https://api.test.com/v1/market",
        "amount": 0.10,
        "token": "0x" + "0" * 40,
    }


@pytest.fixture
def sample_command():
    """Sample agent command for testing."""
    return "Pay 0.10 USDC to access the market data API"
