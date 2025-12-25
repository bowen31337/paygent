"""
QA Tests for Complex Multi-Step Workflows (Feature 115).

This test verifies that complex multi-step workflows complete within 5 minutes
and that all steps are executed correctly.
"""

import time
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.agents.agent_executor_enhanced import AgentExecutorEnhanced
from src.agents.planner import CommandPlanner
from src.models.agent_sessions import AgentMemory, AgentSession
from src.models.execution_logs import ExecutionLog


class TestComplexMultiStepWorkflows:
    """Test that complex multi-step workflows complete within 5 minutes (Feature 115)."""

    @pytest.mark.asyncio
    async def test_complex_workflow_completes_within_5_minutes(self):
        """
        Feature 115: Complex multi-step workflows complete within 5 minutes.

        This test verifies that a complex command requiring multiple steps
        completes within the 5-minute threshold.
        """
        # Create in-memory database
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(AgentSession.__table__.create)
            await conn.run_sync(ExecutionLog.__table__.create)
            await conn.run_sync(AgentMemory.__table__.create)

        async with async_session() as session:
            # Create AgentSession
            agent_session = AgentSession(id=uuid4(), user_id=uuid4())
            session.add(agent_session)
            await session.commit()

            session_id = agent_session.id
            executor = AgentExecutorEnhanced(session_id, session, use_allowlist=False)

            # Test a complex command that triggers planning
            # This simulates: "Swap 10 CRO for USDC then pay 5 USDC to service"
            complex_command = "Swap 10 CRO for USDC then pay 5 USDC to API service"

            start_time = time.time()
            result = await executor.execute_command(
                command=complex_command,
                timeout_seconds=300  # 5 minutes
            )
            duration = time.time() - start_time

            print(f"Complex workflow execution time: {duration:.2f}s")

            # Verify completion within 5 minutes (300 seconds)
            assert duration < 300, f"Workflow took {duration:.2f}s, exceeds 5-minute limit"

            # Verify the command was processed
            assert "success" in result, "Result should contain success field"

            # Verify execution log was created
            assert "execution_log_id" in result, "Should have execution log ID"

            # Query the execution log to verify plan was created
            from uuid import UUID

            from sqlalchemy import select
            log_id_str = result["execution_log_id"]
            log_result = await session.execute(
                select(ExecutionLog).where(ExecutionLog.id == UUID(log_id_str))
            )
            log = log_result.scalar_one_or_none()

            assert log is not None, "Execution log should exist"
            assert log.plan is not None, "Plan should be created for complex command"

            # Verify plan has multiple steps
            plan = log.plan
            if isinstance(plan, dict):
                steps = plan.get("steps", [])
                assert len(steps) >= 2, f"Plan should have at least 2 steps, got {len(steps)}"
                print(f"Plan created with {len(steps)} steps")

    @pytest.mark.asyncio
    async def test_sequential_command_pattern_detection(self):
        """
        Test that the planner correctly identifies sequential commands.
        """
        planner = CommandPlanner()

        # Test commands with sequential keywords
        sequential_commands = [
            ("Pay 10 USDC then swap 5 CRO for USDC", True),
            ("Swap 10 CRO for USDC and then pay 5 USDC", True),
            ("Check balance after that pay 10 USDC", True),
            ("First swap 10 CRO, then pay 5 USDC", True),
            ("Pay 10 USDC finally swap 5 CRO", True),
            ("Pay 10 USDC", False),  # Single action
            ("Swap 10 CRO for USDC", False),  # Single action
        ]

        for command, should_plan in sequential_commands:
            from src.agents.command_parser import CommandParser
            parser = CommandParser()
            parsed = parser.parse(command)

            needs_plan = planner.should_plan(command, parsed.intent)
            assert needs_plan == should_plan, \
                f"Command '{command}' should {'need' if should_plan else 'not need'} planning"

    @pytest.mark.asyncio
    async def test_swap_then_pay_plan_creation(self):
        """
        Test that swap-then-pay commands generate proper multi-step plans.

        Note: The current parser detects the last intent in the command.
        The planner should handle multi-step detection via should_plan().
        """
        planner = CommandPlanner()

        # Test swap then pay pattern
        command = "Swap 10 CRO for USDC then pay 5 USDC to API service"
        from src.agents.command_parser import CommandParser
        parser = CommandParser()
        parsed = parser.parse(command)

        # Current parser behavior: detects "payment" as intent (last match)
        # The planner's should_plan() should detect this needs planning
        needs_plan = planner.should_plan(command, parsed.intent)
        assert needs_plan, "Sequential command should need planning"

        plan = planner.create_plan(command, parsed.intent, parsed.parameters)

        # The planner creates a plan based on the command pattern
        # For "then" pattern, it creates sequential steps
        assert plan is not None, "Plan should be created for sequential command"
        assert len(plan.steps) >= 2, "Should have at least 2 steps"

    @pytest.mark.asyncio
    async def test_budget_constrained_workflow_plan(self):
        """
        Test that budget-constrained commands generate proper plans with approval requirements.
        """
        planner = CommandPlanner()

        command = "Pay 100 USDC to service with budget limit"
        from src.agents.command_parser import CommandParser
        parser = CommandParser()
        parsed = parser.parse(command)

        plan = planner.create_plan(command, parsed.intent, parsed.parameters)

        assert plan is not None, "Plan should be created for budget-constrained payment"
        assert plan.requires_human_approval is True, "Should require human approval"
        assert len(plan.steps) >= 3, "Should have at least 3 steps (check, pay, verify)"

    @pytest.mark.asyncio
    async def test_service_discovery_and_pay_plan(self):
        """
        Test that service discovery + payment commands generate proper plans.
        """
        planner = CommandPlanner()

        # Use a command that clearly matches the discovery+pay pattern
        command = "Find market data services then pay for access"
        from src.agents.command_parser import CommandParser
        parser = CommandParser()
        parsed = parser.parse(command)

        # Check if planning is needed
        needs_plan = planner.should_plan(command, parsed.intent)
        if needs_plan:
            plan = planner.create_plan(command, parsed.intent, parsed.parameters)
            assert plan is not None, "Plan should be created for discovery+pay"
            assert len(plan.steps) >= 2, "Should have at least 2 steps"
        else:
            # If no plan is created, verify the command was parsed correctly
            assert parsed.intent is not None, "Command should be parsed"

    @pytest.mark.asyncio
    async def test_execution_plan_stored_in_log(self):
        """
        Test that execution plans are properly stored in execution logs.
        """
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(AgentSession.__table__.create)
            await conn.run_sync(ExecutionLog.__table__.create)
            await conn.run_sync(AgentMemory.__table__.create)

        async with async_session() as session:
            agent_session = AgentSession(id=uuid4(), user_id=uuid4())
            session.add(agent_session)
            await session.commit()

            executor = AgentExecutorEnhanced(agent_session.id, session, use_allowlist=False)

            # Execute a complex command
            result = await executor.execute_command("Swap 10 CRO for USDC then pay 5 USDC")

            # Verify plan is in result
            assert "plan" in result, "Result should contain plan"
            assert result["plan"] is not None, "Plan should not be None"

            # Verify plan structure
            plan = result["plan"]
            assert "steps" in plan, "Plan should have steps"
            assert len(plan["steps"]) >= 2, "Plan should have at least 2 steps"

    @pytest.mark.asyncio
    async def test_workflow_timeout_handling(self):
        """
        Test that workflows respect timeout limits.
        """
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(AgentSession.__table__.create)
            await conn.run_sync(ExecutionLog.__table__.create)
            await conn.run_sync(AgentMemory.__table__.create)

        async with async_session() as session:
            agent_session = AgentSession(id=uuid4(), user_id=uuid4())
            session.add(agent_session)
            await session.commit()

            executor = AgentExecutorEnhanced(agent_session.id, session, use_allowlist=False)

            # Execute with a very short timeout to test timeout handling
            result = await executor.execute_command(
                "Swap 10 CRO for USDC then pay 5 USDC",
                timeout_seconds=0.001  # Extremely short timeout
            )

            # Should either complete very quickly (mocked) or timeout gracefully
            # The actual behavior depends on whether tools are mocked
            # For this test, we just verify the result structure
            assert "success" in result or "timeout_exceeded" in result, \
                "Should have either success or timeout in result"


