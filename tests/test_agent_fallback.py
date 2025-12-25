"""Test agent fallback to OpenAI GPT-4 when Claude is unavailable."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.main_agent import PaygentAgent
from src.core.config import settings
from src.services.mcp_adapter import get_mcp_adapter


@pytest.mark.asyncio
async def test_agent_fallback_to_gpt4():
    """Test that agent falls back to GPT-4 when Claude is unavailable."""

    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock settings to have OpenAI API key but no Anthropic key
    with patch.object(settings, 'anthropic_api_key', None), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('src.agents.main_agent.ChatOpenAI') as mock_openai:

        # Mock the OpenAI client
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm

        # Create agent - should use GPT-4 fallback
        agent = PaygentAgent(
            db=mock_db,
            session_id="test-session-id",
            llm_model="anthropic/claude-sonnet-4"  # Requesting Claude but no key
        )

        # Verify that OpenAI was initialized
        mock_openai.assert_called_once_with(
            model="gpt-4",
            temperature=0.1,
            max_tokens=4000,
            api_key="test-openai-key",
        )

        # Verify the agent was created with the GPT-4 LLM
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_fallback_when_claude_fails():
    """Test that agent falls back to GPT-4 when Claude initialization fails."""

    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock settings to have both keys
    with patch.object(settings, 'anthropic_api_key', 'test-claude-key'), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('src.agents.main_agent.ChatAnthropic') as mock_anthropic, \
         patch('src.agents.main_agent.ChatOpenAI') as mock_openai:

        # Mock Claude to fail
        mock_anthropic.side_effect = Exception("Claude initialization failed")

        # Mock the OpenAI client
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm

        # Create agent - should fall back to GPT-4
        agent = PaygentAgent(
            db=mock_db,
            session_id="test-session-id",
            llm_model="anthropic/claude-sonnet-4"
        )

        # Verify that Claude was attempted first
        mock_anthropic.assert_called_once_with(
            model="claude-sonnet-4",
            temperature=0.1,
            max_tokens=4000,
            api_key="test-claude-key",
        )

        # Verify that OpenAI was used as fallback
        mock_openai.assert_called_once_with(
            model="gpt-4",
            temperature=0.1,
            max_tokens=4000,
            api_key="test-openai-key",
        )

        # Verify the agent was created with the GPT-4 LLM
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_fallback_when_no_api_keys():
    """Test that agent raises error when no API keys are available."""

    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock settings with no API keys
    with patch.object(settings, 'anthropic_api_key', None), \
         patch.object(settings, 'openai_api_key', None):

        # Create agent - should raise ValueError
        with pytest.raises(ValueError, match="Unable to initialize any LLM"):
            PaygentAgent(
                db=mock_db,
                session_id="test-session-id",
                llm_model="anthropic/claude-sonnet-4"
            )


@pytest.mark.asyncio
async def test_agent_uses_claude_when_available():
    """Test that agent uses Claude when available and requested."""

    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock settings to have Anthropic key
    with patch.object(settings, 'anthropic_api_key', 'test-claude-key'), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('src.agents.main_agent.ChatAnthropic') as mock_anthropic:

        # Mock the Anthropic client
        mock_llm = MagicMock()
        mock_anthropic.return_value = mock_llm

        # Create agent - should use Claude
        agent = PaygentAgent(
            db=mock_db,
            session_id="test-session-id",
            llm_model="anthropic/claude-sonnet-4"
        )

        # Verify that Claude was initialized
        mock_anthropic.assert_called_once_with(
            model="claude-sonnet-4",
            temperature=0.1,
            max_tokens=4000,
            api_key="test-claude-key",
        )

        # Verify the agent was created with the Claude LLM
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_uses_gpt4_when_specifically_requested():
    """Test that agent uses GPT-4 when specifically requested."""

    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock settings to have OpenAI key
    with patch.object(settings, 'anthropic_api_key', None), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('src.agents.main_agent.ChatOpenAI') as mock_openai:

        # Mock the OpenAI client
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm

        # Create agent with GPT-4 model
        agent = PaygentAgent(
            db=mock_db,
            session_id="test-session-id",
            llm_model="openai/gpt-4"
        )

        # Verify that OpenAI was initialized
        mock_openai.assert_called_once_with(
            model="gpt-4",
            temperature=0.1,
            max_tokens=4000,
            api_key="test-openai-key",
        )

        # Verify the agent was created with the GPT-4 LLM
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_mcp_adapter_integration_with_fallback():
    """Test that MCP adapter works with both Claude and GPT-4 fallback."""

    # Mock database session
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock settings with no Anthropic key (force fallback to GPT-4)
    with patch.object(settings, 'anthropic_api_key', None), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('src.agents.main_agent.ChatOpenAI') as mock_openai, \
         patch('src.services.mcp_adapter.get_mcp_adapter') as mock_get_adapter:

        # Mock the OpenAI client
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm

        # Mock the MCP adapter
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        # Create agent - should fall back to GPT-4
        agent = PaygentAgent(
            db=mock_db,
            session_id="test-session-id",
            llm_model="anthropic/claude-sonnet-4"  # Requesting Claude but no key
        )

        # Verify MCP adapter was initialized
        assert agent.mcp_adapter == mock_adapter

        # Verify the agent was created with the GPT-4 LLM
        assert agent.llm == mock_llm


if __name__ == "__main__":
    pytest.main([__file__, "-v"])