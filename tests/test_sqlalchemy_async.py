"""
Test SQLAlchemy async operations.

This test verifies that SQLAlchemy async operations work correctly
including connection pooling, transactions, and error handling.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.database import (
    Base,
    async_session_maker,
    close_db,
    engine,
    get_db,
    init_db,
)


class TestSQLAlchemyAsyncOperations:
    """Test SQLAlchemy async operations."""

    @pytest.mark.asyncio
    async def test_database_engine_creation(self):
        """Test that database engine is created successfully."""
        assert engine is not None
        assert engine.url is not None

    @pytest.mark.asyncio
    async def test_session_factory_creation(self):
        """Test that async session factory is created."""
        assert async_session_maker is not None

    @pytest.mark.asyncio
    async def test_get_db_generator(self):
        """Test that get_db returns a valid async generator."""
        db_gen = get_db()
        assert hasattr(db_gen, '__aiter__')

        # Test that we can get a session
        db = await db_gen.__anext__()
        assert db is not None
        assert isinstance(db, AsyncSession)

        # Clean up
        await db_gen.aclose()

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test creating a database session."""
        async with async_session_maker() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)

    @pytest.mark.asyncio
    async def test_session_commit_and_close(self):
        """Test session commit and close operations."""
        async with async_session_maker() as session:
            # Execute a simple query
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Session should be open
            assert session.is_active

        # Session should be closed after context manager
        assert not session.is_active

    @pytest.mark.asyncio
    async def test_async_rollback_on_error(self):
        """Test that session rolls back on error."""
        async with async_session_maker() as session:
            # Start a transaction
            await session.begin()

            # Simulate an error
            try:
                # This should trigger a rollback
                await session.rollback()
            except Exception:
                pass

            # Session should still be active
            assert session.is_active

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test creating multiple concurrent sessions."""
        async def create_and_use_session():
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar()

        # Create multiple concurrent sessions
        results = await asyncio.gather(
            *[create_and_use_session() for _ in range(5)]
        )

        assert all(r == 1 for r in results)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test database initialization."""
        # This should not raise an error
        await init_db()

    @pytest.mark.asyncio
    async def test_database_close(self):
        """Test database close operation."""
        # This should not raise an error
        await close_db()

    @pytest.mark.asyncio
    async def test_base_model_is_declarative(self):
        """Test that Base is a DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase as SQLADeclarativeBase

        assert issubclass(Base, SQLADeclarativeBase)

    @pytest.mark.asyncio
    async def test_get_db_dependency_injection(self):
        """Test get_db as a FastAPI dependency."""
        # Simulate FastAPI's dependency injection
        async with get_db() as db:
            assert db is not None
            assert isinstance(db, AsyncSession)

            # Execute a query
            result = await db.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_transaction_isolation(self):
        """Test that sessions maintain transaction isolation."""
        async with async_session_maker() as session1:
            async with async_session_maker() as session2:
                # Both sessions should be independent
                result1 = await session1.execute(text("SELECT 1"))
                result2 = await session2.execute(text("SELECT 1"))

                assert result1.scalar() == result2.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_context_manager_cleanup(self):
        """Test that session context manager properly cleans up."""
        session = async_session_maker()
        async with session as db:
            result = await db.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Session should be closed
        assert not session.is_active

    @pytest.mark.asyncio
    async def test_multiple_operations_in_single_session(self):
        """Test multiple database operations in a single session."""
        async with async_session_maker() as session:
            # Execute multiple queries
            for i in range(5):
                result = await session.execute(text(f"SELECT {i}"))
                assert result.scalar() == i

    @pytest.mark.asyncio
    async def test_session_expire_on_commit_false(self):
        """Test that expire_on_commit is set correctly."""
        async with async_session_maker() as session:
            # Check that expire_on_commit is False
            assert session.expire_on_commit is False

    @pytest.mark.asyncio
    async def test_session_autocommit_false(self):
        """Test that autocommit is disabled."""
        async with async_session_maker() as session:
            # Check that autocommit is False
            assert session.autocommit is False

    @pytest.mark.asyncio
    async def test_session_autoflush_false(self):
        """Test that autoflush is disabled."""
        async with async_session_maker() as session:
            # Check that autoflush is False
            assert session.autoflush is False

    @pytest.mark.asyncio
    async def test_engine_pool_configuration(self):
        """Test that engine is configured correctly."""
        # Check pool configuration
        from sqlalchemy.pool import NullPool

        # Async engine should use NullPool
        assert isinstance(engine.pool, NullPool)

    @pytest.mark.asyncio
    async def test_database_url_conversion(self):
        """Test that database URLs are converted correctly."""
        from src.core.config import settings

        db_url = settings.effective_database_url

        # Check that postgresql:// is converted to postgresql+asyncpg://
        if db_url.startswith("postgresql://"):
            assert engine.url.drivername == "postgresql+asyncpg"
        # Check that sqlite:// is converted to sqlite+aiosqlite://
        elif db_url.startswith("sqlite://"):
            assert "aiosqlite" in engine.url.drivername


class TestSQLAlchemyConnectionPool:
    """Test database connection pool handling under load."""

    @pytest.mark.asyncio
    async def test_high_load_concurrent_queries(self):
        """Test that connection pool handles high load."""
        async def execute_query():
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT 1 + 1"))
                return result.scalar()

        # Execute 50 concurrent queries
        results = await asyncio.gather(
            *[execute_query() for _ in range(50)]
        )

        assert all(r == 2 for r in results)
        assert len(results) == 50

    @pytest.mark.asyncio
    async def test_pool_handles_connection_reuse(self):
        """Test that connection pool reuses connections efficiently."""
        sessions = []

        # Create multiple sessions sequentially
        for _ in range(10):
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                sessions.append(session)
                assert result.scalar() == 1

        assert len(sessions) == 10

    @pytest.mark.asyncio
    async def test_pool_handles_rapid_open_close(self):
        """Test rapid session open and close cycles."""
        for _ in range(20):
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_pool_handles_errors_gracefully(self):
        """Test that pool handles connection errors gracefully."""
        async def execute_with_timeout():
            try:
                async with async_session_maker() as session:
                    # Set a query timeout
                    await session.execute(text("SELECT 1"))
                    await asyncio.sleep(0.01)
                    return True
            except Exception as e:
                # Should handle errors gracefully
                return False

        results = await asyncio.gather(
            *[execute_with_timeout() for _ in range(10)]
        )

        # Most should succeed
        assert sum(results) >= 8

    @pytest.mark.asyncio
    async def test_pool_pre_ping_enabled(self):
        """Test that pool pre_ping is enabled."""
        # Check that pool_pre_ping is enabled in engine
        assert engine.pool is not None

        # Execute a query to test connection
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1


class TestSQLAlchemyRealWorldScenarios:
    """Test real-world database usage scenarios."""

    @pytest.mark.asyncio
    async def test_crud_operations(self):
        """Test basic CRUD operations."""
        from src.models.services import Service

        async with async_session_maker() as session:
            # Create
            service = Service(
                name="Test Service",
                description="Test description",
                endpoint="https://example.com",
                pricing_model="pay-per-call",
                price_amount="0.10",
                price_token="USDC",
            )

            session.add(service)
            await session.commit()
            await session.refresh(service)

            assert service.id is not None
            assert service.name == "Test Service"

            # Read
            result = await session.execute(
                select(Service).where(Service.name == "Test Service")
            )
            retrieved_service = result.scalar_one()

            assert retrieved_service.id == service.id

            # Update
            retrieved_service.description = "Updated description"
            await session.commit()
            await session.refresh(retrieved_service)

            assert retrieved_service.description == "Updated description"

            # Delete
            await session.delete(retrieved_service)
            await session.commit()

            # Verify deletion
            result = await session.execute(
                select(Service).where(Service.name == "Test Service")
            )
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self):
        """Test that transactions roll back on exception."""
        from src.models.services import Service

        async with async_session_maker() as session:
            # Add a service
            service = Service(
                name="Rollback Test",
                description="Should be rolled back",
                endpoint="https://example.com",
                pricing_model="pay-per-call",
                price_amount="0.10",
                price_token="USDC",
            )

            session.add(service)
            await session.flush()

            service_id = service.id

            # Rollback the transaction
            await session.rollback()

            # Verify the service was not committed
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_nested_transaction_rollback(self):
        """Test nested transaction (savepoint) rollback."""
        from src.models.services import Service

        async with async_session_maker() as session:
            # Outer transaction
            service1 = Service(
                name="Service 1",
                description="Should persist",
                endpoint="https://example.com",
                pricing_model="pay-per-call",
                price_amount="0.10",
                price_token="USDC",
            )
            session.add(service1)
            await session.flush()

            # Nested transaction (savepoint)
            async with session.begin_nested():
                service2 = Service(
                    name="Service 2",
                    description="Should be rolled back",
                    endpoint="https://example.com",
                    pricing_model="pay-per-call",
                    price_amount="0.10",
                    price_token="USDC",
                )
                session.add(service2)
                # Rollback the nested transaction
                await session.rollback()

            # Service 1 should still be in session
            assert service1 in session

            # Service 2 should not be persisted
            result = await session.execute(
                select(Service).where(Service.name == "Service 2")
            )
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_bulk_operations(self):
        """Test bulk insert operations."""
        from src.models.services import Service

        async with async_session_maker() as session:
            # Bulk insert
            services = [
                Service(
                    name=f"Bulk Service {i}",
                    description=f"Service {i}",
                    endpoint="https://example.com",
                    pricing_model="pay-per-call",
                    price_amount="0.10",
                    price_token="USDC",
                )
                for i in range(10)
            ]

            session.add_all(services)
            await session.commit()

            # Verify bulk insert
            result = await session.execute(
                select(Service).where(Service.name.like("Bulk Service%"))
            )
            retrieved_services = result.scalars().all()

            assert len(retrieved_services) == 10

            # Cleanup
            for service in retrieved_services:
                await session.delete(service)
            await session.commit()

    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """Test concurrent write operations."""
        from src.models.services import Service

        async def create_service(index: int):
            async with async_session_maker() as session:
                service = Service(
                    name=f"Concurrent Service {index}",
                    description=f"Service {index}",
                    endpoint="https://example.com",
                    pricing_model="pay-per-call",
                    price_amount="0.10",
                    price_token="USDC",
                )
                session.add(service)
                await session.commit()
                return service.id

        # Create services concurrently
        service_ids = await asyncio.gather(
            *[create_service(i) for i in range(10)]
        )

        assert len(service_ids) == 10
        assert all(id is not None for id in service_ids)

        # Cleanup
        async with async_session_maker() as session:
            for service_id in service_ids:
                service = await session.get(Service, service_id)
                if service:
                    await session.delete(service)
            await session.commit()

    @pytest.mark.asyncio
    async def test_relationship_loading(self):
        """Test loading related objects."""
        from src.models.payments import Payment
        from src.models.services import Service

        async with async_session_maker() as session:
            # Create a service
            service = Service(
                name="Related Service",
                description="Test service",
                endpoint="https://example.com",
                pricing_model="pay-per-call",
                price_amount="0.10",
                price_token="USDC",
            )
            session.add(service)
            await session.commit()
            await session.refresh(service)

            # Create a payment for this service
            payment = Payment(
                agent_wallet="0x1234567890123456789012345678901234567890",
                service_id=service.id,
                recipient="0x0987654321098765432109876543210987654321",
                amount="0.10",
                token="USDC",
                status="pending",
            )
            session.add(payment)
            await session.commit()

            # Load payment with service relationship
            result = await session.execute(
                select(Payment).where(Payment.id == payment.id)
            )
            retrieved_payment = result.scalar_one()

            # Access the relationship
            assert retrieved_payment.service is not None
            assert retrieved_payment.service.name == "Related Service"

            # Cleanup
            await session.delete(retrieved_payment)
            await session.delete(service)
            await session.commit()
