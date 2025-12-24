"""
Test SQL injection prevention via parameterized queries.

This test verifies that:
1. SQLAlchemy uses parameterized queries (not string concatenation)
2. User input is properly escaped
3. SQL injection attempts are prevented
"""
import pytest
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestSQLInjectionPrevention:
    """Test suite for SQL injection prevention."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_command(self, db_session: AsyncSession):
        """Test that SQL injection in agent command is prevented."""
        from src.services.execution_log_service import ExecutionLogService
        from src.models.agent_sessions import ExecutionLog, AgentSession
        from uuid import uuid4
        from datetime import datetime

        # Create a session
        session = AgentSession(
            id=uuid4(),
            user_id=uuid4(),
            wallet_address=None,
            config={}
        )
        db_session.add(session)
        await db_session.commit()

        # Attempt SQL injection via command
        malicious_command = "'; DROP TABLE execution_logs; --"
        log_service = ExecutionLogService(db_session)

        # This should NOT execute SQL injection
        # The command is stored as a string value, not concatenated into SQL
        log = await log_service.create_log(
            session_id=session.id,
            command=malicious_command,
            plan=[],
            tool_calls=[],
            result={},
            total_cost=0.0,
            duration_ms=0
        )

        # Verify log was created safely (command stored as data)
        assert log.id is not None
        assert log.command == malicious_command

        # Verify execution_logs table still exists
        result = await db_session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='execution_logs'"))
        tables = result.fetchall()
        assert any('execution_logs' in str(t) for t in tables)

        # Clean up
        await db_session.delete(log)
        await db_session.delete(session)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_sql_injection_in_filter(self, db_session: AsyncSession):
        """Test that SQL injection in WHERE clause filters is prevented."""
        from src.models.agent_sessions import AgentSession
        from uuid import uuid4
        from sqlalchemy import select

        # Create test session
        test_session = AgentSession(
            id=uuid4(),
            user_id=uuid4(),
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            config={}
        )
        db_session.add(test_session)
        await db_session.commit()

        # Attempt SQL injection via filter
        injection_attempt = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb' OR '1'='1"
        result = await db_session.execute(
            select(AgentSession).where(AgentSession.wallet_address == injection_attempt)
        )
        sessions = result.scalars().all()

        # Should return empty (no match), not all sessions
        # Parameterized query treats the injection string as a literal value
        assert len(sessions) == 0

        # Verify we can still query normally
        result = await db_session.execute(
            select(AgentSession).where(AgentSession.wallet_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        )
        sessions = result.scalars().all()
        assert len(sessions) == 1

        # Clean up
        await db_session.delete(test_session)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_raw_sql_with_parameters(self, db_session: AsyncSession):
        """Test that raw SQL with parameters is safe."""
        from uuid import uuid4

        # Create test data
        test_id = str(uuid4())
        malicious_input = "'; DROP TABLE agents; --"

        # Use parameterized query (NOT string formatting)
        # This is the SAFE way to do raw SQL
        result = await db_session.execute(
            text("SELECT :input as safe_input"),
            {"input": malicious_input}
        )
        row = result.fetchone()

        # The malicious input is treated as a string value, not executable SQL
        assert row[0] == malicious_input

        # Verify tables still exist
        result = await db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [r[0] for r in result.fetchall()]
        assert 'agent_sessions' in tables
        assert 'execution_logs' in tables

    @pytest.mark.asyncio
    async def test_union_based_injection_prevented(self, db_session: AsyncSession):
        """Test that UNION-based injection is prevented."""
        from src.models.agent_sessions import AgentSession, ExecutionLog
        from sqlalchemy import select
        from uuid import uuid4

        # Create test session
        session = AgentSession(
            id=uuid4(),
            user_id=uuid4(),
            wallet_address="0xTEST",
            config={}
        )
        db_session.add(session)
        await db_session.commit()

        # Attempt UNION-based injection
        injection = "0xTEST' UNION SELECT * FROM execution_logs --"
        result = await db_session.execute(
            select(AgentSession).where(AgentSession.wallet_address == injection)
        )
        sessions = result.scalars().all()

        # Should return no results (treated as literal string)
        assert len(sessions) == 0

        # Clean up
        await db_session.delete(session)
        await db_session.commit()


# Test utilities
@pytest.fixture
async def db_session():
    """Provide a database session for testing."""
    from src.core.database import get_db_session

    async with get_db_session() as session:
        yield session
