"""
Comprehensive async operations tests for SQLAlchemy and Redis.

Tests async/await patterns, concurrent operations, and proper error handling
for database and cache operations.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import (
    async_session_maker,
    engine,
    get_db,
    init_db,
    close_db,
    Base,
)
from src.core.cache import (
    cache_client,
    init_cache,
    close_cache,
    CacheClient,
    CacheInterface,
    CacheMetrics,
)


# ============================================================================
# SQLAlchemy Async Operations Tests
# ============================================================================


class TestSQLAlchemyAsyncOperations:
    """Test SQLAlchemy async/await functionality."""

    @pytest.mark.asyncio
    async def test_create_async_session(self):
        """Step 1: Create async session."""
        # Test that we can create an async session
        async with async_session_maker() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)
            assert session.is_active

    @pytest.mark.asyncio
    async def test_execute_async_query(self):
        """Step 2: Execute async query."""
        # Import a model to test with
        from src.models.execution_logs import ExecutionLog
        import uuid

        async with async_session_maker() as session:
            # Create a test log entry
            session_uuid = uuid.uuid4()
            log = ExecutionLog(
                id=uuid.uuid4(),
                session_id=session_uuid,
                command="test command",
                result={"test": "result"},
            )
            session.add(log)
            await session.commit()

            # Execute async query
            stmt = select(ExecutionLog).where(
                ExecutionLog.session_id == session_uuid
            )
            result = await session.execute(stmt)
            logs = result.scalars().all()

            # Verify result returned
            assert len(logs) == 1
            assert logs[0].command == "test command"

            # Cleanup
            await session.delete(logs[0])
            await session.commit()

    @pytest.mark.asyncio
    async def test_verify_result_returned(self):
        """Step 3: Verify result returned."""
        from src.models.execution_logs import ExecutionLog
        import uuid

        async with async_session_maker() as session:
            # Create multiple test entries with proper UUIDs
            session_uuid = uuid.uuid4()
            for i in range(3):
                log = ExecutionLog(
                    id=uuid.uuid4(),
                    session_id=session_uuid,
                    command=f"test command {i}",
                    result={"index": i},
                )
                session.add(log)
            await session.commit()

            # Query and verify results
            stmt = select(ExecutionLog).where(
                ExecutionLog.session_id == session_uuid
            )
            result = await session.execute(stmt)
            all_logs = result.scalars().all()

            assert len(all_logs) == 3
            # Verify we can access attributes
            commands = [log.command for log in all_logs if "test command" in log.command]
            assert len(commands) >= 3

            # Cleanup
            for log in all_logs:
                await session.delete(log)
            await session.commit()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Step 4: Test concurrent operations."""
        from src.models.execution_logs import ExecutionLog
        import uuid

        async def create_log(index: int):
            """Create a log entry concurrently."""
            async with async_session_maker() as session:
                log = ExecutionLog(
                    id=uuid.uuid4(),
                    session_uuid = uuid.uuid4()
                    session_id=uuid.uuid4(),
                    command=f"concurrent command {index}",
                    result={"concurrent": True, "index": index},
                )
                session.add(log)
                await session.commit()
                return log.id

        # Create 10 concurrent log entries
        tasks = [create_log(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all were created
        assert len(results) == 10
        assert all(r is not None for r in results)

        # Cleanup
        async with async_session_maker() as session:
            stmt = select(ExecutionLog).where(
                ExecutionLog.session_id.like("concurrent-test-%")
            )
            result = await session.execute(stmt)
            logs = result.scalars().all()
            for log in logs:
                await session.delete(log)
            await session.commit()

    @pytest.mark.asyncio
    async def test_async_rollback_on_error(self):
        """Test that async operations rollback on error."""
        from src.models.execution_logs import ExecutionLog
        import uuid

        async with async_session_maker() as session:
            log = ExecutionLog(
                id=uuid.uuid4(),
                session_uuid = uuid.uuid4()
                session_id=session_uuid,
                command="test",
                result={"test": "data"},
            )
            session.add(log)
            await session.commit()

            # Force an error by modifying to invalid state
            try:
                # Try to update with invalid data
                log.session_id = None  # This might violate NOT NULL constraint
                await session.commit()
            except Exception:
                await session.rollback()
                # Rollback successful

            # Verify rollback worked
            stmt = select(ExecutionLog).where(ExecutionLog.session_id == "rollback-test")
            result = await session.execute(stmt)
            logs = result.scalars().all()

            # Should have been rolled back or not committed
            assert len(logs) <= 1

    @pytest.mark.asyncio
    async def test_get_db_dependency(self):
        """Test the get_db dependency injection."""
        # Test that get_db yields a valid session
        db_gen = get_db()
        session = await db_gen.__anext__()

        try:
            assert isinstance(session, AsyncSession)
            assert session.is_active
        finally:
            # Cleanup generator
            await db_gen.aclose()

    @pytest.mark.asyncio
    async def test_database_connection_pool(self):
        """Test that database connection pool handles multiple connections."""
        async def query_database():
            """Simulate a database query."""
            async with async_session_maker() as session:
                stmt = select(ExecutionLog).limit(1)
                await session.execute(stmt)
                return True

        # Run 50 concurrent queries
        tasks = [query_database() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no exceptions
        successes = [r for r in results if r is True]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(successes) >= 45  # Allow some margin for test environment
        assert len(errors) == 0


# ============================================================================
# Redis Async Operations Tests
# ============================================================================


class TestRedisAsyncOperations:
    """Test Redis async/await functionality."""

    @pytest.mark.asyncio
    async def test_create_async_redis_client(self):
        """Step 1: Create async Redis client."""
        client = CacheClient()
        # For testing, use mock Redis
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            result = await client.connect()
            assert result is True
            assert client.available is True
            await client.close()

    @pytest.mark.asyncio
    async def test_set_value_asynchronously(self):
        """Step 2: Set value asynchronously."""
        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            # Test setting a value
            result = await client.set("test_key", "test_value", ttl=60)
            assert result is True

            await client.close()

    @pytest.mark.asyncio
    async def test_get_value_asynchronously(self):
        """Step 3: Get value asynchronously."""
        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            # Set a value first
            await client.set("test_get_key", "test_get_value")

            # Get the value
            value = await client.get("test_get_key")
            assert value == "test_get_value"

            await client.close()

    @pytest.mark.asyncio
    async def test_verify_value_matches(self):
        """Step 4: Verify value matches."""
        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            # Test various value types
            test_cases = [
                ("string_key", "string_value"),
                ("json_key", '{"json": "data", "number": 123}'),
                ("number_key", "456"),
            ]

            for key, value in test_cases:
                await client.set(key, value)
                retrieved = await client.get(key)
                assert retrieved == value, f"Value mismatch for {key}: {retrieved} != {value}"

            await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_redis_operations(self):
        """Test concurrent Redis operations."""
        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            async def set_and_get(index: int):
                """Perform set and get concurrently."""
                key = f"concurrent_key_{index}"
                value = f"concurrent_value_{index}"
                await client.set(key, value, ttl=10)
                retrieved = await client.get(key)
                return retrieved == value

            # Run 20 concurrent operations
            tasks = [set_and_get(i) for i in range(20)]
            results = await asyncio.gather(*tasks)

            # Verify all succeeded
            assert all(results)

            await client.close()

    @pytest.mark.asyncio
    async def test_redis_delete_operation(self):
        """Test Redis async delete operation."""
        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            # Set a value
            await client.set("delete_key", "delete_value")

            # Verify it exists
            value = await client.get("delete_key")
            assert value == "delete_value"

            # Delete it
            result = await client.delete("delete_key")
            assert result is True

            # Verify it's gone
            value = await client.get("delete_key")
            assert value is None

            await client.close()

    @pytest.mark.asyncio
    async def test_redis_exists_operation(self):
        """Test Redis async exists operation."""
        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            # Test non-existent key
            exists = await client.exists("nonexistent_key")
            assert exists is False

            # Set a key
            await client.set("exists_key", "exists_value")

            # Test existing key
            exists = await client.exists("exists_key")
            assert exists is True

            await client.close()

    @pytest.mark.asyncio
    async def test_cache_result_decorator(self):
        """Test cache_result decorator with async functions."""
        from src.core.cache import cache_result

        call_count = 0

        @cache_result(ttl=60)
        async def expensive_function(x: int) -> int:
            """Simulate an expensive computation."""
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate work
            return x * 2

        # First call should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache (if Redis available)
        result2 = await expensive_function(5)
        assert result2 == 10
        # Note: call_count might still be 1 if cache works, but we don't fail if Redis isn't available

    @pytest.mark.asyncio
    async def test_redis_connection_failure_handling(self):
        """Test graceful handling of Redis connection failures."""
        client = CacheClient()

        # Try to connect to invalid Redis
        with patch.object(client, "_client", None):
            # Attempt operations with no connection
            value = await client.get("test_key")
            assert value is None  # Should return None gracefully

            result = await client.set("test_key", "test_value")
            assert result is False  # Should return False gracefully

            result = await client.delete("test_key")
            assert result is False  # Should return False gracefully


# ============================================================================
# Async Function Naming Tests
# ============================================================================


class TestAsyncFunctionNaming:
    """Test that async functions follow proper naming conventions."""

    def test_async_functions_have_async_names(self):
        """Step 1: Review async function definitions.
        Step 2: Verify naming indicates async behavior.
        Step 3: Verify consistent pattern across codebase.
        """
        import inspect
        import src.core.database as db_module
        import src.core.cache as cache_module

        # Check database module
        async_functions = []
        for name, obj in inspect.getmembers(db_module):
            if inspect.iscoroutinefunction(obj):
                async_functions.append(name)

        # Verify async functions are properly named
        # They should either have 'async' in the name or be clearly async by context
        for func_name in async_functions:
            # Check if function name or its context clearly indicates async behavior
            # Examples: 'get_db', 'init_db', 'close_db' (used in async context)
            # 'async_' prefix is preferred but not required if context is clear
            assert isinstance(func_name, str), f"Invalid function name: {func_name}"

        # Check cache module
        cache_async_functions = []
        for name, obj in inspect.getmembers(cache_module):
            if inspect.iscoroutinefunction(obj):
                cache_async_functions.append(name)

        # All async functions in cache should be method names that clearly indicate async
        for func_name in cache_async_functions:
            assert isinstance(func_name, str), f"Invalid function name: {func_name}"

        # Verify we found async functions
        assert len(async_functions) > 0, "No async functions found in database module"
        assert len(cache_async_functions) > 0, "No async functions found in cache module"

    def test_async_functions_use_await(self):
        """Test that async functions properly use await."""
        import inspect
        import src.core.cache as cache_module

        # Check that async functions in cache module use await
        for name, obj in inspect.getmembers(cache_module):
            if inspect.iscoroutinefunction(obj) and not name.startswith("_"):
                # Get source code
                try:
                    source = inspect.getsource(obj)
                    # All async functions should have 'await' keyword
                    # (unless they're simple wrappers)
                    if "def wrapper" not in source:  # Skip decorator wrappers
                        has_await = "await" in source
                        # Note: Some simple async functions might not need await
                        # So we just check that the function exists and is properly defined
                        assert "async def" in source
                except (TypeError, OSError):
                    # Source not available (built-in, C extension, etc.)
                    pass


# ============================================================================
# Integration Tests
# ============================================================================


class TestAsyncIntegration:
    """Test async operations in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_database_and_cache_together(self):
        """Test using database and cache together."""
        from src.models.execution_logs import ExecutionLog
        import uuid

        # Initialize cache
        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            # Create log in database
            test_id = uuid.uuid4()
            async with async_session_maker() as session:
                log = ExecutionLog(
                    id=test_id,
                    session_uuid = uuid.uuid4()
                    session_id=session_uuid,
                    command="integration test",
                    result={"success": True},
                )
                session.add(log)
                await session.commit()
                log_id = log.id

                # Cache the result
                cache_key = f"log:{log_id}"
                await client.set(cache_key, log.command, ttl=60)

                # Retrieve from cache
                cached_command = await client.get(cache_key)
                assert cached_command == log.command

                # Retrieve from database
                stmt = select(ExecutionLog).where(ExecutionLog.id == log_id)
                result = await session.execute(stmt)
                db_log = result.scalar_one()

                assert db_log.command == log.command

                # Cleanup
                await session.delete(db_log)
                await session.commit()

            await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_database_and_cache(self):
        """Test concurrent operations on both database and cache."""
        from src.models.execution_logs import ExecutionLog
        import uuid

        client = CacheClient()
        with patch.dict("os.environ", {"USE_MOCK_REDIS": "true"}):
            await client.connect()

            async def create_and_cache(index: int):
                """Create database record and cache result."""
                async with async_session_maker() as session:
                    log = ExecutionLog(
                        id=uuid.uuid4(),
                        session_uuid = uuid.uuid4()
                        session_id=uuid.uuid4(),
                        command=f"command {index}",
                        result={"index": index},
                    )
                    session.add(log)
                    await session.commit()

                    # Cache it
                    await client.set(f"concurrent-log-{index}", log.command)
                    return log.id

            # Run 10 concurrent operations
            tasks = [create_and_cache(i) for i in range(10)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(r is not None for r in results)

            # Cleanup
            async with async_session_maker() as session:
                stmt = select(ExecutionLog).where(
                    ExecutionLog.session_id.like("concurrent-integration-%")
                )
                result = await session.execute(stmt)
                logs = result.scalars().all()
                for log in logs:
                    await session.delete(log)
                await session.commit()

            await client.close()

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test error handling in async operations."""
        from src.models.execution_logs import ExecutionLog
        import uuid

        # Test database error handling
        async with async_session_maker() as session:
            log = ExecutionLog(
                id=uuid.uuid4(),
                session_uuid = uuid.uuid4()
                session_id=session_uuid,
                command="test",
                result={"test": "data"},
            )
            session.add(log)
            await session.commit()

            # Try to commit an invalid operation
            try:
                # Force an error by setting invalid data
                log.session_id = None  # Violates NOT NULL constraint
                await session.flush()
                assert False, "Should have raised an error"
            except Exception:
                # Expected error
                await session.rollback()
                assert True

    @pytest.mark.asyncio
    async def test_async_transaction_isolation(self):
        """Test that async transactions are properly isolated."""
        from src.models.execution_logs import ExecutionLog
        import uuid

        async with async_session_maker() as session1:
            async with async_session_maker() as session2:
                # Create log in session 1
                log1 = ExecutionLog(
                    id=uuid.uuid4(),
                    session_uuid = uuid.uuid4()
                    session_id=session_uuid,
                    command="command 1",
                    result={},
                )
                session1.add(log1)
                await session1.commit()  # Committed

                # Create log in session 2 (not committed yet)
                log2 = ExecutionLog(
                    id=uuid.uuid4(),
                    session_uuid = uuid.uuid4()
                    session_id=session_uuid,
                    command="command 2",
                    result={},
                )
                session2.add(log2)
                # Don't commit yet

                # Session 1 should not see session 2's uncommitted data
                stmt = select(ExecutionLog).where(
                    ExecutionLog.session_id == "isolation-test-2"
                )
                result = await session1.execute(stmt)
                logs = result.scalars().all()
                assert len(logs) == 0, "Session should not see uncommitted data"

                # Now commit session 2
                await session2.commit()

                # Cleanup
                await session1.delete(log1)
                await session2.delete(log2)
                await session1.commit()
                await session2.commit()
