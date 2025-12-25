"""
Centralized error handling and safe error messages.

This module provides utilities for handling errors safely without leaking
sensitive information like stack traces, database details, or internal
implementation details in production environments.
"""
import logging
import re
import traceback
from typing import Any

from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import settings
from src.core.security import sanitize
from src.services.alerting_service import (
    AlertType,
    send_critical_alert,
)

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error: str
    detail: str | None = None


class SafeException(Exception):
    """Base exception for safe errors that can be shown to users."""

    def __init__(self, message: str, detail: str | None = None):
        """
        Initialize the safe exception.

        Args:
            message: User-friendly error message
            detail: Optional additional details
        """
        self.message = message
        self.detail = detail
        super().__init__(message)


class PaymentError(SafeException):
    """Exception for payment-related errors."""

    pass


class ServiceNotFoundError(SafeException):
    """Exception when a service is not found."""

    pass


class InsufficientBalanceError(SafeException):
    """Exception for insufficient balance errors."""

    pass


class DailyLimitExceededError(SafeException):
    """Exception for daily spending limit errors."""

    pass


class PaygentError(Exception):
    """Base exception for Paygent application errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Initialize the Paygent error.

        Args:
            message: Error message
            details: Optional additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


def create_safe_error_message(
    error: Exception, include_detail: bool = False
) -> str:
    """
    Create a safe error message that doesn't leak sensitive information.

    Args:
        error: The exception that occurred
        include_detail: Whether to include non-sensitive detail

    Returns:
        A safe error message for the user
    """
    # In debug mode, show full error
    if settings.debug:
        return str(error)

    # In production, show generic messages
    error_type = type(error).__name__

    # Map specific error types to safe messages
    safe_messages = {
        "ValueError": "Invalid input provided",
        "ValidationError": "Request validation failed",
        "AuthenticationError": "Authentication failed",
        "AuthorizationError": "Insufficient permissions",
        "NotFoundError": "Resource not found",
        "ConnectionError": "Service unavailable",
        "TimeoutError": "Request timed out",
        "HTTPException": "Request processing error",
        "SQLAlchemyError": "Database error occurred",
        "RedisError": "Cache service error",
    }

    # Return safe message or generic fallback
    return safe_messages.get(error_type, "An error occurred while processing your request")


def create_error_response(
    status_code: int, message: str, detail: str | None = None
) -> JSONResponse:
    """
    Create a standardized JSON error response.

    Args:
        status_code: HTTP status code
        message: Main error message
        detail: Optional additional detail

    Returns:
        JSONResponse with error information
    """
    error_response = ErrorResponse(
        error=message, detail=detail if settings.debug else None
    )

    # Log the full error for debugging
    logger.error(f"Error {status_code}: {message} - {detail}")

    return JSONResponse(
        status_code=status_code, content=error_response.model_dump()
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """
    Handle HTTPException globally and sanitize error messages.

    Args:
        request: The request that caused the exception
        exc: The HTTPException that was raised

    Returns:
        JSONResponse with sanitized error information
    """
    # Sanitize error detail to prevent information leakage
    safe_detail = None
    if exc.detail:
        if settings.debug:
            safe_detail = str(exc.detail)
        else:
            # Check if detail looks like it might contain sensitive info
            detail_str = str(exc.detail)
            safe_detail = create_safe_error_message(Exception(detail_str))

    return create_error_response(
        status_code=exc.status_code,
        message=create_safe_error_message(exc),
        detail=safe_detail,
    )


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle all other exceptions globally.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse with sanitized error information
    """
    # Log full exception for debugging
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Send critical alert for unhandled exceptions
    if settings.alert_enabled:
        send_critical_alert(
            alert_type=AlertType.EXTERNAL_SERVICE_FAILURE,
            message=f"Unhandled exception: {type(exc).__name__}",
            details={
                "error": str(exc),
                "path": str(request.url.path),
                "method": request.method,
            },
            correlation_id=getattr(exc, "correlation_id", None),
        )

    # Return generic error in production
    if settings.debug:
        # In debug mode, show full traceback
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        # In production, don't leak implementation details
        detail = None

    return create_error_response(
        status_code=500,
        message="Internal server error",
        detail=detail,
    )


def validate_command_input(command: str) -> str:
    """
    Validate and sanitize user command input to prevent injection attacks.

    Args:
        command: Raw user command string

    Returns:
        Sanitized command string

    Raises:
        ValueError: If command contains potentially dangerous content
    """
    if not command or not command.strip():
        raise ValueError("Command cannot be empty")

    # Check for shell injection patterns
    dangerous_patterns = [
        ";",     # Command separator
        "&&",    # Logical AND
        "||",    # Logical OR
        "&",     # Background command
        "|",     # Pipe
        ">",     # Output redirection
        ">>",    # Append redirection
        "<",     # Input redirection
        "`",     # Command substitution
        "$(",    # Command substitution
        "${",    # Parameter expansion
        "\n",    # Newline injection
        "\r",    # Carriage return
        "\t",    # Tab character
        "\\",    # Escape character
        "*",     # Glob pattern (can be dangerous in some contexts)
        "?",     # Glob pattern (can be dangerous in some contexts)
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern in command:
            raise ValueError(
                "Command contains invalid characters. "
                "Please provide a natural language command without special characters."
            )

    # Check for SQL injection patterns - be very conservative for natural language

    # Check for obvious SQL injection patterns (quotes with SQL keywords)
    if re.search(r'["\']\s*(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+["\']', command_lower):
        raise ValueError("Command contains potential SQL injection patterns. Please provide a natural language command.")

    # Check for SQL keywords followed by common SQL syntax patterns
    sql_keywords = r'\b(select|insert|update|delete|drop|create|alter|exec|execute)\b'
    if re.search(f'{sql_keywords}\\s+\\w+\\s+from\\b', command_lower):
        raise ValueError("Command contains potential SQL injection patterns. Please provide a natural language command.")

    # Check for SQL UNION patterns
    if re.search(r'union\s+select\b', command_lower):
        raise ValueError("Command contains potential SQL injection patterns. Please provide a natural language command.")

    # Check for script injection attempts
    script_keywords = [
        "javascript:", "data:", "vbscript:", "file://",
        "http:", "https:", "ftp:", "mailto:",  # Restrict common protocols
    ]
    for keyword in script_keywords:
        if keyword in command_lower:
            # Allow http/https for legitimate URLs, but restrict others
            if keyword in ["http:", "https:"]:
                # Basic URL validation - this is a simple check
                if not re.match(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', command_lower):
                    raise ValueError("Command contains invalid URL format")
            else:
                raise ValueError("Command contains invalid content")

    # Check for Python injection patterns - only flag obvious attempts
    python_injection_patterns = [
        "__import__", "globals", "locals"
    ]
    for pattern in python_injection_patterns:
        if pattern in command_lower:
            raise ValueError("Command contains potentially dangerous keywords")

    # Check for exec/eval only when they look like function calls
    if re.search(r'\b(exec|eval)\s*\(', command_lower):
        raise ValueError("Command contains potentially dangerous keywords")

    # Check for file system access patterns - be more permissive for natural language
    # Only block if it looks like actual file access attempts
    if re.search(r'["\'](\.\./|\./|/[a-zA-Z0-9_/-]+)["\']', command):
        raise ValueError("Command contains invalid file path patterns")

    # Length limit to prevent DoS
    if len(command) > 10000:
        raise ValueError("Command is too long. Maximum 10,000 characters.")

    return command.strip()


def sanitize_dict_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize a dictionary for logging by removing sensitive fields.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary safe for logging
    """
    return sanitize(data)
