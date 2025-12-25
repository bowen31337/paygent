"""Test LLM fallback functionality.

Tests that the agent properly falls back from Claude to GPT-4 when Claude is unavailable.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.main_agent import PaygentAgent


@pytest.mark.asyncio
async def test_agent_fallback_to_openai_when_claude_unavailable():
    """Test that agent falls back to OpenAI when Anthropic API fails."""
    # Create a mock database session
    mock_db = AsyncMock()

    # Mock the ChatAnthropic import to fail
    with patch("src.agents.main_agent.ChatAnthropic", side_effect=ImportError("No module named 'langchain_anthropic'")):
        # Mock ChatOpenAI to succeed
        with patch("src.agents.main_agent.ChatOpenAI") as mock_openai:
            mock_llm = MagicMock()
            mock_openai.return_value = mock_llm

            # Create agent with Anthropic model (should fall back to OpenAI)
            agent = PaygentAgent(
                db=mock_db,
                session_id="test-session-id",
                llm_model="anthropic/claude-sonnet-4",
            )

            # Verify OpenAI was initialized
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["temperature"] == 0.1
            assert call_kwargs["max_tokens"] == 4000

            # Verify the agent's LLM is the OpenAI mock
            assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_uses_claude_when_available():
    """Test that agent uses Claude when it's available."""
    mock_db = AsyncMock()

    # Mock ChatAnthropic to succeed
    with patch("src.agents.main_agent.ChatAnthropic") as mock_anthropic:
        mock_llm = MagicMock()
        mock_anthropic.return_value = mock_llm

        # Create agent with Anthropic model
        agent = PaygentAgent(
            db=mock_db,
            session_id="test-session-id",
            llm_model="anthropic/claude-sonnet-4",
        )

        # Verify Anthropic was initialized
        mock_anthropic.assert_called_once()
        call_kwargs = mock_anthropic.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4"

        # Verify the agent's LLM is the Anthropic mock
        assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_agent_raises_error_when_no_llm_available():
    """Test that agent raises error when both LLMs are unavailable."""
    mock_db = AsyncMock()

    # Mock both ChatAnthropic and ChatOpenAI to fail
    with patch("src.agents.main_agent.ChatAnthropic", side_effect=ImportError("Not available")):
        with patch("src.agents.main_agent.ChatOpenAI", side_effect=ImportError("Not available")):
            # Try to create agent - should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                PaygentAgent(
                    db=mock_db,
                    session_id="test-session-id",
                    llm_model="anthropic/claude-sonnet-4",
                )

            # Verify error message
            assert "Unable to initialize any LLM" in str(exc_info.value)


@pytest.mark.asyncio
async def test_agent_fallback_on_api_key_missing():
    """Test that agent falls back when Anthropic API key is missing."""
    from src.core.config import settings

    mock_db = AsyncMock()

    # Temporarily remove Anthropic API key
    original_key = settings.anthropic_api_key
    settings.anthropic_api_key = None

    try:
        # Mock ChatOpenAI to succeed
        with patch("src.agents.main_agent.ChatOpenAI") as mock_openai:
            mock_llm = MagicMock()
            mock_openai.return_value = mock_llm

            # Create agent - should skip Anthropic and use OpenAI
            agent = PaygentAgent(
                db=mock_db,
                session_id="test-session-id",
                llm_model="anthropic/claude-sonnet-4",
            )

            # Verify OpenAI was used
            mock_openai.assert_called_once()
            assert agent.llm == mock_llm
    finally:
        # Restore original API key
        settings.anthropic_api_key = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
