"""
Application configuration and settings management.

This module loads configuration from environment variables and provides
a centralized settings object for the entire application.
"""

from functools import lru_cache
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Paygent"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", description="deployment environment")

    # API Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    jwt_secret: str = Field(default="development-secret-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # LLM Configuration
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key for Claude")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for fallback")
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
    x402_max_retries: int = 3
    x402_retry_delay_ms: int = 1000

    # Wallet Configuration (development only - use HSM in production)
    agent_wallet_private_key: Optional[str] = Field(
        default=None,
        description="Agent wallet private key (development only)"
    )

    # Database Configuration
    # Vercel Postgres (production)
    postgres_url: Optional[str] = Field(default=None, description="Vercel Postgres connection URL")
    # Local development
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/paygent",
        description="PostgreSQL connection URL"
    )

    # Redis/KV Configuration
    # Vercel KV (production)
    kv_url: Optional[str] = Field(default=None, description="Vercel KV connection URL")
    kv_rest_api_url: Optional[str] = None
    kv_rest_api_token: Optional[str] = None
    # Local development
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )

    # Vercel Blob (production)
    blob_read_write_token: Optional[str] = None

    # Crypto.com Integration
    crypto_com_api_key: Optional[str] = None
    crypto_com_mcp_url: str = "https://mcp.crypto.com"

    # Rate Limiting
    rate_limit_requests_per_minute: int = 100

    # Agent Configuration
    agent_max_iterations: int = 50
    agent_timeout_seconds: int = 300
    agent_default_budget_usd: float = 100.0
    hitl_approval_threshold_usd: float = 10.0

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

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
