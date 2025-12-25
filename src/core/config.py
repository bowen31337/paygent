"""
Application configuration and settings management.

This module loads configuration from environment variables and provides
a centralized settings object for the entire application.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from .constants import (
    AGENT_DEFAULT_BUDGET_USD,
    AGENT_MAX_ITERATIONS,
    AGENT_TIMEOUT_SECONDS,
    DEFAULT_APP_PORT,
    DEFAULT_DAILY_LIMIT_USD,
    DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE,
    HITL_APPROVAL_THRESHOLD_USD,
    JWT_EXPIRATION_HOURS,
    X402_MAX_RETRIES,
    X402_RETRY_DELAY_MS,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Paygent"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", description="deployment environment")

    # API Server
    host: str = "0.0.0.0"
    port: int = DEFAULT_APP_PORT

    # Security
    jwt_secret: str = Field(default="development-secret-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = JWT_EXPIRATION_HOURS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list.

        Args:
            v: CORS origins as string (comma-separated) or list

        Returns:
            list[str]: List of CORS origin URLs
        """
        if isinstance(v, str):
            if not v.strip():
                return ["http://localhost:3000", "http://localhost:8000"]
            return [origin.strip() for origin in v.split(",")]
        return v

    # LLM Configuration
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key for Claude")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for fallback")
    default_model: str = "claude-sonnet-4-20250514"
    fallback_model: str = "gpt-4"

    # Cronos Blockchain
    cronos_rpc_url: str = Field(
        default="https://evm-t3.cronos.org",
        description="Cronos EVM RPC URL"
    )
    cronos_chain_id: int = Field(default=338, description="338 for testnet, 25 for mainnet")
    cronos_testnet_rpc_url: str = "https://evm-t3.cronos.org"
    cronos_testnet_chain_id: int = 338

    # x402 Configuration
    x402_facilitator_url: str = Field(
        default="https://x402-facilitator.cronos.org",
        description="x402 Facilitator URL for payment verification"
    )
    x402_max_retries: int = X402_MAX_RETRIES
    x402_retry_delay_ms: int = X402_RETRY_DELAY_MS

    # Wallet Configuration (development only - use HSM in production)
    agent_wallet_private_key: str | None = Field(
        default=None,
        description="Agent wallet private key (development only)"
    )
    default_wallet_address: str = Field(
        default="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        description="Default agent wallet address"
    )
    default_daily_limit_usd: float = DEFAULT_DAILY_LIMIT_USD

    # Database Configuration
    # Vercel Postgres (production)
    postgres_url: str | None = Field(default=None, description="Vercel Postgres connection URL")
    # Local development - uses SQLite in-memory by default for easy testing
    database_url: str = Field(
        default="sqlite:///:memory:",
        description="Database connection URL (PostgreSQL or SQLite)"
    )

    # Redis/KV Configuration
    # Vercel KV (production)
    kv_url: str | None = Field(default=None, description="Vercel KV connection URL")
    kv_rest_api_url: str | None = None
    kv_rest_api_token: str | None = None
    # Local development - optional, will gracefully disable cache if not available
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL (optional, cache disabled if not reachable)"
    )

    # Vercel Blob (production)
    blob_read_write_token: str | None = None

    # Crypto.com Integration
    crypto_com_api_key: str | None = None
    crypto_com_mcp_url: str = "https://mcp.crypto.com"

    # Rate Limiting
    rate_limit_requests_per_minute: int = DEFAULT_RATE_LIMIT_REQUESTS_PER_MINUTE

    # Agent Configuration
    agent_max_iterations: int = AGENT_MAX_ITERATIONS
    agent_timeout_seconds: int = AGENT_TIMEOUT_SECONDS
    agent_default_budget_usd: float = AGENT_DEFAULT_BUDGET_USD
    hitl_approval_threshold_usd: float = HITL_APPROVAL_THRESHOLD_USD

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Alerting
    alert_webhook_url: str | None = Field(
        default=None,
        description="Webhook URL for critical alert notifications"
    )
    alert_enabled: bool = Field(
        default=True,
        description="Whether to enable alerting for critical failures"
    )

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
