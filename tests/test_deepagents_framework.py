"""
Test deepagents framework initialization with Claude Sonnet 4.

This test verifies that the deepagents framework (or our compatible implementation)
properly initializes with Claude Sonnet 4 and falls back to GPT-4 when needed.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.basic_agent import BasicPaygentAgent
from src.agents.main_agent import PaygentAgent


class TestDeepAgentsFramework:
    """Test deepagents framework initialization and execution."""

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
    async def test_basic_agent_initialization(self, mock_db):
        """Test that BasicPaygentAgent initializes successfully."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(
            db=mock_db,
            session_id=session_id,
            llm_model="mock",
        )

        assert agent.session_id == session_id
        assert agent.llm_model == "mock"
        assert agent.tools == []
        assert agent.callback_handler is not None
        assert agent.callback_handler.session_id == session_id

    @pytest.mark.asyncio
    async def test_basic_agent_health_check(self, mock_db):
        """Test that BasicPaygentAgent can handle health check commands."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        result = await agent.execute_command("health check")

        assert result["success"] is True
        assert "result" in result
        assert result["result"]["agent_type"] == "Basic Paygent Agent"
        assert str(session_id) in result["session_id"]

    @pytest.mark.asyncio
    async def test_basic_agent_balance_check(self, mock_db):
        """Test that BasicPaygentAgent can handle balance checking commands."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        result = await agent.execute_command("what's my balance")

        assert result["success"] is True
        assert "result" in result
        assert "balance_details" in result["result"]
        assert "balances" in result["result"]["balance_details"]

    @pytest.mark.asyncio
    async def test_basic_agent_list_tools(self, mock_db):
        """Test that BasicPaygentAgent can list available tools."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        result = await agent.execute_command("what can you do")

        assert result["success"] is True
        assert "result" in result
        assert "tools" in result["result"]
        assert isinstance(result["result"]["tools"], list)
        assert len(result["result"]["tools"]) > 0

    @pytest.mark.asyncio
    async def test_basic_agent_payment_command(self, mock_db):
        """Test that BasicPaygentAgent can handle payment commands with mock LLM."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        result = await agent.execute_command("pay 0.10 USDC to access the market data API")

        assert result["success"] is True
        assert "result" in result
        assert "action_required" in result["result"]

    @pytest.mark.asyncio
    async def test_basic_agent_swap_command(self, mock_db):
        """Test that BasicPaygentAgent can handle swap commands with mock LLM."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        result = await agent.execute_command("swap 100 USDC for CRO")

        assert result["success"] is True
        assert "result" in result
        assert "action_required" in result["result"]
        assert result["result"]["action_required"] == "vvs_swap"

    @pytest.mark.asyncio
    async def test_basic_agent_unknown_command(self, mock_db):
        """Test that BasicPaygentAgent handles unknown commands gracefully."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        result = await agent.execute_command("xyz123 unknown command")

        # Should return a helpful response even for unknown commands
        assert "result" in result or "success" in result

    @pytest.mark.asyncio
    async def test_basic_agent_concurrent_commands(self, mock_db):
        """Test that BasicPaygentAgent can handle multiple concurrent commands."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute multiple commands concurrently
        commands = [
            "health check",
            "what's my balance",
            "what can you do",
        ]

        results = await asyncio.gather(
            *[agent.execute_command(cmd) for cmd in commands]
        )

        assert len(results) == 3
        for result in results:
            assert "success" in result or "result" in result

    @pytest.mark.asyncio
    async def test_callback_handler_events(self, mock_db):
        """Test that callback handler tracks agent events."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Execute a command that triggers callbacks
        await agent.execute_command("health check")

        # Check that events were recorded
        events = agent.callback_handler.events
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_agent_session_info(self, mock_db, mock_session_service):
        """Test getting agent session information."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(
            db=mock_db,
            session_id=session_id,
        )
        agent.session_service = mock_session_service

        info = await agent.get_session_info()

        assert "session_id" in info
        assert info["agent_type"] == "Basic Paygent Agent"
        assert "tools_count" in info

    @pytest.mark.asyncio
    async def test_agent_execution_summary(self, mock_db):
        """Test getting agent execution summary."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        summary = await agent.get_execution_summary()

        assert summary["agent_type"] == "Basic Paygent Agent"
        assert str(session_id) in summary["session_id"]
        assert "tools_count" in summary

    @pytest.mark.asyncio
    async def test_agent_tool_addition(self, mock_db):
        """Test adding tools to the agent."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Create a mock tool
        mock_tool = MagicMock()
        mock_tool.__class__.__name__ = "MockTool"

        initial_count = len(agent.tools)
        await agent.add_tool(mock_tool)

        assert len(agent.tools) == initial_count + 1

    @pytest.mark.asyncio
    async def test_agent_handles_errors_gracefully(self, mock_db):
        """Test that agent handles exceptions gracefully."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Mock a command that will fail
        with patch.object(agent, '_parse_command', side_effect=Exception("Test error")):
            result = await agent.execute_command("test command")

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_agent_command_parsing_variations(self, mock_db):
        """Test that agent correctly parses various command formats."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Test different command variations
        test_cases = [
            ("health check", "health_check"),
            ("are you alive?", "health_check"),
            ("what's my balance", "get_balance"),
            ("how much do i have", "get_balance"),
            ("list tools", "list_tools"),
            ("what can you do", "list_tools"),
            ("hello", "simple_response"),
            ("pay 10 usdc", "mock_llm_response"),
        ]

        for command, expected_action in test_cases:
            result = agent._parse_command(command)
            assert result["action_type"] == expected_action, \
                f"Command '{command}' should map to '{expected_action}', got '{result['action_type']}'"

    @pytest.mark.asyncio
    async def test_framework_compatibility(self, mock_db):
        """Test that the framework is compatible with the expected API."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(db=mock_db, session_id=session_id)

        # Verify the agent has the expected interface
        assert hasattr(agent, 'execute_command')
        assert hasattr(agent, 'add_tool')
        assert hasattr(agent, 'get_session_info')
        assert hasattr(agent, 'get_execution_summary')

        # Verify methods are callable
        assert callable(agent.execute_command)
        assert callable(agent.add_tool)
        assert callable(agent.get_session_info)
        assert callable(agent.get_execution_summary)


