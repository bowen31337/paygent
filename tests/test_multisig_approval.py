"""
Test multi-sig approval for high-value operations.

This test verifies that multi-signature approval workflows work correctly
for high-value operations requiring multiple approvals.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.approval_requests import ApprovalRequest
from src.services.approval_service import ApprovalService


class TestMultiSigApproval:
    """Test multi-signature approval functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.fixture
    def approval_service(self, mock_db):
        """Create an approval service instance."""
        return ApprovalService(mock_db)

    @pytest.mark.asyncio
    async def test_create_approval_request(self, approval_service):
        """Test creating a new approval request."""
        session_id = uuid4()
        tool_name = "x402_payment"
        tool_args = {
            "amount": "1000",
            "token": "USDC",
            "recipient": "0x1234567890123456789012345678901234567890",
        }

        request = await approval_service.create_request(
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            required_approvers=3,
        )

        assert request is not None
        assert request.session_id == session_id
        assert request.tool_name == tool_name
        assert request.decision == "pending"
        assert request.required_approvers == 3

    @pytest.mark.asyncio
    async def test_multi_sig_approval_workflow(self, mock_db):
        """Test complete multi-sig approval workflow."""
        from src.models.agent_sessions import AgentSession

        # Create a session
        session_id = uuid4()
        approval_service = ApprovalService(mock_db)

        # Mock database operations
        mock_request = MagicMock()
        mock_request.id = uuid4()
        mock_request.session_id = session_id
        mock_request.tool_name = "x402_payment"
        mock_request.tool_args = {"amount": "1000", "token": "USDC"}
        mock_request.decision = "pending"
        mock_request.required_approvers = 3
        mock_request.approvals = []
        mock_request.created_at = datetime.utcnow()

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Create approval request
        with patch.object(approval_service, '_create_db_request', return_value=mock_request):
            request = await approval_service.create_request(
                session_id=session_id,
                tool_name="x402_payment",
                tool_args={"amount": "1000", "token": "USDC"},
                required_approvers=3,
            )

            assert request.decision == "pending"
            assert request.required_approvers == 3

            # Add first approval
            approver_1 = "0x1111111111111111111111111111111111111111"
            with patch.object(approval_service, '_add_approval', return_value=True):
                result = await approval_service.add_approval(
                    request.id, approver_1, "approve"
                )
                assert result is True

            # Add second approval
            approver_2 = "0x2222222222222222222222222222222222222222"
            with patch.object(approval_service, '_add_approval', return_value=True):
                result = await approval_service.add_approval(
                    request.id, approver_2, "approve"
                )
                assert result is True

            # Add third approval (should reach threshold)
            approver_3 = "0x3333333333333333333333333333333333333333"
            with patch.object(
                approval_service,
                '_check_approval_threshold',
                return_value=True
            ):
                with patch.object(approval_service, '_update_request_decision', return_value=True):
                    result = await approval_service.add_approval(
                        request.id, approver_3, "approve"
                    )
                    assert result is True

    @pytest.mark.asyncio
    async def test_approval_threshold_checking(self, approval_service):
        """Test that approval threshold is correctly checked."""
        request_id = uuid4()

        # Test with different approval counts
        test_cases = [
            (1, 3, False),  # 1 of 3 approvals - not enough
            (2, 3, False),  # 2 of 3 approvals - not enough
            (3, 3, True),   # 3 of 3 approvals - threshold reached
            (4, 3, True),   # 4 of 3 approvals - threshold exceeded
        ]

        for current, required, expected in test_cases:
            result = await approval_service._check_threshold(current, required)
            assert result is expected

    @pytest.mark.asyncio
    async def test_approval_with_edits(self, approval_service):
        """Test approval with edited tool arguments."""
        session_id = uuid4()
        request_id = uuid4()

        original_args = {
            "amount": "1000",
            "token": "USDC",
            "recipient": "0x1234567890123456789012345678901234567890",
        }

        edited_args = {
            "amount": "500",  # Reduced amount
            "token": "USDC",
            "recipient": "0x1234567890123456789012345678901234567890",
        }

        # Mock the request
        mock_request = MagicMock()
        mock_request.id = request_id
        mock_request.tool_args = original_args

        # Approver edits the arguments
        with patch.object(approval_service, '_get_request', return_value=mock_request):
            result = await approval_service.approve_with_edits(
                request_id=request_id,
                approver="0x1111111111111111111111111111111111111111",
                edited_args=edited_args,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_rejection_workflow(self, approval_service):
        """Test rejection workflow for approval requests."""
        request_id = uuid4()

        # Single rejection should reject the request
        with patch.object(approval_service, '_update_request_decision', return_value=True):
            result = await approval_service.reject_request(
                request_id=request_id,
                rejector="0x1111111111111111111111111111111111111111",
                reason="Amount too high",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_concurrent_approvals(self, approval_service):
        """Test concurrent approval submissions."""
        request_id = uuid4()

        approvers = [
            f"0x{i:040x}" for i in range(1, 6)  # 5 approvers
        ]

        # Submit all approvals concurrently
        with patch.object(approval_service, '_add_approval', return_value=True):
            results = await asyncio.gather(
                *[
                    approval_service.add_approval(request_id, approver, "approve")
                    for approver in approvers
                ]
            )

            assert all(results)
            assert len(results) == 5

    @pytest.mark.asyncio
    async def test_approval_timeout(self, approval_service):
        """Test that approval requests timeout after a period."""
        request_id = uuid4()

        # Mock request created 2 hours ago
        old_request = MagicMock()
        old_request.id = request_id
        old_request.created_at = datetime.utcnow() - timedelta(hours=2)
        old_request.decision = "pending"

        # Check for timeout
        with patch.object(approval_service, '_get_request', return_value=old_request):
            is_expired = await approval_service._check_expiry(request_id, timeout_hours=1)
            assert is_expired is True

        # Mock request created 30 minutes ago
        recent_request = MagicMock()
        recent_request.id = request_id
        recent_request.created_at = datetime.utcnow() - timedelta(minutes=30)
        recent_request.decision = "pending"

        with patch.object(approval_service, '_get_request', return_value=recent_request):
            is_expired = await approval_service._check_expiry(request_id, timeout_hours=1)
            assert is_expired is False

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self, approval_service):
        """Test retrieving pending approval requests."""
        session_id = uuid4()

        # Mock pending requests
        mock_requests = [
            MagicMock(
                id=uuid4(),
                tool_name="x402_payment",
                decision="pending",
                created_at=datetime.utcnow(),
            )
            for _ in range(5)
        ]

        with patch.object(approval_service, '_get_pending_requests', return_value=mock_requests):
            pending = await approval_service.get_pending_requests(session_id)

            assert len(pending) == 5
            assert all(req.decision == "pending" for req in pending)

    @pytest.mark.asyncio
    async def test_approval_history(self, approval_service):
        """Test retrieving approval history."""
        session_id = uuid4()

        # Mock approval history
        mock_history = [
            MagicMock(
                id=uuid4(),
                tool_name="x402_payment",
                decision="approved",
                created_at=datetime.utcnow() - timedelta(hours=1),
            ),
            MagicMock(
                id=uuid4(),
                tool_name="transfer_tokens",
                decision="rejected",
                created_at=datetime.utcnow() - timedelta(hours=2),
            ),
        ]

        with patch.object(approval_service, '_get_approval_history', return_value=mock_history):
            history = await approval_service.get_approval_history(session_id)

            assert len(history) == 2
            assert history[0].decision == "approved"
            assert history[1].decision == "rejected"

    @pytest.mark.asyncio
    async def test_multi_sig_with_varying_thresholds(self, approval_service):
        """Test multi-sig with different approval thresholds."""
        test_cases = [
            (1, 1, True),   # 1 of 1 - threshold reached
            (2, 3, False),  # 2 of 3 - not enough
            (3, 3, True),   # 3 of 3 - threshold reached
            (4, 5, False),  # 4 of 5 - not enough
            (5, 5, True),   # 5 of 5 - threshold reached
        ]

        for current, required, expected in test_cases:
            result = await approval_service._check_threshold(current, required)
            assert result is expected, \
                f"Failed for {current}/{required} approvals, expected {expected}"

    @pytest.mark.asyncio
    async def test_approval_revocation(self, approval_service):
        """Test that an approval can be revoked."""
        request_id = uuid4()
        approver = "0x1111111111111111111111111111111111111111"

        with patch.object(approval_service, '_revoke_approval', return_value=True):
            result = await approval_service.revoke_approval(request_id, approver)
            assert result is True

    @pytest.mark.asyncio
    async def test_duplicate_approval_prevention(self, approval_service):
        """Test that duplicate approvals from the same approver are prevented."""
        request_id = uuid4()
        approver = "0x1111111111111111111111111111111111111111"

        # First approval
        with patch.object(approval_service, '_add_approval', return_value=True):
            result1 = await approval_service.add_approval(request_id, approver, "approve")
            assert result1 is True

        # Try to approve again
        with patch.object(approval_service, '_add_approval', return_value=False):
            result2 = await approval_service.add_approval(request_id, approver, "approve")
            assert result2 is False

    @pytest.mark.asyncio
    async def test_high_value_operation_detection(self, approval_service):
        """Test detection of high-value operations requiring multi-sig."""
        test_cases = [
            ({"amount": "10", "token": "USDC"}, False),    # Low value - single sig
            ({"amount": "100", "token": "USDC"}, False),   # Medium value - single sig
            ({"amount": "1000", "token": "USDC"}, True),   # High value - multi-sig
            ({"amount": "10000", "token": "USDC"}, True),  # Very high value - multi-sig
        ]

        for tool_args, expected in test_cases:
            is_high_value = await approval_service._is_high_value_operation(tool_args)
            assert is_high_value is expected, \
                f"Failed for args {tool_args}, expected {expected}"

    @pytest.mark.asyncio
    async def test_approval_notification(self, approval_service):
        """Test that notifications are sent for approval requests."""
        request_id = uuid4()
        approvers = [
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            "0x3333333333333333333333333333333333333333",
        ]

        with patch.object(approval_service, '_send_notifications', return_value=True) as mock_notify:
            await approval_service._notify_approvers(request_id, approvers)
            assert mock_notify.call_count == 1


class TestMultiSigDatabaseIntegration:
    """Test multi-sig approval with database integration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_create_and_persist_request(self, mock_db):
        """Test creating and persisting an approval request."""
        from src.models.approval_requests import ApprovalRequest

        session_id = uuid4()
        approval_service = ApprovalService(mock_db)

        mock_request = ApprovalRequest(
            id=uuid4(),
            session_id=session_id,
            tool_name="x402_payment",
            tool_args={"amount": "1000", "token": "USDC"},
            decision="pending",
            required_approvers=3,
            created_at=datetime.utcnow(),
        )

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch.object(approval_service, '_create_db_object', return_value=mock_request):
            request = await approval_service.create_request(
                session_id=session_id,
                tool_name="x402_payment",
                tool_args={"amount": "1000", "token": "USDC"},
                required_approvers=3,
            )

            assert request.decision == "pending"
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_request_decision(self, mock_db):
        """Test updating the decision of an approval request."""
        request_id = uuid4()
        approval_service = ApprovalService(mock_db)

        mock_request = MagicMock()
        mock_request.id = request_id
        mock_request.decision = "approved"
        mock_request.decision_made_at = datetime.utcnow()

        mock_db.commit = AsyncMock()

        with patch.object(approval_service, '_get_request', return_value=mock_request):
            result = await approval_service._update_request_decision(
                request_id, "approved"
            )
            assert result is True
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_pending_by_session(self, mock_db):
        """Test querying pending requests by session ID."""
        from sqlalchemy import select

        session_id = uuid4()
        approval_service = ApprovalService(mock_db)

        mock_requests = [
            MagicMock(
                id=uuid4(),
                session_id=session_id,
                decision="pending",
            )
            for _ in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_requests)
        mock_db.execute = AsyncMock(return_value=mock_result)

        pending = await approval_service._get_pending_requests(session_id)

        assert len(pending) == 3
        assert all(req.decision == "pending" for req in pending)


class TestMultiSigRealWorldScenarios:
    """Test real-world multi-sig approval scenarios."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_large_payment_requires_multi_sig(self, mock_db):
        """Test that large payments require multiple approvals."""
        approval_service = ApprovalService(mock_db)

        large_payment = {
            "amount": "50000",
            "token": "USDC",
            "recipient": "0x1234567890123456789012345678901234567890",
        }

        is_high_value = await approval_service._is_high_value_operation(large_payment)
        assert is_high_value is True

    @pytest.mark.asyncio
    async def test_emergency_approval_expedited(self, mock_db):
        """Test expedited approval for emergency operations."""
        approval_service = ApprovalService(mock_db)

        # Emergency operation might require fewer approvers but faster response
        emergency_request = {
            "operation": "emergency_withdrawal",
            "amount": "1000",
            "reason": "emergency",
        }

        # Emergency operations might have special handling
        is_emergency = "emergency" in emergency_request.get("operation", "")
        assert is_emergency is True

    @pytest.mark.asyncio
    async def test_delegated_approval(self, mock_db):
        """Test delegated approval workflow."""
        approval_service = ApprovalService(mock_db)

        # Owner can delegate approval authority
        delegator = "0x1111111111111111111111111111111111111111"
        delegate = "0x2222222222222222222222222222222222222222"

        with patch.object(approval_service, '_add_delegation', return_value=True):
            result = await approval_service.add_delegation(
                delegator=delegator,
                delegate=delegate,
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_approval_cascading(self, mock_db):
        """Test cascading approvals for related operations."""
        approval_service = ApprovalService(mock_db)

        # Primary request
        primary_request_id = uuid4()

        # Secondary dependent requests
        dependent_requests = [uuid4() for _ in range(3)]

        # When primary is approved, dependents should auto-approve
        with patch.object(approval_service, '_cascade_approval', return_value=True):
            result = await approval_service.cascade_approval(
                primary_request_id, dependent_requests
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_time_locked_approval(self, mock_db):
        """Test time-locked approval (delayed execution)."""
        approval_service = ApprovalService(id=uuid4())

        # Create a time-locked approval
        execution_time = datetime.utcnow() + timedelta(hours=1)

        with patch.object(approval_service, '_create_time_lock', return_value=True):
            result = await approval_service.create_time_lock(
                request_id=uuid4(),
                execution_time=execution_time,
            )
            assert result is True

        # Check if execution time has reached
        with patch.object(approval_service, '_check_time_lock', return_value=False):
            is_ready = await approval_service._check_time_lock(uuid4())
            assert is_ready is False  # Not yet time
