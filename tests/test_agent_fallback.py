"""Test agent fallback to OpenAI GPT-4 when Claude is unavailable."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.main_agent import PaygentAgent
from src.core.config import settings


@pytest.mark.asyncio
async def test_agent_fallback_to_gpt4():
    """Test that agent falls back to GPT-4 when Claude is unavailable."""
    mock_db = AsyncMock(spec=AsyncSession)
    with patch.object(settings, 'anthropic_api_key', None), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('src.agents.main_agent.ChatOpenAI') as mock_openai:
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm
        agent = PaygentAgent(db=mock_db, session_id="test-session-id", llm_model="anthropic/claude-sonnet-4")
        mock_openai.assert_called_once_with(model="gpt-4", temperature=0.1, max_tokens=4000, api_key="test-openai-key")
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_fallback_when_claude_fails():
    """Test that agent falls back to GPT-4 when Claude initialization fails."""
    mock_db = AsyncMock(spec=AsyncSession)
    with patch.object(settings, 'anthropic_api_key', 'test-claude-key'), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('langchain_anthropic.ChatAnthropic') as mock_anthropic, \
         patch('src.agents.main_agent.ChatOpenAI') as mock_openai:
        mock_anthropic.side_effect = Exception("Claude initialization failed")
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm
        agent = PaygentAgent(db=mock_db, session_id="test-session-id", llm_model="anthropic/claude-sonnet-4")
        mock_anthropic.assert_called_once_with(model="claude-sonnet-4", temperature=0.1, max_tokens=4000, api_key="test-claude-key")
        mock_openai.assert_called_once_with(model="gpt-4", temperature=0.1, max_tokens=4000, api_key="test-openai-key")
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_fallback_when_no_api_keys():
    """Test that agent raises error when no API keys are available."""
    mock_db = AsyncMock(spec=AsyncSession)
    with patch.object(settings, 'anthropic_api_key', None), \
         patch.object(settings, 'openai_api_key', None):
        with pytest.raises(ValueError, match="Unable to initialize any LLM"):
            PaygentAgent(db=mock_db, session_id="test-session-id", llm_model="anthropic/claude-sonnet-4")


@pytest.mark.asyncio
async def test_agent_uses_claude_when_available():
    """Test that agent uses Claude when available and requested."""
    mock_db = AsyncMock(spec=AsyncSession)
    with patch.object(settings, 'anthropic_api_key', 'test-claude-key'), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('langchain_anthropic.ChatAnthropic') as mock_anthropic:
        mock_llm = MagicMock()
        mock_anthropic.return_value = mock_llm
        agent = PaygentAgent(db=mock_db, session_id="test-session-id", llm_model="anthropic/claude-sonnet-4")
        mock_anthropic.assert_called_once_with(model="claude-sonnet-4", temperature=0.1, max_tokens=4000, api_key="test-claude-key")
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_uses_gpt4_when_specifically_requested():
    """Test that agent uses GPT-4 when specifically requested."""
    mock_db = AsyncMock(spec=AsyncSession)
    with patch.object(settings, 'anthropic_api_key', None), \
         patch.object(settings, 'openai_api_key', 'test-openai-key'), \
         patch('src.agents.main_agent.ChatOpenAI') as mock_openai:
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm
        agent = PaygentAgent(db=mock_db, session_id="test-session-id", llm_model="openai/gpt-4")
        mock_openai.assert_called_once_with(model="gpt-4", temperature=0.1, max_tokens=4000, api_key="test-openai-key")
        assert agent.llm == mock_llm


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
