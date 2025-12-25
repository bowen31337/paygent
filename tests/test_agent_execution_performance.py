"""
Test agent execution performance - ensure simple operations complete within 30 seconds.

This test verifies that the agent can execute simple commands quickly and efficiently.
Feature 114: Agent command execution completes within 30 seconds for simple operations
"""

import asyncio
import time
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.agent_executor_enhanced import AgentExecutorEnhanced
from src.core.database import async_session_maker


class TestAgentExecutionPerformance:
    """Test agent execution performance requirements."""

    @pytest.mark.asyncio
    async def test_simple_balance_check_completes_quickly(self):
        """
        Test that a simple balance check command completes within 5 seconds.

        This is a simple operation that should be very fast as it only queries
        wallet balances without making external API calls.
        """
        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            # Load memory (empty)
            await executor.load_memory()

            # Measure execution time
            start_time = time.time()

            # Execute simple balance check command
            result = await executor.execute_command("Check my wallet balance")

            execution_time = time.time() - start_time

            # Assert completion within 5 seconds (much faster than 30s requirement)
            assert execution_time < 5.0, f"Balance check took {execution_time:.2f}s, expected < 5s"

            # Assert result is successful
            assert result is not None
            assert result.get("success") is True or "status" in result

            print(f"✓ Balance check completed in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_simple_service_discovery_completes_quickly(self):
        """
        Test that service discovery completes within 10 seconds.

        Service discovery queries the database and returns available services.
        With caching, this should be very fast.
        """
        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            await executor.load_memory()

            start_time = time.time()

            # Execute service discovery command
            result = await executor.execute_command("What services are available?")

            execution_time = time.time() - start_time

            # Assert completion within 10 seconds
            assert execution_time < 10.0, f"Service discovery took {execution_time:.2f}s, expected < 10s"

            assert result is not None
            print(f"✓ Service discovery completed in {execution_time:.2f}s")

    @pytest.mark.asyncio
    async def test_command_parsing_is_fast(self):
        """
        Test that command parsing happens quickly (< 1 second).

        Command parsing is a local operation and should be extremely fast.
        """
        from src.agents.command_parser import CommandParser

        parser = CommandParser()
        test_commands = [
            "Check my wallet balance",
            "Pay 0.10 USDC to API service",
            "Swap 10 CRO for USDC",
            "What services are available?",
            "Show me my transaction history",
        ]

        start_time = time.time()

        for command in test_commands:
            parsed = parser.parse(command)
            assert parsed is not None
            assert parsed.intent is not None

        parsing_time = time.time() - start_time

        # All commands should parse in under 1 second total
        assert parsing_time < 1.0, f"Command parsing took {parsing_time:.2f}s, expected < 1s"

        avg_time = parsing_time / len(test_commands)
        print(f"✓ Parsed {len(test_commands)} commands in {parsing_time:.3f}s (avg: {avg_time:.3f}s per command)")

    @pytest.mark.asyncio
    async def test_memory_operations_are_fast(self):
        """
        Test that memory load/save operations are fast.

        Memory operations should complete quickly as they're simple DB operations.
        """
        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            # Test save memory performance
            start_time = time.time()

            for i in range(10):
                await executor.save_memory(
                    message_type="human",
                    content=f"Test message {i}",
                    metadata={"index": i}
                )

            save_time = time.time() - start_time

            # 10 memory saves should complete in under 2 seconds
            assert save_time < 2.0, f"Memory saves took {save_time:.2f}s, expected < 2s"

            # Test load memory performance
            start_time = time.time()
            await executor.load_memory()
            load_time = time.time() - start_time

            # Loading should be very fast
            assert load_time < 1.0, f"Memory load took {load_time:.2f}s, expected < 1s"

            print(f"✓ Saved 10 memories in {save_time:.3f}s, loaded in {load_time:.3f}s")

    @pytest.mark.asyncio
    async def test_simple_commands_meet_30_second_requirement(self):
        """
        Test that all simple commands meet the 30-second requirement.

        This is a comprehensive test that verifies the overall performance requirement.
        """
        simple_commands = [
            "Check my wallet balance",
            "What services are available?",
            "Show me the last payment",
        ]

        async with async_session_maker() as db:
            session_id = uuid4()
            executor = AgentExecutorEnhanced(session_id, db, use_allowlist=False)

            await executor.load_memory()

            results = []
            for command in simple_commands:
                start_time = time.time()

                try:
                    result = await executor.execute_command(command)
                    execution_time = time.time() - start_time

                    results.append({
                        "command": command,
                        "time": execution_time,
                        "success": result is not None
                    })

                    # Each command should complete within 30 seconds
                    assert execution_time < 30.0, f"Command '{command}' took {execution_time:.2f}s, exceeded 30s limit"

                except Exception as e:
                    # If command fails, we still count the time
                    execution_time = time.time() - start_time
                    results.append({
                        "command": command,
                        "time": execution_time,
                        "success": False,
                        "error": str(e)
                    })

            # Print summary
            print("\n" + "=" * 60)
            print("Simple Commands Performance Summary")
            print("=" * 60)
            for r in results:
                status = "✓" if r["success"] else "✗"
                print(f"{status} {r['command'][:40]:40s} - {r['time']:.2f}s")
            print("=" * 60)

            # Assert all commands completed successfully
            successful = sum(1 for r in results if r["success"])
            assert successful == len(simple_commands), f"Only {successful}/{len(simple_commands)} commands succeeded"

            # Assert average time is reasonable (should be much less than 30s)
            avg_time = sum(r["time"] for r in results) / len(results)
            assert avg_time < 15.0, f"Average execution time {avg_time:.2f}s is too high"
            print(f"Average execution time: {avg_time:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
