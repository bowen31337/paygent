"""
Unit tests for agent execution API routes.

Tests the /api/v1/agent/execute endpoint and related functionality.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from uuid import UUID

from src.main import app
from src.core.database import get_db
from tests.conftest import TEST_DATABASE_URL


class TestAgentExecute:
    """Test agent execute command endpoint."""

    @pytest.mark.asyncio
    async def test_execute_command_returns_200(self, db_session):
        """Test that execute command returns 200 status."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={"command": "Pay 0.10 USDC to access the market data API"}
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_command_returns_session_id(self, db_session):
        """Test that execute command returns a session_id."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={"command": "Pay 0.10 USDC to access the market data API"}
            )
            data = response.json()

            assert "session_id" in data
            # Verify it's a valid UUID
            UUID(data["session_id"])

    @pytest.mark.asyncio
    async def test_execute_command_returns_status(self, db_session):
        """Test that execute command returns execution status."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={"command": "Pay 0.10 USDC to access the market data API"}
            )
            data = response.json()

            assert "status" in data
            assert data["status"] in ["completed", "running", "failed"]

    @pytest.mark.asyncio
    async def test_execute_command_validates_empty_command(self, db_session):
        """Test that execute command rejects empty command strings."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={"command": ""}
            )
            # Should fail validation
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_execute_command_validates_missing_command(self, db_session):
        """Test that execute command rejects missing command field."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={}
            )
            # Should fail validation
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_execute_command_with_existing_session(self, db_session):
        """Test that execute command can reuse an existing session."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # First execution - creates session
            response1 = await client.post(
                "/api/v1/agent/execute",
                json={"command": "First command"}
            )
            data1 = response1.json()
            session_id = data1["session_id"]

            # Second execution - reuse session
            response2 = await client.post(
                "/api/v1/agent/execute",
                json={"command": "Second command", "session_id": session_id}
            )
            data2 = response2.json()

            assert data2["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_execute_command_with_budget_limit(self, db_session):
        """Test that execute command accepts budget limit."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={
                    "command": "Pay 0.10 USDC",
                    "budget_limit_usd": 100.0
                }
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_command_returns_result(self, db_session):
        """Test that execute command returns result data."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={"command": "Pay 0.10 USDC to access the market data API"}
            )
            data = response.json()

            assert "result" in data
            assert isinstance(data["result"], dict)

    @pytest.mark.asyncio
    async def test_execute_command_returns_total_cost(self, db_session):
        """Test that execute command returns total cost."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={"command": "Pay 0.10 USDC"}
            )
            data = response.json()

            assert "total_cost_usd" in data
            assert isinstance(data["total_cost_usd"], (int, float))

    @pytest.mark.asyncio
    async def test_execute_command_stores_in_database(self, db_session):
        """Test that execute command stores session and log in database."""
        from sqlalchemy import select
        from src.models.agent_sessions import AgentSession, ExecutionLog

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/execute",
                json={"command": "Test command"}
            )
            data = response.json()
            session_id = data["session_id"]

            # Verify session exists in DB
            result = await db_session.execute(
                select(AgentSession).where(AgentSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            assert session is not None

            # Verify execution log exists
            result = await db_session.execute(
                select(ExecutionLog).where(ExecutionLog.session_id == session_id)
            )
            log = result.scalar_one_or_none()
            assert log is not None
            assert log.command == "Test command"


class TestAgentSessions:
    """Test agent session management endpoints."""

    @pytest.mark.asyncio
    async def test_list_sessions_returns_200(self, db_session):
        """Test that list sessions returns 200."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/agent/sessions")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_sessions_returns_structure(self, db_session):
        """Test that list sessions returns correct structure."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/agent/sessions")
            data = response.json()

            assert "sessions" in data
            assert "total" in data
            assert "offset" in data
            assert "limit" in data
            assert isinstance(data["sessions"], list)
