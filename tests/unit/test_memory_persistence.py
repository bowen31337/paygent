"""
Unit tests for memory persistence in AgentExecutorEnhanced.

Tests that conversation memory is properly persisted across command executions.
"""

from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.database import get_db
from src.main import app


class TestMemoryPersistence:
    """Test memory persistence across agent command executions."""

    @pytest.mark.asyncio
    async def test_memory_persistence_basic(self, db_session):
        """Test that basic memory persistence works."""
        from uuid import uuid4

        from sqlalchemy import select

        from src.agents.agent_executor_enhanced import AgentExecutorEnhanced
        from src.models.agent_sessions import AgentMemory, AgentSession

        # Override the get_db dependency
        async def override_get_db():
            yield db_session
        app.dependency_overrides[get_db] = override_get_db

        try:
            # Create a test session
            test_session = AgentSession(
                id=uuid4(),
                user_id=uuid4(),
                wallet_address=None,
                config={}
            )
            db_session.add(test_session)
            await db_session.commit()
            session_id = test_session.id

            # Execute first command
            executor1 = AgentExecutorEnhanced(session_id, db_session)
            result1 = await executor1.execute_command("Check my balance")
            assert result1["success"] is True

            # Verify memory was saved
            result = await db_session.execute(
                select(AgentMemory).where(AgentMemory.session_id == session_id)
            )
            memory_entries = result.scalars().all()
            assert len(memory_entries) == 2  # User message + AI response

            # Execute second command with new executor
            executor2 = AgentExecutorEnhanced(session_id, db_session)
            await executor2.load_memory()
            assert len(executor2.memory) == 2

            # Execute second command
            result2 = await executor2.execute_command("Swap 100 CRO for USDC")
            assert result2["success"] is True

            # Verify memory grew
            result = await db_session.execute(
                select(AgentMemory).where(AgentMemory.session_id == session_id)
            )
            memory_entries = result.scalars().all()
            assert len(memory_entries) == 4  # 2 from first command + 2 from second

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_memory_context_includes_history(self, db_session):
        """Test that memory context includes previous conversation."""
        from uuid import uuid4

        from src.agents.agent_executor_enhanced import AgentExecutorEnhanced
        from src.models.agent_sessions import AgentSession

        # Override the get_db dependency
        async def override_get_db():
            yield db_session
        app.dependency_overrides[get_db] = override_get_db

        try:
            # Create a test session
            test_session = AgentSession(
                id=uuid4(),
                user_id=uuid4(),
                wallet_address=None,
                config={}
            )
            db_session.add(test_session)
            await db_session.commit()
            session_id = test_session.id

            # Execute multiple commands
            executor1 = AgentExecutorEnhanced(session_id, db_session)
            await executor1.execute_command("Check my balance")
            await executor1.execute_command("Swap 100 CRO for USDC")

            # Load memory in new executor
            executor2 = AgentExecutorEnhanced(session_id, db_session)
            await executor2.load_memory()
            context = executor2.get_memory_context()

            # Verify context contains both commands
            assert "Check my balance" in context
            assert "Swap 100 CRO for USDC" in context

        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_memory_via_api_endpoint(self, db_session):
        """Test memory persistence via the API endpoint."""
        from sqlalchemy import select

        from src.models.agent_sessions import AgentMemory

        # Override the get_db dependency
        async def override_get_db():
            yield db_session
        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                # First command
                response1 = await client.post(
                    "/api/v1/agent/execute",
                    json={"command": "Check my balance"}
                )
                assert response1.status_code == 200
                data1 = response1.json()
                session_id = data1["session_id"]

                # Second command with same session
                response2 = await client.post(
                    "/api/v1/agent/execute",
                    json={
                        "command": "Swap 100 CRO for USDC",
                        "session_id": session_id
                    }
                )
                assert response2.status_code == 200
                data2 = response2.json()

                # Verify memory context is returned (inside result)
                assert "memory_context" in data2["result"]
                assert "Check my balance" in data2["result"]["memory_context"]

                # Verify memory in database
                result = await db_session.execute(
                    select(AgentMemory).where(
                        AgentMemory.session_id == UUID(session_id)
                    )
                )
                memory_entries = result.scalars().all()
                assert len(memory_entries) >= 4  # At least 2 commands worth

        finally:
            app.dependency_overrides.clear()
