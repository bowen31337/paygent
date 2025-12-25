"""
Security utilities for sensitive data protection.

This module provides utilities to ensure sensitive information like private keys,
API keys, and passwords are never exposed in logs or error messages.
"""

import re
import logging
from typing import Any, Optional, Set, Literal
from functools import lru_cache

logger = logging.getLogger(__name__)

# Patterns to detect and redact sensitive information
SENSITIVE_PATTERNS = [
    # Private keys (0x followed by 64 hex characters)
    (r'0x[a-fA-F0-9]{64}', '0x*************REDACTED*************'),
    # API keys that look like: sk-ant-... (more permissive pattern)
    (r'sk-ant-[a-zA-Z0-9\-_]{10,}', 'sk-ant-********REDACTED'),
    # OpenAI API keys
    (r'sk-[a-zA-Z0-9]{20,}', 'sk-************************************'),
    # Generic API keys in headers or config
    (r'["\']?(api[_-]?key|api[_-]?secret|private[_-]?key|secret[_-]?key|password|token)["\']?\s*[:=]\s*["\']?[^"\']+\s*["\']?', '***REDACTED***'),
    # Bearer tokens
    (r'Bearer [a-zA-Z0-9\-._~+/]+=*', 'Bearer ***REDACTED***'),
    # Authorization headers with tokens
    (r'Authorization: [^\s]+', 'Authorization: ***REDACTED***'),
]


class RedactingFormatter(logging.Formatter):
    """
    Custom logging formatter that redacts sensitive information.

    This formatter intercepts log messages and replaces sensitive patterns
    with redacted placeholders before the log is written.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: Literal['%', '{', '$'] = '%'
    ) -> None:
        """Initialize the redacting formatter."""
        super().__init__(fmt, datefmt, style)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with sensitive data redacted.

        Args:
            record: The log record to format

        Returns:
            Formatted log message with sensitive data redacted
        """
        # First apply standard formatting
        message = super().format(record)

        # Apply redaction patterns
        for pattern, replacement in SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

        return message


