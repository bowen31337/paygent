"""
Tests for enhanced agent executor logging functionality.

Verifies that:
- Plans are generated and stored
- Tool calls are logged
- Budget limits are enforced
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from uuid import UUID

from src.main import app
from src.core.database import get_db
from src.models.agent_sessions import ExecutionLog


class TestEnhancedExecutorLogging:
    """Test enhanced executor logging features."""

    @pytest.mark.asyncio
    async def test_execute_command_stores_plan(self, db_session):
        """Test that execute command stores execution plan."""
        # Override the get_db dependency to use our test db_session
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                # Execute a payment command (complex operation that should have a plan)
                response = await client.post(
                    "/api/v1/agent/execute",
                    json={"command": "Pay 0.10 USDC to market data API"}
                )
                assert response.status_code == 200
                data = response.json()
                session_id = UUID(data["session_id"])

                # Check the execution log
                result = await db_session.execute(
                    select(ExecutionLog).where(ExecutionLog.session_id == session_id)
                )
                log = result.scalar_one_or_none()
                assert log is not None
                assert log.plan is not None, "Plan should be stored for payment commands"
                assert "steps" in log.plan
                assert len(log.plan["steps"]) > 0
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_execute_command_stores_tool_calls(self, db_session):
        """Test that execute command stores tool calls."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                # Execute a balance check command
                response = await client.post(
                    "/api/v1/agent/execute",
                    json={"command": "Check my balance"}
                )
                assert response.status_code == 200
                data = response.json()
                session_id = UUID(data["session_id"])

                # Check the execution log
                result = await db_session.execute(
                    select(ExecutionLog).where(ExecutionLog.session_id == session_id)
                )
                log = result.scalar_one_or_none()
                assert log is not None
                assert log.tool_calls is not None, "Tool calls should be stored"
                assert len(log.tool_calls) > 0, "Should have at least one tool call"

                # Verify tool call structure
                tool_call = log.tool_calls[0]
                assert "tool_name" in tool_call
                assert "tool_args" in tool_call
                assert "result" in tool_call
                assert "timestamp" in tool_call
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_execute_command_with_budget_limit(self, db_session):
        """Test that budget limits are enforced."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                # Execute a command that exceeds budget
                response = await client.post(
                    "/api/v1/agent/execute",
                    json={
                        "command": "Pay 200 USDC to API",
                        "budget_limit_usd": 100.0
                    }
                )
                assert response.status_code == 200
                data = response.json()

                # Should fail due to budget
                assert data["status"] == "failed"
                assert "result" in data
                assert data["result"].get("success") == False
                assert "exceeds budget" in data["result"].get("error", "")
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_swap_command_stores_tool_calls(self, db_session):
        """Test that swap commands store tool calls."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                # Execute a swap command
                response = await client.post(
                    "/api/v1/agent/execute",
                    json={"command": "Swap 100 CRO for USDC"}
                )
                assert response.status_code == 200
                data = response.json()
                session_id = UUID(data["session_id"])

                # Check the execution log
                result = await db_session.execute(
                    select(ExecutionLog).where(ExecutionLog.session_id == session_id)
                )
                log = result.scalar_one_or_none()
                assert log is not None
                assert log.plan is not None, "Swap should have a plan"
                assert log.tool_calls is not None, "Swap should have tool calls"
                assert len(log.tool_calls) > 0
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_service_discovery_stores_tool_calls(self, db_session):
        """Test that service discovery stores tool calls."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                # Execute a service discovery command
                response = await client.post(
                    "/api/v1/agent/execute",
                    json={"command": "Find available services"}
                )
                assert response.status_code == 200
                data = response.json()
                session_id = UUID(data["session_id"])

                # Check the execution log
                result = await db_session.execute(
                    select(ExecutionLog).where(ExecutionLog.session_id == session_id)
                )
                log = result.scalar_one_or_none()
                assert log is not None
                # Service discovery is simple, may not have a plan
                assert log.tool_calls is not None
                assert len(log.tool_calls) > 0
        finally:
            app.dependency_overrides.clear()
