"""
Test agent concurrent request handling.

This test verifies that the agent can handle multiple concurrent requests
correctly without race conditions or data corruption.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.basic_agent import BasicPaygentAgent


class TestConcurrentRequests:
    """Test agent concurrent request handling."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.fixture
    def mock_session_service(self):
        """Create a mock session service."""
        service = MagicMock()
        service.update_session_last_active = AsyncMock()
        service.get_session = AsyncMock(return_value=MagicMock(
            id="test-session-id",
            user_id="test-user-id",
            wallet_address="0x1234567890123456789012345678901234567890",
            config={"budget_limit_usd": 1000},
            created_at=MagicMock(isoformat=MagicMock(return_value="2025-12-25T00:00:00Z")),
            last_active=MagicMock(isoformat=MagicMock(return_value="2025-12-25T00:00:00Z")),
        ))
        return service

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, mock_db):
        """Test multiple concurrent health check requests."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute 10 concurrent health checks
        results = await asyncio.gather(
            *[agent.execute_command("health check") for _ in range(10)]
        )

        assert len(results) == 10
        assert all(result["success"] is True for result in results)
        assert all(str(session_id) in result["session_id"] for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_different_commands(self, mock_db):
        """Test concurrent execution of different command types."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        commands = [
            "health check",
            "what's my balance",
            "what can you do",
            "pay 10 usdc",
            "swap 100 usdc for cro",
        ]

        # Execute all commands concurrently
        results = await asyncio.gather(
            *[agent.execute_command(cmd) for cmd in commands]
        )

        assert len(results) == 5
        assert all("success" in result or "result" in result for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_balance_checks(self, mock_db):
        """Test multiple concurrent balance check requests."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute 20 concurrent balance checks
        tasks = [agent.execute_command("what's my balance") for _ in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        assert all(result["success"] is True for result in results)
        assert all("balance_details" in result.get("result", {}) for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_swap_commands(self, mock_db):
        """Test multiple concurrent swap commands."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        swap_commands = [
            f"swap {i} USDC for CRO" for i in range(1, 11)
        ]

        # Execute all swap commands concurrently
        results = await asyncio.gather(
            *[agent.execute_command(cmd) for cmd in swap_commands]
        )

        assert len(results) == 10
        assert all("result" in result for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_agent_creation(self, mock_db):
        """Test creating multiple agents concurrently."""
        from uuid import uuid4

        # Create 10 agents concurrently
        session_ids = [uuid4() for _ in range(10)]

        async def create_and_execute(session_id):
            agent = BasicPaygentAgent(db=mock_db, session_id=session_id)
            return await agent.execute_command("health check")

        results = await asyncio.gather(
            *[create_and_execute(sid) for sid in session_ids]
        )

        assert len(results) == 10
        assert all(result["success"] is True for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_sessions_independence(self, mock_db):
        """Test that concurrent sessions maintain independence."""
        from uuid import uuid4

        # Create multiple agents with different session IDs
        agents = [
            BasicPaygentAgent(db=mock_db, session_id=uuid4())
            for _ in range(5)
        ]

        # Execute different commands in each agent
        commands = [
            "health check",
            "what's my balance",
            "what can you do",
            "pay 10 usdc",
            "swap 50 usdc for cro",
        ]

        results = await asyncio.gather(
            *[agent.execute_command(cmd) for agent, cmd in zip(agents, commands)]
        )

        assert len(results) == 5
        assert all("success" in result or "result" in result for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_tool_addition(self, mock_db):
        """Test concurrent tool addition to agents."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Create mock tools
        mock_tools = []
        for i in range(10):
            tool = MagicMock()
            tool.__class__.__name__ = f"MockTool{i}"
            mock_tools.append(tool)

        # Add all tools concurrently
        await asyncio.gather(
            *[agent.add_tool(tool) for tool in mock_tools]
        )

        # Verify all tools were added
        assert len(agent.tools) == 10

    @pytest.mark.asyncio
    async def test_concurrent_session_info_retrieval(self, mock_db, mock_session_service):
        """Test concurrent session info retrieval."""
        from uuid import uuid4

        agents = [
            BasicPaygentAgent(db=mock_db, session_id=uuid4())
            for _ in range(5)
        ]

        for agent in agents:
            agent.session_service = mock_session_service

        # Get session info concurrently
        results = await asyncio.gather(
            *[agent.get_session_info() for agent in agents]
        )

        assert len(results) == 5
        assert all("session_id" in result for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_execution_summary(self, mock_db):
        """Test concurrent execution summary retrieval."""
        from uuid import uuid4

        agents = [
            BasicPaygentAgent(db=mock_db, session_id=uuid4())
            for _ in range(5)
        ]

        # Get execution summaries concurrently
        results = await asyncio.gather(
            *[agent.get_execution_summary() for agent in agents]
        )

        assert len(results) == 5
        assert all("agent_type" in result for result in results)
        assert all(result["agent_type"] == "Basic Paygent Agent" for result in results)

    @pytest.mark.asyncio
    async def test_high_concurrency_load(self, mock_db):
        """Test agent under high concurrent load (100 requests)."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute 100 concurrent requests
        commands = [
            "health check" if i % 3 == 0 else
            "what's my balance" if i % 3 == 1 else
            "what can you do"
            for i in range(100)
        ]

        results = await asyncio.gather(
            *[agent.execute_command(cmd) for cmd in commands]
        )

        assert len(results) == 100
        # Most should succeed
        successful = sum(1 for r in results if r.get("success") or "result" in r)
        assert successful >= 90  # At least 90% should succeed

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, mock_db):
        """Test concurrent mix of different operation types."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Mix of different operations
        async def health_checks():
            return await asyncio.gather(
                *[agent.execute_command("health check") for _ in range(5)]
            )

        async def balance_checks():
            return await asyncio.gather(
                *[agent.execute_command("what's my balance") for _ in range(5)]
            )

        async def tool_listings():
            return await asyncio.gather(
                *[agent.execute_command("what can you do") for _ in range(5)]
            )

        # Execute all operation types concurrently
        results = await asyncio.gather(
            health_checks(),
            balance_checks(),
            tool_listings(),
        )

        # Flatten results
        all_results = [item for sublist in results for item in sublist]

        assert len(all_results) == 15
        assert all("success" in r or "result" in r for r in all_results)

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, mock_db):
        """Test error handling under concurrent load."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Mix of valid and potentially problematic commands
        commands = [
            "health check",
            "xyz123 unknown command",
            "what's my balance",
            "another unknown command abc",
            "what can you do",
        ]

        results = await asyncio.gather(
            *[agent.execute_command(cmd) for cmd in commands]
        )

        assert len(results) == 5
        # All should return some result (success or error)
        assert all("success" in r or "error" in r or "result" in r for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_callback_tracking(self, mock_db):
        """Test that callback handlers track events correctly under concurrency."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute concurrent commands
        await asyncio.gather(
            *[agent.execute_command("health check") for _ in range(10)]
        )

        # Check that callback events were tracked
        events = agent.callback_handler.events
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_rapid_consecutive_commands(self, mock_db):
        """Test rapid consecutive commands from the same session."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute commands in rapid succession
        for i in range(50):
            result = await agent.execute_command("health check")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_with_session_service_updates(self, mock_db, mock_session_service):
        """Test concurrent commands with session service updates."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)
        agent.session_service = mock_session_service

        # Execute concurrent commands that update session
        await asyncio.gather(
            *[agent.execute_command("health check") for _ in range(10)]
        )

        # Verify session service was called for each command
        assert mock_session_service.update_session_last_active.call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_agents_with_shared_db(self, mock_db):
        """Test multiple concurrent agents sharing the same DB connection."""
        from uuid import uuid4

        # Create multiple agents with the same mock DB
        agents = [
            BasicPaygentAgent(db=mock_db, session_id=uuid4())
            for _ in range(10)
        ]

        # Execute commands in all agents concurrently
        results = await asyncio.gather(
            *[agent.execute_command("health check") for agent in agents]
        )

        assert len(results) == 10
        assert all(result["success"] is True for result in results)


class TestConcurrentRequestsStress:
    """Stress tests for concurrent request handling."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_extreme_concurrency(self, mock_db):
        """Test agent with extreme concurrency (1000 requests)."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute 1000 concurrent requests
        results = await asyncio.gather(
            *[agent.execute_command("health check") for _ in range(1000)],
            return_exceptions=True,
        )

        # Check results
        successful = sum(
            1 for r in results
            if not isinstance(r, Exception) and (r.get("success") or "result" in r)
        )

        # At least 95% should succeed
        assert successful >= 950

    @pytest.mark.asyncio
    async def test_sustained_concurrent_load(self, mock_db):
        """Test agent under sustained concurrent load."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute multiple waves of concurrent requests
        for wave in range(10):
            results = await asyncio.gather(
                *[agent.execute_command("health check") for _ in range(50)]
            )
            assert all(result["success"] is True for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_with_varying_complexity(self, mock_db):
        """Test concurrent requests with varying complexity."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Mix of simple and complex commands
        commands = []
        for i in range(100):
            if i % 4 == 0:
                commands.append("health check")
            elif i % 4 == 1:
                commands.append("what's my balance")
            elif i % 4 == 2:
                commands.append("what can you do")
            else:
                commands.append(f"swap {i} usdc for cro")

        results = await asyncio.gather(
            *[agent.execute_command(cmd) for cmd in commands]
        )

        assert len(results) == 100
        # Most should succeed
        successful = sum(1 for r in results if r.get("success") or "result" in r)
        assert successful >= 90
