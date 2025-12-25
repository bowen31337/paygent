"""
Test agent transaction audit trail.

This test verifies that the agent maintains a complete audit trail of all
transactions including commands, tool calls, results, costs, and timing.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.audit_service import AuditService


@pytest.mark.asyncio
class TestAgentAuditTrail:
    """Test agent transaction audit trail functionality."""

    async def test_create_execution_log(self, db_session: AsyncSession):
        """Test creating an execution log entry."""
        audit_service = AuditService(db_session)

        session_id = uuid4()
        command = "Pay 0.10 USDC to API service"
        plan = {
            "steps": [
                {"description": "Check wallet balance", "status": "pending"},
                {"description": "Execute payment", "status": "pending"},
            ]
        }

        log = await audit_service.create_execution_log(
            session_id=session_id,
            command=command,
            plan=plan,
        )

        assert log is not None
        assert log.id is not None
        assert log.session_id == session_id
        assert log.command == command
        assert log.plan == plan
        assert log.created_at is not None

    async def test_update_execution_log_with_results(self, db_session: AsyncSession):
        """Test updating execution log with execution results."""
        audit_service = AuditService(db_session)

        # Create initial log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Check my wallet balance",
        )

        # Update with results
        tool_calls = [
            {
                "tool": "check_balance",
                "args": {"token": "USDC"},
                "result": {"balance": 100.0},
            }
        ]
        result = {"status": "success", "balance": 100.0}
        total_cost_usd = 0.001
        duration_ms = 1500

        updated_log = await audit_service.update_execution_log(
            log_id=log.id,
            tool_calls=tool_calls,
            result=result,
            total_cost_usd=total_cost_usd,
            duration_ms=duration_ms,
        )

        assert updated_log.id == log.id
        assert updated_log.tool_calls == tool_calls
        assert updated_log.result == result
        assert updated_log.total_cost_usd == total_cost_usd
        assert updated_log.duration_ms == duration_ms

    async def test_record_tool_call(self, db_session: AsyncSession):
        """Test recording individual tool calls."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Swap 10 CRO for USDC",
        )

        # Record tool call
        tool_call = await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="swap_tokens",
            tool_args={"from_token": "CRO", "to_token": "USDC", "amount": 10},
            tool_result={"amount_out": 7.5, "tx_hash": "0x123"},
            success=True,
            duration_ms=1200,
        )

        assert tool_call is not None
        assert tool_call.id is not None
        assert tool_call.execution_log_id == log.id
        assert tool_call.tool_name == "swap_tokens"
        assert tool_call.success is True
        assert tool_call.duration_ms == 1200

    async def test_record_failed_tool_call(self, db_session: AsyncSession):
        """Test recording failed tool calls."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Pay 1000 USDC to service",
        )

        # Record failed tool call
        tool_call = await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="execute_payment",
            tool_args={"amount": 1000, "token": "USDC"},
            success=False,
            error_message="Insufficient balance",
            duration_ms=500,
        )

        assert tool_call.success is False
        assert tool_call.error_message == "Insufficient balance"
        assert tool_call.tool_result is None

    async def test_get_execution_log(self, db_session: AsyncSession):
        """Test retrieving an execution log by ID."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Check my wallet balance",
        )

        # Retrieve log
        retrieved_log = await audit_service.get_execution_log(log.id)

        assert retrieved_log is not None
        assert retrieved_log["id"] == str(log.id)
        assert retrieved_log["session_id"] == str(session_id)
        assert retrieved_log["command"] == "Check my wallet balance"

    async def test_get_session_execution_logs(self, db_session: AsyncSession):
        """Test retrieving all execution logs for a session."""
        audit_service = AuditService(db_session)

        # Create session with multiple execution logs
        session_id = uuid4()

        log1 = await audit_service.create_execution_log(
            session_id=session_id,
            command="Check balance",
        )
        log2 = await audit_service.create_execution_log(
            session_id=session_id,
            command="Swap tokens",
        )
        log3 = await audit_service.create_execution_log(
            session_id=session_id,
            command="Pay for service",
        )

        # Get all session logs
        session_logs = await audit_service.get_session_execution_logs(session_id)

        assert session_logs["session_id"] == str(session_id)
        assert session_logs["total"] == 3
        assert len(session_logs["execution_logs"]) == 3

        # Verify order (newest first)
        commands = [log["command"] for log in session_logs["execution_logs"]]
        assert commands == ["Pay for service", "Swap tokens", "Check balance"]

    async def test_get_tool_calls_for_execution_log(self, db_session: AsyncSession):
        """Test retrieving all tool calls for an execution log."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Multi-step workflow",
        )

        # Record multiple tool calls
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="check_balance",
            tool_args={"token": "CRO"},
            tool_result={"balance": 100.0},
            success=True,
        )
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="swap_tokens",
            tool_args={"from": "CRO", "to": "USDC", "amount": 10},
            tool_result={"amount_out": 7.5},
            success=True,
        )
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="execute_payment",
            tool_args={"amount": 5, "token": "USDC"},
            success=False,
            error_message="Service unavailable",
        )

        # Get tool calls
        tool_calls = await audit_service.get_tool_calls(log.id)

        assert len(tool_calls) == 3
        assert tool_calls[0]["tool_name"] == "check_balance"
        assert tool_calls[1]["tool_name"] == "swap_tokens"
        assert tool_calls[2]["tool_name"] == "execute_payment"
        assert tool_calls[0]["success"] is True
        assert tool_calls[1]["success"] is True
        assert tool_calls[2]["success"] is False

    async def test_complete_audit_trail(self, db_session: AsyncSession):
        """Test complete audit trail from command to tool calls to results."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        command = "Pay 0.10 USDC to access the market data API"

        log = await audit_service.create_execution_log(
            session_id=session_id,
            command=command,
            plan={
                "steps": [
                    {"description": "Check wallet balance", "status": "completed"},
                    {"description": "Execute x402 payment", "status": "completed"},
                ]
            },
        )

        # Record tool calls
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="check_balance",
            tool_args={"token": "USDC"},
            tool_result={"balance": 100.0},
            success=True,
            duration_ms=50,
        )
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="execute_x402_payment",
            tool_args={
                "service_url": "https://api.example.com/data",
                "amount": 0.10,
                "token": "USDC",
            },
            tool_result={
                "tx_hash": "0xabcdef123456",
                "status": "confirmed",
                "gas_used": 21000,
            },
            success=True,
            duration_ms=200,
        )

        # Update with final result
        await audit_service.update_execution_log(
            log_id=log.id,
            result={"status": "success", "service_access_granted": True},
            total_cost_usd=0.002,
            duration_ms=250,
        )

        # Retrieve complete audit trail
        audit_trail = await audit_service.get_execution_log(log.id)
        tool_calls = await audit_service.get_tool_calls(log.id)

        # Verify all components
        assert audit_trail is not None
        assert audit_trail["command"] == command
        assert audit_trail["plan"] is not None
        assert audit_trail["result"]["status"] == "success"
        assert audit_trail["total_cost_usd"] == 0.002
        assert audit_trail["duration_ms"] == 250

        assert len(tool_calls) == 2
        assert tool_calls[0]["tool_name"] == "check_balance"
        assert tool_calls[1]["tool_name"] == "execute_x402_payment"
        assert tool_calls[1]["tool_result"]["tx_hash"] == "0xabcdef123456"

    async def test_session_execution_logs_pagination(self, db_session: AsyncSession):
        """Test pagination of session execution logs."""
        audit_service = AuditService(db_session)

        # Create session with many execution logs
        session_id = uuid4()
        for i in range(15):
            await audit_service.create_execution_log(
                session_id=session_id,
                command=f"Command {i}",
            )

        # Test pagination
        page1 = await audit_service.get_session_execution_logs(session_id, offset=0, limit=10)
        assert page1["total"] == 15
        assert len(page1["execution_logs"]) == 10

        page2 = await audit_service.get_session_execution_logs(session_id, offset=10, limit=10)
        assert len(page2["execution_logs"]) == 5

    async def test_timestamps_accuracy(self, db_session: AsyncSession):
        """Test that timestamps are accurately recorded."""
        audit_service = AuditService(db_session)

        before_creation = datetime.utcnow()

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Test command",
        )

        after_creation = datetime.utcnow()

        # Verify timestamp
        assert log.created_at is not None
        assert before_creation <= log.created_at <= after_creation

        # Record tool call
        tool_call = await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="test_tool",
            tool_args={},
        )

        assert tool_call.created_at is not None
        assert tool_call.created_at >= log.created_at

    async def test_transaction_hashes_recorded(self, db_session: AsyncSession):
        """Test that blockchain transaction hashes are recorded in tool calls."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Execute blockchain payment",
        )

        # Record tool call with transaction hash
        tx_hash = "0x1234567890abcdef1234567890abcdef12345678"
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="execute_payment",
            tool_args={"amount": 10, "token": "USDC"},
            tool_result={"tx_hash": tx_hash, "status": "confirmed"},
            success=True,
        )

        # Retrieve and verify
        tool_calls = await audit_service.get_tool_calls(log.id)
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool_result"]["tx_hash"] == tx_hash

    async def test_amounts_and_recipients_recorded(self, db_session: AsyncSession):
        """Test that payment amounts and recipients are recorded."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Pay 0.50 USDC to 0xRecipient",
        )

        # Record payment tool call
        recipient = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        amount = 0.50
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="execute_payment",
            tool_args={"recipient": recipient, "amount": amount, "token": "USDC"},
            tool_result={"tx_hash": "0x987654", "status": "confirmed"},
            success=True,
        )

        # Retrieve and verify
        tool_calls = await audit_service.get_tool_calls(log.id)
        assert tool_calls[0]["tool_args"]["recipient"] == recipient
        assert tool_calls[0]["tool_args"]["amount"] == amount
        assert tool_calls[0]["tool_args"]["token"] == "USDC"

    async def test_gas_costs_recorded(self, db_session: AsyncSession):
        """Test that gas costs are recorded in tool calls."""
        audit_service = AuditService(db_session)

        # Create execution log
        session_id = uuid4()
        log = await audit_service.create_execution_log(
            session_id=session_id,
            command="Execute blockchain transaction",
        )

        # Record tool call with gas information
        gas_used = 45000
        gas_price_gwei = 25
        await audit_service.record_tool_call(
            execution_log_id=log.id,
            tool_name="execute_payment",
            tool_args={"amount": 10, "token": "CRO"},
            tool_result={
                "tx_hash": "0x123",
                "gas_used": gas_used,
                "gas_price_gwei": gas_price_gwei,
                "gas_cost_usd": 0.001,
            },
            success=True,
        )

        # Retrieve and verify
        tool_calls = await audit_service.get_tool_calls(log.id)
        assert tool_calls[0]["tool_result"]["gas_used"] == gas_used
        assert tool_calls[0]["tool_result"]["gas_price_gwei"] == gas_price_gwei
        assert tool_calls[0]["tool_result"]["gas_cost_usd"] == 0.001