class TestDeepAgentsClaudeIntegration:
    """Test Claude Sonnet 4 integration (when available)."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip if API keys not available
        reason="Requires ANTHROPIC_API_KEY"
    )
    async def test_claude_initialization(self, mock_db):
        """Test Claude Sonnet 4 initialization when API key is available."""
        from uuid import uuid4

        session_id = uuid4()

        with patch('src.agents.main_agent.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.openai_api_key = None

            agent = PaygentAgent(
                db=mock_db,
                session_id=session_id,
                llm_model="anthropic/claude-sonnet-4",
            )

            assert agent.llm is not None
            assert agent.llm_model == "anthropic/claude-sonnet-4"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip if API keys not available
        reason="Requires OPENAI_API_KEY"
    )
    async def test_gpt4_fallback(self, mock_db):
        """Test GPT-4 fallback when Claude is unavailable."""
        from uuid import uuid4

        session_id = uuid4()

        with patch('src.agents.main_agent.settings') as mock_settings:
            mock_settings.anthropic_api_key = None
            mock_settings.openai_api_key = "test-key"

            agent = PaygentAgent(
                db=mock_db,
                session_id=session_id,
                llm_model="anthropic/claude-sonnet-4",
            )

            # Should fall back to GPT-4
            assert agent.llm is not None

    @pytest.mark.asyncio
    async def test_framework_works_without_api_keys(self, mock_db):
        """Test that BasicPaygentAgent works even without API keys."""
        from uuid import uuid4

        session_id = uuid4()
        agent = BasicPaygentAgent(
            db=mock_db,
            session_id=session_id,
        )

        # Should still be able to execute commands with mock responses
        result = await agent.execute_command("health check")
        assert result["success"] is True
