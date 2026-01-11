"""
LLM client utilities.

Provides factory functions for creating LLM model configurations
compatible with deepagents create_deep_agent API.
"""

import logging
from typing import Any

from src.core.config import settings

logger = logging.getLogger(__name__)


def get_model_string(model: str = "anthropic/claude-sonnet-4") -> str:
    """
    Get a model string for use with create_deep_agent.

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4", "openai/gpt-4")

    Returns:
        Model string in deepagents format (e.g., "anthropic:claude-sonnet-4-20250514")
    """
    model_lower = model.lower()

    if "anthropic" in model_lower or "claude" in model_lower:
        return "anthropic:claude-sonnet-4-20250514"
    elif "openai" in model_lower or "gpt" in model_lower:
        return "openai:gpt-4"
    else:
        # Default to Anthropic Claude Sonnet 4
        logger.warning(f"Unknown model '{model}', defaulting to Claude Sonnet 4")
        return "anthropic:claude-sonnet-4-20250514"


def get_llm_config(
    model: str = "anthropic/claude-sonnet-4",
    temperature: float = 0.1,
    max_tokens: int = 4000,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """
    Get LLM configuration for use with deepagents.

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4", "openai/gpt-4")
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        api_key: Optional API key (uses settings if not provided)
        base_url: Optional custom base URL for API endpoint (uses settings if not provided)

    Returns:
        Configuration dict for deepagents
    """
    model_string = get_model_string(model)
    model_lower = model.lower()

    # Determine API key and base URL based on model type
    if "anthropic" in model_lower or "claude" in model_lower:
        if api_key is None:
            api_key = settings.anthropic_api_key
        if base_url is None:
            base_url = settings.anthropic_base_url
    elif "openai" in model_lower or "gpt" in model_lower:
        if api_key is None:
            api_key = settings.openai_api_key
        if base_url is None:
            base_url = settings.openai_base_url

    config = {
        "model": model_string,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "api_key": api_key,
    }

    # Only include base_url if it's set (allows using default endpoints)
    if base_url:
        config["base_url"] = base_url

    return config
