"""
Tests for the session memory module.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.memory import SessionMemoryManager


class TestSessionMemoryManager:
    """Test SessionMemoryManager class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.add = Mock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def session_id(self):
        """Create a test session ID."""
        return uuid4()

    @pytest.fixture
    def memory_manager(self, mock_db, session_id):
        """Create a SessionMemoryManager instance with mocked dependencies."""
        return SessionMemoryManager(mock_db, session_id)

    def test_initialization(self, memory_manager, session_id):
        """Test memory manager initializes correctly."""
        assert memory_manager.session_id == session_id
        assert memory_manager.db is not None

    @pytest.mark.asyncio
    async def test_store_conversation_basic(self, memory_manager, mock_db):
        """Test storing a basic conversation turn."""
        user_msg = "Check my balance"
        agent_response = "Your balance is 100 USDC"

        result = await memory_manager.store_conversation(user_msg, agent_response)

        # Verify db.add was called twice (user + agent messages)
        assert mock_db.add.call_count == 2
        assert mock_db.commit.call_count == 1
        assert isinstance(result, UUID)

    @pytest.mark.asyncio
    async def test_store_conversation_with_metadata(self, memory_manager, mock_db):
        """Test storing conversation with metadata."""
        user_msg = "Pay 100 USDC"
        agent_response = "Payment initiated"
        metadata = {"intent": "payment", "amount": 100}

        await memory_manager.store_conversation(
            user_msg,
            agent_response,
            metadata=metadata
        )

        assert mock_db.add.call_count == 2
        assert mock_db.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_store_conversation_custom_message_type(self, memory_manager, mock_db):
        """Test storing conversation with custom message type."""
        user_msg = "System notification"
        agent_response = "Processed"

        await memory_manager.store_conversation(
            user_msg,
            agent_response,
            message_type="system"
        )

        assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_store_conversation_empty_metadata(self, memory_manager, mock_db):
        """Test storing conversation with None metadata defaults to empty dict."""
        await memory_manager.store_conversation(
            "Hello",
            "Hi there",
            metadata=None
        )

        # Should still store successfully
        assert mock_db.add.call_count == 2
        assert mock_db.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_get_conversation_history_default_params(self, memory_manager):
        """Test retrieving conversation history with default parameters."""
        # Mock the database query result
        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=mock_result)
        mock_result.all = Mock(return_value=[])

        memory_manager.db.execute = AsyncMock(return_value=mock_result)

        history = await memory_manager.get_conversation_history()

        assert isinstance(history, list)
        memory_manager.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_history_with_limit(self, memory_manager):
        """Test retrieving conversation history with custom limit."""
        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=mock_result)
        mock_result.all = Mock(return_value=[])

        memory_manager.db.execute = AsyncMock(return_value=mock_result)

        history = await memory_manager.get_conversation_history(limit=5)

        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_get_conversation_history_with_offset(self, memory_manager):
        """Test retrieving conversation history with offset."""
        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=mock_result)
        mock_result.all = Mock(return_value=[])

        memory_manager.db.execute = AsyncMock(return_value=mock_result)

        history = await memory_manager.get_conversation_history(limit=10, offset=5)

        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_clear_memory(self, memory_manager):
        """Test clearing memory."""
        # Mock the delete query
        mock_result = AsyncMock()
        memory_manager.db.execute = AsyncMock(return_value=mock_result)

        await memory_manager.clear_memory()

        memory_manager.db.execute.assert_called()
        memory_manager.db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_memory_count(self, memory_manager):
        """Test getting memory count."""
        # Mock count query - need to handle the chain properly
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[1, 2, 3, 4, 5])  # Return list of 5 items

        async def mock_scalars_func():
            return mock_scalars

        mock_result = AsyncMock()
        mock_result.scalars = mock_scalars_func

        memory_manager.db.execute = AsyncMock(return_value=mock_result)

        count = await memory_manager.get_memory_count()

        assert isinstance(count, int)
        assert count == 5

    def test_multiple_session_managers(self, mock_db):
        """Test creating multiple memory managers for different sessions."""
        session1 = uuid4()
        session2 = uuid4()

        manager1 = SessionMemoryManager(mock_db, session1)
        manager2 = SessionMemoryManager(mock_db, session2)

        assert manager1.session_id != manager2.session_id
        assert manager1.session_id == session1
        assert manager2.session_id == session2

    @pytest.mark.asyncio
    async def test_store_conversation_database_error(self, memory_manager, mock_db):
        """Test handling database error during conversation storage."""
        # Mock database to raise an exception
        mock_db.commit = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(Exception):
            await memory_manager.store_conversation(
                "Test message",
                "Test response"
            )

    @pytest.mark.asyncio
    async def test_get_conversation_history_empty(self, memory_manager):
        """Test retrieving history when no conversations exist."""
        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=mock_result)
        mock_result.all = Mock(return_value=[])

        memory_manager.db.execute = AsyncMock(return_value=mock_result)

        history = await memory_manager.get_conversation_history()

        assert history == []

    @pytest.mark.asyncio
    async def test_conversation_history_format(self, memory_manager):
        """Test that conversation history returns proper format."""
        # Create mock memory objects
        mock_memory = Mock()
        mock_memory.message_type = "human"
        mock_memory.content = "Test message"
        mock_memory.timestamp = datetime.utcnow()
        mock_memory.extra_data = {}

        mock_result = AsyncMock()
        mock_result.scalars = Mock(return_value=mock_result)
        mock_result.all = Mock(return_value=[mock_memory])

        memory_manager.db.execute = AsyncMock(return_value=mock_result)

        history = await memory_manager.get_conversation_history()

        assert len(history) == 1
        assert isinstance(history[0], dict)
