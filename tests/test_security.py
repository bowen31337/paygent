"""
Tests for security utilities, particularly private key protection in logs.
"""

import logging
from io import StringIO

from src.core.security import (
    RedactingFormatter,
    is_safe_for_logging,
    redact_dict,
    redact_string,
    safe_log_dict,
    sanitize,
)


class TestRedactingFormatter:
    """Tests for the RedactingFormatter logging formatter."""

    def test_redact_private_key_in_log(self):
        """Test that private keys are redacted in log messages."""
        formatter = RedactingFormatter('%(message)s')
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Private key: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "0x1234567890abcdef" not in formatted
        assert "***REDACTED***" in formatted

    def test_redact_api_key_in_log(self):
        """Test that API keys are redacted in log messages."""
        formatter = RedactingFormatter('%(message)s')
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="API Key: sk-ant-api123-456789abcdef",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "sk-ant-api123-456789abcdef" not in formatted
        assert "REDACTED" in formatted

    def test_redact_bearer_token(self):
        """Test that Bearer tokens are redacted."""
        formatter = RedactingFormatter('%(message)s')
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in formatted
        assert "***REDACTED***" in formatted

    def test_safe_message_passes_through(self):
        """Test that safe messages are not altered."""
        formatter = RedactingFormatter('%(message)s')
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processing payment of 100 USDC",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert formatted == "Processing payment of 100 USDC"