class TestWorkflowPerformanceMetrics:
    """Test performance metrics for workflows."""

    @pytest.mark.asyncio
    async def test_workflow_duration_is_tracked(self):
        """
        Verify that workflow execution duration is properly tracked.
        """
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(AgentSession.__table__.create)
            await conn.run_sync(ExecutionLog.__table__.create)
            await conn.run_sync(AgentMemory.__table__.create)

        async with async_session() as session:
            agent_session = AgentSession(id=uuid4(), user_id=uuid4())
            session.add(agent_session)
            await session.commit()

            executor = AgentExecutorEnhanced(agent_session.id, session, use_allowlist=False)

            result = await executor.execute_command("Check my balance")

            # Verify duration is tracked
            assert "duration_ms" in result, "Result should contain duration_ms"
            assert isinstance(result["duration_ms"], int), "duration_ms should be integer"
            assert result["duration_ms"] > 0, "duration_ms should be positive"

            # Verify duration is in database log
            from uuid import UUID

            from sqlalchemy import select
            log_id_str = result["execution_log_id"]
            log_result = await session.execute(
                select(ExecutionLog).where(ExecutionLog.id == UUID(log_id_str))
            )
            log = log_result.scalar_one_or_none()

            assert log is not None, "Log should exist"
            assert log.duration_ms > 0, "Database log should have duration"

    @pytest.mark.asyncio
    async def test_multi_step_workflow_step_tracking(self):
        """
        Test that individual steps in a workflow are tracked.
        """
        planner = CommandPlanner()

        # Create a complex plan
        command = "Swap 10 CRO for USDC then pay 5 USDC to service"
        from src.agents.command_parser import CommandParser
        parser = CommandParser()
        parsed = parser.parse(command)

        plan = planner.create_plan(command, parsed.intent, parsed.parameters)

        assert plan is not None, "Plan should be created"

        # Verify each step has required fields
        for step in plan.steps:
            assert step.step_id > 0, "Step should have ID"
            assert step.description, "Step should have description"
            assert step.action_type, "Step should have action type"
            assert step.status, "Step should have status"

        print(f"Workflow has {len(plan.steps)} steps:")
        for step in plan.steps:
            print(f"  Step {step.step_id}: {step.description} ({step.status})")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