def redact_dict(data: dict[str, Any], additional_keys: Optional[set[str]] = None) -> dict[str, Any]:
    """
    Redact sensitive values from a dictionary.

    Args:
        data: Dictionary to redact
        additional_keys: Additional keys to redact beyond the default list

    Returns:
        Dictionary with sensitive values redacted
    """
    if not isinstance(data, dict):
        return data

    sensitive_keys = {
        'private_key', 'privatekey', 'private-key',
        'api_key', 'apikey', 'api-key',
        'api_secret', 'apisecret', 'api-secret',
        'secret', 'password', 'token',
        'authorization', 'auth',
        'credentials', 'credential',
    }

    if additional_keys:
        sensitive_keys.update(additional_keys)

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            # Redact the entire value
            if isinstance(value, str) and len(value) > 10:
                # Show first 4 and last 4 chars for debugging
                redacted[key] = f"{value[:4]}...{value[-4:]} ***REDACTED***"
            else:
                redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            # Recursively redact nested dictionaries
            redacted[key] = redact_dict(value, additional_keys)
        elif isinstance(value, list):
            # Redact items in lists
            redacted[key] = [
                redact_dict(item, additional_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value

    return redacted


def safe_log_dict(
    logger: logging.Logger,
    level: int,
    data: dict[str, Any],
    additional_keys: Optional[set[str]] = None
) -> None:
    """
    Safely log a dictionary with sensitive data redacted.

    Args:
        logger: Logger instance to use
        level: Logging level (e.g., logging.INFO, logging.ERROR)
        data: Dictionary to log
        additional_keys: Additional keys to redact
    """
    redacted = redact_dict(data, additional_keys)
    logger.log(level, str(redacted))


def is_safe_for_logging(value: str) -> bool:
    """
    Check if a string value is safe to log without redaction.

    Args:
        value: String value to check

    Returns:
        True if safe, False if contains sensitive patterns
    """
    for pattern, _ in SENSITIVE_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return False
    return True


def redact_string(value: str) -> str:
    """
    Redact sensitive information from a string.

    Args:
        value: String to redact

    Returns:
        String with sensitive information redacted
    """
    for pattern, replacement in SENSITIVE_PATTERNS:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    return value


def configure_secure_logging() -> logging.Logger:
    """
    Configure the root logger to use secure redacting formatters.

    This should be called during application startup to ensure all logs
    have sensitive data redacted.

    Returns:
        The configured root logger
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with redacting formatter
    console_handler = logging.StreamHandler()

    # Use a standard format with redaction
    formatter = RedactingFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger


# Convenience function for quick redaction
def sanitize(data: Any) -> Any:
    """
    Sanitize data for logging by redacting sensitive information.

    Args:
        data: Any data structure to sanitize

    Returns:
        Sanitized version of the data
    """
    if isinstance(data, str):
        return redact_string(data)
    elif isinstance(data, dict):
        return redact_dict(data)
    elif isinstance(data, list):
        return [sanitize(item) for item in data]
    else:
        return data


# =============================================================================
# Tool Allowlist Security
# =============================================================================

class ToolAllowlistError(Exception):
    """Raised when a tool is not in the allowlist."""
    pass


class ToolAllowlist:
    """
    Manages a allowlist of permitted tools for agent execution.

    This provides security by restricting which tools an agent can invoke,
    preventing unauthorized or dangerous operations.
    """

    # Default allowlist - all safe tools
    DEFAULT_ALLOWED_TOOLS: Set[str] = {
        "check_balance",
        "discover_services",
        "x402_payment",
        "swap_tokens",
        "vvs_quote",
        "vvs_liquidity",
        "vvs_farm",
        "transfer_tokens",
        "get_approval",
    }

    # Tools that are always blocked (dangerous operations)
    BLOCKED_TOOLS: Set[str] = {
        "exec",
        "eval",
        "system",
        "subprocess",
        "os.system",
        "os.exec",
        "os.popen",
        "shell",
        "bash",
        "sh",
        "python",
        "javascript",
        "execute_sql",
        "drop_table",
        "delete_all",
        "transfer_all",
        "withdraw_all",
    }

    def __init__(self, allowed_tools: Optional[Set[str]] = None) -> None:
        """
        Initialize the tool allowlist.

        Args:
            allowed_tools: Set of allowed tool names. If None, uses DEFAULT_ALLOWED_TOOLS.
        """
        if allowed_tools is None:
            self.allowed_tools = self.DEFAULT_ALLOWED_TOOLS.copy()
        else:
            self.allowed_tools = allowed_tools.copy()

        logger.info(f"ToolAllowlist initialized with {len(self.allowed_tools)} allowed tools")

    def is_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed to be executed.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if the tool is allowed, False otherwise
        """
        # Always block dangerous tools
        if tool_name in self.BLOCKED_TOOLS:
            logger.warning(f"Tool '{tool_name}' is in BLOCKED_TOOLS - denied")
            return False

        # Check if tool is in allowlist
        allowed = tool_name in self.allowed_tools

        if not allowed:
            logger.warning(f"Tool '{tool_name}' not in allowlist - denied")

        return allowed

    def validate_tool_call(self, tool_name: str, tool_args: dict[str, Any]) -> None:
        """
        Validate a tool call, raising an exception if not allowed.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments being passed to the tool

        Raises:
            ToolAllowlistError: If the tool is not allowed
        """
        if not self.is_allowed(tool_name):
            raise ToolAllowlistError(
                f"Tool '{tool_name}' is not in the allowlist and cannot be executed. "
                f"Allowed tools: {sorted(self.allowed_tools)}"
            )

        logger.info(f"Tool call validated: {tool_name}")

    def add_tool(self, tool_name: str) -> None:
        """Add a tool to the allowlist."""
        self.allowed_tools.add(tool_name)
        logger.info(f"Added tool '{tool_name}' to allowlist")

    def remove_tool(self, tool_name: str) -> None:
        """Remove a tool from the allowlist."""
        if tool_name in self.allowed_tools:
            self.allowed_tools.remove(tool_name)
            logger.info(f"Removed tool '{tool_name}' from allowlist")

    def get_allowed_tools(self) -> Set[str]:
        """Get the current set of allowed tools."""
        return self.allowed_tools.copy()


# Global tool allowlist instance
_tool_allowlist: Optional[ToolAllowlist] = None


def get_tool_allowlist() -> ToolAllowlist:
    """
    Get the global tool allowlist instance.

    Returns:
        ToolAllowlist instance
    """
    global _tool_allowlist
    if _tool_allowlist is None:
        _tool_allowlist = ToolAllowlist()
    return _tool_allowlist


def configure_tool_allowlist(allowed_tools: Set[str]) -> None:
    """
    Configure the global tool allowlist.

    Args:
        allowed_tools: Set of allowed tool names
    """
    global _tool_allowlist
    _tool_allowlist = ToolAllowlist(allowed_tools)
    logger.info(f"Configured global tool allowlist with {len(allowed_tools)} tools")


def is_tool_allowed(tool_name: str) -> bool:
    """
    Check if a tool is allowed using the global allowlist.

    Args:
        tool_name: Name of the tool to check

    Returns:
        True if allowed, False otherwise
    """
    return get_tool_allowlist().is_allowed(tool_name)


def validate_tool_call(tool_name: str, tool_args: dict[str, Any]) -> None:
    """
    Validate a tool call using the global allowlist.

    Args:
        tool_name: Name of the tool
        tool_args: Arguments for the tool

    Raises:
        ToolAllowlistError: If the tool is not allowed
    """
    get_tool_allowlist().validate_tool_call(tool_name, tool_args)