class TestRedactDict:
    """Tests for dictionary redaction."""

    def test_redact_private_key_in_dict(self):
        """Test that private keys are redacted in dictionaries."""
        data = {
            "address": "0x1234567890123456789012345678901234567890",
            "private_key": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "amount": 100,
        }

        redacted = redact_dict(data)
        assert redacted["address"] == data["address"]
        assert redacted["amount"] == data["amount"]
        assert "***REDACTED***" in redacted["private_key"]
        assert data["private_key"] not in redacted["private_key"]

    def test_redact_multiple_sensitive_fields(self):
        """Test redaction of multiple sensitive fields."""
        data = {
            "api_key": "sk-1234567890",
            "secret": "my-secret-password",
            "token": "auth-token-123",
            "normal_field": "safe-value",
        }

        redacted = redact_dict(data)
        assert "***REDACTED***" in redacted["api_key"]
        assert "***REDACTED***" in redacted["secret"]
        assert "***REDACTED***" in redacted["token"]
        assert redacted["normal_field"] == "safe-value"

    def test_redact_nested_dict(self):
        """Test redaction of nested dictionaries."""
        data = {
            "user": {
                "name": "Alice",
                "config": {  # Changed from "credentials" to avoid auto-redaction
                    "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "api_key": "sk-test-key",
                },
            },
        }

        redacted = redact_dict(data)
        # Check the nested dict was returned as a dict
        assert isinstance(redacted["user"], dict)
        assert isinstance(redacted["user"]["config"], dict)
        # Check redaction happened
        assert "REDACTED" in redacted["user"]["config"]["private_key"]
        assert "REDACTED" in redacted["user"]["config"]["api_key"]
        assert redacted["user"]["name"] == "Alice"

    def test_redact_dict_with_custom_keys(self):
        """Test redaction with additional custom keys."""
        data = {
            "custom_sensitive": "secret-value",
            "normal_field": "safe-value",
        }

        redacted = redact_dict(data, additional_keys=["custom_sensitive"])
        assert "***REDACTED***" in redacted["custom_sensitive"]
        assert redacted["normal_field"] == "safe-value"

    def test_show_partial_value_for_long_strings(self):
        """Test that long sensitive values show first and last few characters."""
        data = {
            "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        }

        redacted = redact_dict(data)
        # Should show first 4 and last 4 chars
        assert "0x12" in redacted["private_key"]
        assert "cdef" in redacted["private_key"]
        assert "REDACTED" in redacted["private_key"]


class TestRedactString:
    """Tests for string redaction."""

    def test_redact_private_key_string(self):
        """Test redacting private key from string."""
        private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        redacted = redact_string(f"My key is {private_key}")

        assert private_key not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_api_key_string(self):
        """Test redacting API key from string."""
        api_key = "sk-ant-api1234567890"
        redacted = redact_string(f"Using API key: {api_key}")

        assert api_key not in redacted
        assert "sk-ant-********REDACTED" in redacted

    def test_redact_authorization_header(self):
        """Test redacting Authorization header."""
        header = "Authorization: Bearer my-secret-token"
        redacted = redact_string(header)

        assert "my-secret-token" not in redacted
        assert "***REDACTED***" in redacted


class TestIsSafeForLogging:
    """Tests for safety checking."""

    def test_safe_string(self):
        """Test that safe strings return True."""
        assert is_safe_for_logging("Processing payment of 100 USDC")
        assert is_safe_for_logging("User alice@example.com logged in")

    def test_unsafe_private_key(self):
        """Test that strings with private keys return False."""
        assert not is_safe_for_logging(
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

    def test_unsafe_api_key(self):
        """Test that strings with API keys return False."""
        assert not is_safe_for_logging("sk-ant-api1234567890")
        assert not is_safe_for_logging("Authorization: Bearer token123")


class TestSanitize:
    """Tests for the sanitize utility function."""

    def test_sanitize_string(self):
        """Test sanitizing a string."""
        private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        sanitized = sanitize(f"Key: {private_key}")

        assert private_key not in sanitized
        assert "***REDACTED***" in sanitized

    def test_sanitize_dict(self):
        """Test sanitizing a dictionary."""
        data = {
            "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "amount": 100,
        }
        sanitized = sanitize(data)

        assert "***REDACTED***" in sanitized["private_key"]
        assert sanitized["amount"] == 100

    def test_sanitize_list(self):
        """Test sanitizing a list."""
        data = [
            "safe-value",
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        ]
        sanitized = sanitize(data)

        assert sanitized[0] == "safe-value"
        assert "***REDACTED***" in sanitized[1]

    def test_sanitize_other_types(self):
        """Test that other types pass through unchanged."""
        assert sanitize(123) == 123
        assert sanitize(45.67) == 45.67
        assert sanitize(True) is True


class TestSafeLogDict:
    """Tests for safe dictionary logging."""

    def test_safe_log_dict_with_sensitive_data(self, caplog):
        """Test logging dictionary with sensitive data."""
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)

        data = {
            "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "amount": 100,
        }

        with caplog.at_level(logging.DEBUG):
            safe_log_dict(logger, logging.INFO, data)

        # Check that the log doesn't contain the private key
        for record in caplog.records:
            assert "0x1234567890abcdef" not in record.message
            assert "***REDACTED***" in record.message

    def test_safe_log_dict_with_additional_keys(self, caplog):
        """Test logging with additional sensitive keys."""
        logger = logging.getLogger("test_logger2")
        logger.setLevel(logging.DEBUG)

        data = {
            "custom_secret": "secret-value",
            "normal": "value",
        }

        with caplog.at_level(logging.DEBUG):
            safe_log_dict(logger, logging.INFO, data, additional_keys=["custom_secret"])

        # Check that custom_secret was redacted
        for record in caplog.records:
            assert "secret-value" not in record.message
            assert "***REDACTED***" in record.message


class TestIntegration:
    """Integration tests for security features."""

    def test_end_to_end_private_key_protection(self, caplog):
        """Test that private keys are protected throughout logging pipeline."""
        # Configure logger with redacting formatter
        logger = logging.getLogger("integration_test")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(RedactingFormatter('%(message)s'))
        logger.addHandler(handler)

        private_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

        # Log private key directly
        logger.error(f"Failed to initialize with key: {private_key}")

        # Check handler output
        stream = handler.stream
        log_output = stream.getvalue()

        assert private_key not in log_output
        assert "***REDACTED***" in log_output

    def test_multiple_patterns_in_single_message(self):
        """Test redaction of multiple sensitive patterns in one message."""
        formatter = RedactingFormatter('%(message)s')
        message = (
            "Config: private_key=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef, "
            "api_key=sk-ant-api123, "
            "token=auth-token-456"
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Check all patterns are redacted
        assert "0x1234567890abcdef" not in formatted
        assert "sk-ant-api123" not in formatted
        assert "auth-token-456" not in formatted
        # Should have multiple REDACTED markers
        assert "REDACTED" in formatted
