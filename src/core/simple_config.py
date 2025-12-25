"""
Simple Configuration Module for Paygent.

This module provides a simplified configuration system that doesn't rely on
pydantic, allowing the application to work when pydantic_core has issues.
"""

import os
from typing import Any


class SimpleSettings:
    """Simple configuration settings without pydantic dependency."""

    def __init__(self):
        """Initialize settings from environment variables."""
        # Application
        self.app_name = os.getenv("APP_NAME", "Paygent")
        self.app_version = os.getenv("APP_VERSION", "0.1.0")
        self.debug = os.getenv("DEBUG", "true").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Server
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))

        # Security
        self.jwt_secret = os.getenv("JWT_SECRET", "development-secret-change-in-production")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION", "24"))

        # CORS
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
        self.cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

        # LLM Configuration
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
        self.fallback_model = os.getenv("FALLBACK_MODEL", "gpt-4")

        # Cronos Blockchain
        self.cronos_rpc_url = os.getenv("CRONOS_RPC_URL", "https://evm-t3.cronos.org")
        self.cronos_chain_id = int(os.getenv("CRONOS_CHAIN_ID", "338"))
        self.cronos_testnet_rpc_url = os.getenv("CRONOS_TESTNET_RPC_URL", "https://evm-t3.cronos.org")
        self.cronos_testnet_chain_id = int(os.getenv("CRONOS_TESTNET_CHAIN_ID", "338"))

        # x402 Configuration
        self.x402_facilitator_url = os.getenv("X402_FACILITATOR_URL", "https://x402-facilitator.cronos.org")
        self.x402_max_retries = int(os.getenv("X402_MAX_RETRIES", "3"))
        self.x402_retry_delay_ms = int(os.getenv("X402_RETRY_DELAY_MS", "1000"))

        # Wallet Configuration
        self.agent_wallet_private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY")
        self.default_wallet_address = os.getenv("DEFAULT_WALLET_ADDRESS", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
        self.default_daily_limit_usd = float(os.getenv("DEFAULT_DAILY_LIMIT_USD", "1000.0"))

        # Database Configuration
        self.postgres_url = os.getenv("POSTGRES_URL")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./paygent.db")

        # Redis/KV Configuration
        self.kv_url = os.getenv("KV_URL")
        self.kv_rest_api_url = os.getenv("KV_REST_API_URL")
        self.kv_rest_api_token = os.getenv("KV_REST_API_TOKEN")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Vercel Blob
        self.blob_read_write_token = os.getenv("BLOB_READ_WRITE_TOKEN")

        # Crypto.com Integration
        self.crypto_com_api_key = os.getenv("CRYPTO_COM_API_KEY")
        self.crypto_com_mcp_url = os.getenv("CRYPTO_COM_MCP_URL", "https://mcp.crypto.com")

        # Rate Limiting
        self.rate_limit_requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100"))

        # Agent Configuration
        self.agent_max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "50"))
        self.agent_timeout_seconds = int(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))
        self.agent_default_budget_usd = float(os.getenv("AGENT_DEFAULT_BUDGET_USD", "100.0"))
        self.hitl_approval_threshold_usd = float(os.getenv("HITL_APPROVAL_THRESHOLD_USD", "10.0"))

        # Logging
        self.log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Alerting
        self.alert_webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        self.alert_enabled = os.getenv("ALERT_ENABLED", "true").lower() == "true"

    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL (Vercel Postgres or local)."""
        return self.postgres_url or self.database_url

    @property
    def effective_redis_url(self) -> str:
        """Get the effective Redis URL (Vercel KV or local)."""
        return self.kv_url or self.redis_url

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary for debugging."""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "debug": self.debug,
            "environment": self.environment,
            "log_level": self.log_level,
            "host": self.host,
            "port": self.port,
            "cors_origins": self.cors_origins,
            "default_model": self.default_model,
            "fallback_model": self.fallback_model,
            "cronos_rpc_url": self.cronos_rpc_url,
            "cronos_chain_id": self.cronos_chain_id,
            "x402_facilitator_url": self.x402_facilitator_url,
            "database_url": self.effective_database_url,
            "redis_url": self.effective_redis_url,
            "is_production": self.is_production,
        }

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if not self.anthropic_api_key:
            issues.append("ANTHROPIC_API_KEY not set - Claude will not work")

        if not self.openai_api_key:
            issues.append("OPENAI_API_KEY not set - fallback to GPT-4 will not work")

        if not self.cronos_rpc_url:
            issues.append("CRONOS_RPC_URL not set - blockchain operations will fail")

        if not self.x402_facilitator_url:
            issues.append("X402_FACILITATOR_URL not set - x402 payments will fail")

        return issues


# Global settings instance
settings = SimpleSettings()
