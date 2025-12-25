"""
Tests for the configuration module.

This module tests the Settings class and configuration loading functionality.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.core.config import Settings, get_settings


class TestSettings:
    """Test the Settings class and configuration loading."""

    def test_default_settings(self):
        """Test that default settings are properly initialized."""
        settings = Settings()

        assert settings.app_name == "Paygent"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.environment == "development"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_expiration_hours == 24
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:8000" in settings.cors_origins

    def test_production_environment(self):
        """Test production environment settings."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            settings = Settings()
            assert settings.environment == "production"
            assert settings.is_production is True

    def test_development_environment(self):
        """Test development environment settings."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings()
            assert settings.environment == "development"
            assert settings.is_production is False

    def test_cors_origins_parsing_string(self):
        """Test parsing CORS origins from comma-separated string."""
        test_origins = "https://example.com,https://api.example.com"
        settings = Settings(cors_origins=test_origins)

        assert len(settings.cors_origins) == 2
        assert "https://example.com" in settings.cors_origins
        assert "https://api.example.com" in settings.cors_origins

    def test_cors_origins_parsing_list(self):
        """Test parsing CORS origins from list."""
        test_origins = ["https://example.com", "https://api.example.com"]
        settings = Settings(cors_origins=test_origins)

        assert len(settings.cors_origins) == 2
        assert "https://example.com" in settings.cors_origins
        assert "https://api.example.com" in settings.cors_origins

    def test_cors_origins_empty_string(self):
        """Test that empty CORS origins string returns defaults."""
        settings = Settings(cors_origins="")
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:8000" in settings.cors_origins

    def test_database_url_postgresql(self):
        """Test PostgreSQL URL transformation."""
        postgres_url = "postgresql://user:pass@localhost/test"
        settings = Settings(database_url=postgres_url)

        assert settings.effective_database_url.startswith("postgresql+asyncpg://")

    def test_database_url_sqlite(self):
        """Test SQLite URL transformation."""
        sqlite_url = "sqlite:///test.db"
        settings = Settings(database_url=sqlite_url)

        assert settings.effective_database_url.startswith("sqlite+aiosqlite:///")

    def test_database_url_memory(self):
        """Test in-memory SQLite URL."""
        memory_url = "sqlite:///:memory:"
        settings = Settings(database_url=memory_url)

        assert settings.effective_database_url == "sqlite+aiosqlite:///:memory:"

    def test_redis_url_default(self):
        """Test default Redis URL."""
        settings = Settings()
        assert settings.effective_redis_url == "redis://localhost:6379"

    def test_redis_url_vercel_kv(self):
        """Test Vercel KV URL takes precedence."""
        kv_url = "redis://kv.example.com:6380"
        settings = Settings(kv_url=kv_url)
        assert settings.effective_redis_url == kv_url

    def test_invalid_database_url(self):
        """Test invalid database URL raises validation error."""
        with pytest.raises(ValidationError):
            Settings(database_url="invalid://url")

    def test_jwt_secret_validation(self):
        """Test JWT secret validation."""
        settings = Settings(jwt_secret="test-secret")
        assert settings.jwt_secret == "test-secret"

    def test_rate_limit_validation(self):
        """Test rate limit validation."""
        settings = Settings(rate_limit_requests_per_minute=1000)
        assert settings.rate_limit_requests_per_minute == 1000

    def test_agent_config_validation(self):
        """Test agent configuration validation."""
        settings = Settings(
            agent_max_iterations=100,
            agent_timeout_seconds=600,
            agent_default_budget_usd=500.0
        )

        assert settings.agent_max_iterations == 100
        assert settings.agent_timeout_seconds == 600
        assert settings.agent_default_budget_usd == 500.0

    def test_logging_config(self):
        """Test logging configuration."""
        settings = Settings(
            log_level="DEBUG",
            log_format="%(levelname)s - %(message)s"
        )

        assert settings.log_level == "DEBUG"
        assert settings.log_format == "%(levelname)s - %(message)s"

    def test_alert_config(self):
        """Test alert configuration."""
        webhook_url = "https://hooks.slack.com/webhooks/test"
        settings = Settings(
            alert_webhook_url=webhook_url,
            alert_enabled=True
        )

        assert settings.alert_webhook_url == webhook_url
        assert settings.alert_enabled is True

    def test_crypto_com_config(self):
        """Test Crypto.com configuration."""
        api_key = "test-crypto-com-api-key"
        mcp_url = "https://mcp.crypto.com"
        settings = Settings(
            crypto_com_api_key=api_key,
            crypto_com_mcp_url=mcp_url
        )

        assert settings.crypto_com_api_key == api_key
        assert settings.crypto_com_mcp_url == mcp_url

    def test_x402_config(self):
        """Test x402 configuration."""
        facilitator_url = "https://test.x402.com"
        settings = Settings(
            x402_facilitator_url=facilitator_url,
            x402_max_retries=5,
            x402_retry_delay_ms=2000
        )

        assert settings.x402_facilitator_url == facilitator_url
        assert settings.x402_max_retries == 5
        assert settings.x402_retry_delay_ms == 2000

    def test_wallet_config(self):
        """Test wallet configuration."""
        private_key = "0x" + "a" * 64
        wallet_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        settings = Settings(
            agent_wallet_private_key=private_key,
            default_wallet_address=wallet_address,
            default_daily_limit_usd=500.0
        )

        assert settings.agent_wallet_private_key == private_key
        assert settings.default_wallet_address == wallet_address
        assert settings.default_daily_limit_usd == 500.0

    @pytest.mark.asyncio
    async def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
        assert settings1.app_name == settings2.app_name

    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        test_env = {
            "APP_NAME": "TestApp",
            "DEBUG": "true",
            "JWT_SECRET": "test-secret-key",
            "CORS_ORIGINS": "https://test.com,https://api.test.com"
        }

        with patch.dict(os.environ, test_env):
            settings = Settings()

            assert settings.app_name == "TestApp"
            assert settings.debug is True
            assert settings.jwt_secret == "test-secret-key"
            assert len(settings.cors_origins) == 2
            assert "https://test.com" in settings.cors_origins
            assert "https://api.test.com" in settings.cors_origins

    def test_postgres_url_override(self):
        """Test PostgreSQL URL environment variable override."""
        postgres_url = "postgresql://user:pass@prod-db:5432/prod"
        with patch.dict(os.environ, {"POSTGRES_URL": postgres_url}):
            settings = Settings()
            assert settings.effective_database_url == postgres_url

    def test_kv_url_override(self):
        """Test KV URL environment variable override."""
        kv_url = "redis://prod-kv:6380"
        with patch.dict(os.environ, {"KV_URL": kv_url}):
            settings = Settings()
            assert settings.effective_redis_url == kv_url

    def test_invalid_cors_origins_format(self):
        """Test invalid CORS origins format handling."""
        # Should handle malformed input gracefully
        settings = Settings(cors_origins="not-a-url,")
        # Should still include defaults
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:8000" in settings.cors_origins

    def test_wallet_address_validation(self):
        """Test wallet address format validation."""
        # Valid address
        valid_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        settings = Settings(default_wallet_address=valid_address)
        assert settings.default_wallet_address == valid_address

    def test_daily_limit_validation(self):
        """Test daily limit validation."""
        settings = Settings(default_daily_limit_usd=0.0)
        assert settings.default_daily_limit_usd == 0.0

        settings = Settings(default_daily_limit_usd=10000.0)
        assert settings.default_daily_limit_usd == 10000.0

    def test_model_config(self):
        """Test Pydantic model configuration."""
        settings = Settings()

        # Test that extra fields are ignored (extra = "ignore")
        settings_dict = {
            "extra_field": "should_be_ignored",
            "another_extra": "also_ignored",
            "app_name": "ValidApp"
        }

        # This should not raise an error due to extra = "ignore"
        valid_settings = Settings(**settings_dict)
        assert valid_settings.app_name == "ValidApp"
        assert not hasattr(valid_settings, "extra_field")

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        test_env = {
            "app_name": "TestAppLower",
            "DEBUG": "True",
            "jwt_algorithm": "RS256"
        }

        with patch.dict(os.environ, test_env):
            settings = Settings()

            assert settings.app_name == "TestAppLower"
            assert settings.debug is True
            assert settings.jwt_algorithm == "RS256"
