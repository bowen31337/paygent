"""
Vercel database configuration and connection management.

Handles Vercel Postgres integration for serverless deployment.
"""
import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

# Create base for models
Base = declarative_base()

# Vercel Postgres connection URL from environment
def get_vercel_postgres_url() -> str | None:
    """Get Vercel Postgres URL from environment."""
    return os.getenv("POSTGRES_URL")

def get_vercel_postgres_url_non_pooling() -> str | None:
    """Get Vercel Postgres non-pooling URL from environment."""
    return os.getenv("POSTGRES_URL_NON_POOLING")

def get_dev_database_url() -> str:
    """Get development database URL."""
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./paygent.db")

# Determine database URL based on environment
def get_database_url() -> str:
    """Get database URL based on deployment environment."""
    vercel_postgres_url = get_vercel_postgres_url()
    vercel_postgres_url_non_pooling = get_vercel_postgres_url_non_pooling()
    dev_database_url = get_dev_database_url()

    if vercel_postgres_url:
        # Vercel environment - use connection pooling
        return vercel_postgres_url
    elif vercel_postgres_url_non_pooling:
        # Vercel environment - direct connection (for migrations)
        return vercel_postgres_url_non_pooling
    else:
        # Local development - use SQLite
        return dev_database_url

# Create async engine with appropriate settings for Vercel
def _create_engine():
    """Create async engine with proper imports and error handling."""
    try:
        # Try PostgreSQL first
        db_url = get_database_url()
        if db_url.startswith("postgresql"):
            from sqlalchemy.ext.asyncio import create_async_engine
            return create_async_engine(
                db_url,
                echo=False,  # Disable SQL logging in production
                pool_pre_ping=True,  # Verify connections
                pool_recycle=300,  # Recycle connections every 5 minutes
                pool_size=10,  # Connection pool size for Vercel
                max_overflow=20,  # Max overflow connections
                connect_args={
                    "command_timeout": 60,  # 60 second timeout
                    "server_settings": {
                        "jit": "off",  # Disable JIT for faster connection
                    },
                },
            )
        else:
            # SQLite configuration
            from sqlalchemy.ext.asyncio import create_async_engine
            return create_async_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                connect_args={
                    "check_same_thread": False,  # SQLite setting
                },
            )
    except ImportError as e:
        if "psycopg2" in str(e):
            # Fall back to SQLite if PostgreSQL driver not available
            import warnings
            warnings.warn("psycopg2 not available, falling back to SQLite", RuntimeWarning, stacklevel=2)
            return create_async_engine(
                "sqlite+aiosqlite:///./paygent.db",
                echo=False,
                pool_pre_ping=True,
                connect_args={
                    "check_same_thread": False,
                },
            )
        raise

# Create engine factory function
def get_engine():
    """Get database engine, recreating if needed."""
    return _create_engine()

engine = get_engine()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Usage in FastAPI endpoints:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session here
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """Close database engine."""
    await engine.dispose()


async def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# For Alembic migrations
def get_sync_engine():
    """Get synchronous engine for Alembic."""
    from sqlalchemy import create_engine

    sync_url = get_database_url()
    if sync_url.startswith("sqlite"):
        # SQLite doesn't need special sync engine
        return None

    # Convert async URL to sync URL
    sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        return create_engine(
            sync_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "connect_timeout": 60,
                "server_settings": {
                    "jit": "off",
                },
            },
        )
    except ImportError as e:
        if "psycopg2" in str(e):
            # Return None if PostgreSQL driver not available
            import warnings
            warnings.warn("psycopg2 not available for sync engine, returning None", RuntimeWarning, stacklevel=2)
            return None
        raise


# Database health check
async def check_database_health() -> dict:
    """
    Check database health and return status.

    Returns:
        dict: Health status information
    """
    try:
        # Test connection
        is_connected = await test_connection()

        # Get engine info
        url = str(engine.url)
        pool_size = engine.pool.size()
        checked_in_connections = engine.pool.checkedin()
        checked_out_connections = engine.pool.checkedout()

        return {
            "status": "healthy" if is_connected else "unhealthy",
            "database_url": url,
            "pool_size": pool_size,
            "checked_in_connections": checked_in_connections,
            "checked_out_connections": checked_out_connections,
            "connection_test": is_connected,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database_url": get_database_url(),
        }
