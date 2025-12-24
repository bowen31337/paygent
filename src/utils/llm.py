"""
LLM client utilities.

Provides factory functions for creating LLM instances.
"""

import logging
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_base import BaseChatModel

from src.core.config import settings

logger = logging.getLogger(__name__)


def get_llm_client(
    model: str = "anthropic/claude-sonnet-4",
    temperature: float = 0.1,
    max_tokens: int = 4000,
    api_key: Optional[str] = None,
) -> BaseChatModel:
    """
    Get an LLM client instance.

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4", "openai/gpt-4")
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        api_key: Optional API key (uses settings if not provided)

    Returns:
        Configured LLM instance
    """
    model_lower = model.lower()

    if "anthropic" in model_lower or "claude" in model_lower:
        return ChatAnthropic(
            model="claude-sonnet-4",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key or settings.anthropic_api_key,
        )
    elif "openai" in model_lower or "gpt" in model_lower:
        return ChatOpenAI(
            model="gpt-4",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key or settings.openai_api_key,
        )
    else:
        # Default to Anthropic
        logger.warning(f"Unknown model '{model}', defaulting to Claude Sonnet 4")
        return ChatAnthropic(
            model="claude-sonnet-4",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key or settings.anthropic_api_key,
        )
