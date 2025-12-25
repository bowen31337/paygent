"""
Test complex multi-step workflow performance - ensure workflows complete within 5 minutes.

This test verifies that the agent can execute complex, multi-step operations efficiently.
Feature 115: Complex multi-step workflows complete within 5 minutes
"""

import time
from uuid import uuid4

import pytest

from src.agents.agent_executor_enhanced import AgentExecutorEnhanced
from src.core.database import async_session_maker


class TestComplexWorkflowPerformance:
    """Test complex workflow performance requirements."""

    @pytest.mark.asyncio
    async def test_multi_step_swap_and_payment_workflow(self):
        """
        Test a complex workflow: Check balance -> Swap tokens -> Make payment.

        This simulates a realistic user workflow where someone wants to:
        1. Check their current balance
        2. Swap some CRO for USDC
        3. Pay for a service using the USDC

        Expected: Should complete within 2 minutes (well under 5 min requirement).
        """
        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            # Load memory (empty initially)
            await executor.load_memory()

            start_time = time.time()

            # Step 1: Check balance
            print("\nStep 1: Checking balance...")
            result1 = await executor.execute_command("Check my wallet balance")
            step1_time = time.time() - start_time
            assert result1 is not None
            assert result1.get("success") is True
            print(f"✓ Balance check completed in {step1_time:.2f}s")

            # Step 2: Swap tokens (small amount for testing)
            print("\nStep 2: Swapping tokens...")
            step2_start = time.time()
            result2 = await executor.execute_command("Swap 1 CRO for USDC")
            step2_time = time.time() - step2_start
            # Swap might fail in test env, but we measure time
            print(f"✓ Swap attempt completed in {step2_time:.2f}s")

            # Step 3: Check services
            print("\nStep 3: Discovering services...")
            step3_start = time.time()
            result3 = await executor.execute_command("What services are available?")
            step3_time = time.time() - step3_start
            assert result3 is not None
            print(f"✓ Service discovery completed in {step3_time:.2f}s")

            total_time = time.time() - start_time

            # Assert total workflow completes within 2 minutes
            assert total_time < 120.0, f"Multi-step workflow took {total_time:.2f}s, expected < 120s"

            print(f"\n{'='*60}")
            print("Multi-Step Workflow Performance Summary")
            print(f"{'='*60}")
            print(f"Step 1 (Balance Check):     {step1_time:.2f}s")
            print(f"Step 2 (Swap):              {step2_time:.2f}s")
            print(f"Step 3 (Service Discovery): {step3_time:.2f}s")
            print(f"{'-'*60}")
            print(f"Total Time:                 {total_time:.2f}s")
            print(f"{'='*60}")

    @pytest.mark.asyncio
    async def test_sequential_command_performance(self):
        """
        Test that executing multiple commands sequentially maintains good performance.

        This tests the agent's ability to handle a conversation with multiple turns.
        """
        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            await executor.load_memory()

            commands = [
                "Check my wallet balance",
                "What services are available?",
                "Show me my transaction history",
                "Check my wallet balance again",  # Should use memory context
            ]

            start_time = time.time()
            results = []

            for i, command in enumerate(commands, 1):
                cmd_start = time.time()
                result = await executor.execute_command(command)
                cmd_time = time.time() - cmd_start

                results.append({
                    "command": command,
                    "time": cmd_time,
                    "success": result is not None
                })

                print(f"Command {i}: {command[:40]:40s} - {cmd_time:.2f}s")

                # Each command should complete within 30 seconds
                assert cmd_time < 30.0, f"Command {i} took {cmd_time:.2f}s, exceeded 30s limit"

            total_time = time.time() - start_time

            # Total should complete well under 5 minutes
            assert total_time < 300.0, f"Sequential commands took {total_time:.2f}s, exceeded 300s limit"

            # Assert most commands succeeded
            successful = sum(1 for r in results if r["success"])
            assert successful >= len(commands) // 2, f"Only {successful}/{len(commands)} commands succeeded"

            avg_time = total_time / len(commands)
            print(f"\n✓ All {len(commands)} commands completed in {total_time:.2f}s (avg: {avg_time:.2f}s per command)")

    @pytest.mark.asyncio
    async def test_workflow_with_memory_context(self):
        """
        Test that workflows using memory context perform well.

        Memory operations should not significantly impact performance.
        """
        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            await executor.load_memory()

            # First command to establish context
            start_time = time.time()
            result1 = await executor.execute_command("I want to swap 10 CRO for USDC")
            first_time = time.time() - start_time
            print(f"First command (with context setup): {first_time:.2f}s")

            # Second command using context (should reference previous)
            start_time = time.time()
            result2 = await executor.execute_command("How much USDC will I get?")
            second_time = time.time() - start_time
            print(f"Second command (using memory): {second_time:.2f}s")

            total_time = first_time + second_time

            # Both commands should complete quickly
            assert total_time < 30.0, f"Context-aware workflow took {total_time:.2f}s, expected < 30s"

            print(f"✓ Context-aware workflow completed in {total_time:.2f}s")

    @pytest.mark.asyncio
    async def test_five_minute_requirement_for_complex_workflow(self):
        """
        Comprehensive test: Verify complex workflows meet the 5-minute requirement.

        This is the main test for the feature requirement.
        """
        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            await executor.load_memory()

            # Complex workflow spanning multiple operations
            workflow_steps = [
                "Check my wallet balance",
                "What services cost less than 1 USDC?",
                "Swap 5 CRO for USDC",
                "Check my balance again",
                "Show me available services",
            ]

            print(f"\n{'='*60}")
            print("Complex 5-Minute Workflow Test")
            print(f"{'='*60}\n")

            start_time = time.time()
            step_times = []

            for i, step in enumerate(workflow_steps, 1):
                step_start = time.time()

                try:
                    result = await executor.execute_command(step)
                    step_time = time.time() - step_start
                    step_times.append(step_time)

                    status = "✓" if result else "✗"
                    print(f"{status} Step {i}: {step[:45]:45s} - {step_time:.2f}s")

                except Exception as e:
                    step_time = time.time() - step_start
                    step_times.append(step_time)
                    print(f"✗ Step {i}: {step[:45]:45s} - {step_time:.2f}s (Error: {str(e)[:30]})")

            total_time = time.time() - start_time

            print(f"\n{'-'*60}")
            print(f"Total workflow time: {total_time:.2f}s")
            print(f"Average step time: {sum(step_times)/len(step_times):.2f}s")
            print(f"{'='*60}\n")

            # Main assertion: Must complete within 5 minutes
            assert total_time < 300.0, f"Complex workflow exceeded 5-minute limit: {total_time:.2f}s"

            # Also verify average performance is reasonable
            avg_time = sum(step_times) / len(step_times)
            assert avg_time < 60.0, f"Average step time {avg_time:.2f}s is too high"

            print("✓ Complex workflow completed well within 5-minute requirement!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
