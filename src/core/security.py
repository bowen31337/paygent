"""
Security utilities for sensitive data protection.

This module provides utilities to ensure sensitive information like private keys,
API keys, and passwords are never exposed in logs or error messages.
"""

import re
import logging
from typing import Any, Dict

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

    def __init__(self, fmt=None, datefmt=None, style='%'):
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


def redact_dict(data: Dict[str, Any], additional_keys: list = None) -> Dict[str, Any]:
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

    redacted = {}
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


def safe_log_dict(logger: logging.Logger, level: int, data: Dict[str, Any], additional_keys: list = None):
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


def configure_secure_logging():
    """
    Configure the root logger to use secure redacting formatters.

    This should be called during application startup to ensure all logs
    have sensitive data redacted.
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
