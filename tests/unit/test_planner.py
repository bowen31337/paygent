"""
Tests for the agent planner module.
"""

import pytest
from datetime import datetime
from src.agents.planner import PlanStep, ExecutionPlan, CommandPlanner


class TestPlanStep:
    """Test PlanStep dataclass."""

    def test_create_plan_step_minimal(self):
        """Test creating a plan step with minimal parameters."""
        step = PlanStep(
            step_id=1,
            description="Check balance",
            action_type="balance_check"
        )

        assert step.step_id == 1
        assert step.description == "Check balance"
        assert step.action_type == "balance_check"
        assert step.parameters == {}
        assert step.dependencies == []
        assert step.requires_approval is False
        assert step.expected_outcome == ""
        assert step.status == "pending"

    def test_create_plan_step_full(self):
        """Test creating a plan step with all parameters."""
        step = PlanStep(
            step_id=1,
            description="Execute payment",
            action_type="payment",
            parameters={"amount": "100", "token": "USDC"},
            dependencies=[0],
            requires_approval=True,
            expected_outcome="Payment successful",
            status="pending"
        )

        assert step.step_id == 1
        assert step.parameters == {"amount": "100", "token": "USDC"}
        assert step.dependencies == [0]
        assert step.requires_approval is True
        assert step.expected_outcome == "Payment successful"

    def test_plan_step_status_update(self):
        """Test updating plan step status."""
        step = PlanStep(
            step_id=1,
            description="Test step",
            action_type="test"
        )

        assert step.status == "pending"
        step.status = "in_progress"
        assert step.status == "in_progress"
        step.status = "completed"
        assert step.status == "completed"


class TestExecutionPlan:
    """Test ExecutionPlan dataclass."""

    def test_create_execution_plan_minimal(self):
        """Test creating an execution plan with minimal parameters."""
        steps = [
            PlanStep(step_id=1, description="Step 1", action_type="test"),
            PlanStep(step_id=2, description="Step 2", action_type="test")
        ]

        plan = ExecutionPlan(
            plan_id="plan-123",
            command="Test command",
            steps=steps
        )

        assert plan.plan_id == "plan-123"
        assert plan.command == "Test command"
        assert len(plan.steps) == 2
        assert plan.estimated_cost_usd == 0.0
        assert plan.estimated_duration_seconds == 0
        assert plan.requires_human_approval is False
        assert plan.status == "created"
        assert isinstance(plan.created_at, datetime)

    def test_create_execution_plan_full(self):
        """Test creating an execution plan with all parameters."""
        steps = [
            PlanStep(step_id=1, description="Step 1", action_type="test")
        ]

        plan = ExecutionPlan(
            plan_id="plan-456",
            command="Complex command",
            steps=steps,
            estimated_cost_usd=1.5,
            estimated_duration_seconds=60,
            requires_human_approval=True,
            status="approved"
        )

        assert plan.estimated_cost_usd == 1.5
        assert plan.estimated_duration_seconds == 60
        assert plan.requires_human_approval is True
        assert plan.status == "approved"


class TestCommandPlanner:
    """Test CommandPlanner class."""

    def test_planner_initialization(self):
        """Test planner initializes correctly."""
        planner = CommandPlanner()
        assert planner.plans == {}
        assert isinstance(planner.plans, dict)

    def test_should_plan_with_sequential_keywords(self):
        """Test planning detection with sequential keywords."""
        planner = CommandPlanner()

        # Test various sequential keywords
        commands_with_keywords = [
            "Check balance then swap USDC for CRO",
            "Get price after that make a payment",
            "Approve allowance next execute payment",
            "Swap tokens and then check balance",
            "Do this first and finally do that"
        ]

        for command in commands_with_keywords:
            result = planner.should_plan(command, "swap")
            assert result is True, f"Failed for command: {command}"

    def test_should_plan_with_budget_constraints(self):
        """Test planning detection for budget-constrained payments."""
        planner = CommandPlanner()

        budget_commands = [
            "Make a payment with budget limit",
            "Execute payment with spending limit",
            "Pay 100 USDC within budget"
        ]

        for command in budget_commands:
            result = planner.should_plan(command, "payment")
            assert result is True, f"Failed for command: {command}"

    def test_should_plan_with_service_discovery_and_payment(self):
        """Test planning detection for service discovery + payment."""
        planner = CommandPlanner()

        service_commands = [
            "Find a service and pay for it",
            "Discover market data API and access it",
            "Search for oracle service and pay"
        ]

        for command in service_commands:
            result = planner.should_plan(command, "service_discovery")
            assert result is True, f"Failed for command: {command}"

    def test_should_not_plan_simple_commands(self):
        """Test that simple commands don't require planning."""
        planner = CommandPlanner()

        simple_commands = [
            ("Check my balance", "balance_check"),
            ("Swap 100 USDC for CRO", "swap"),
            ("Pay 50 USDC to merchant", "payment"),
            ("Get current price", "price_check")
        ]

        for command, intent in simple_commands:
            result = planner.should_plan(command, intent)
            assert result is False, f"Should not plan for: {command}"

    def test_should_plan_multi_step_defi(self):
        """Test planning detection for multi-step DeFi operations."""
        planner = CommandPlanner()

        defi_commands = [
            "Approve USDC then swap",
            "Check allowance and then swap tokens"
        ]

        for command in defi_commands:
            result = planner.should_plan(command, "swap")
            assert result is True, f"Failed for DeFi command: {command}"

    def test_plan_storage_and_retrieval(self):
        """Test storing and retrieving plans."""
        planner = CommandPlanner()

        steps = [
            PlanStep(step_id=1, description="Step 1", action_type="test")
        ]
        plan = ExecutionPlan(
            plan_id="test-plan",
            command="Test command",
            steps=steps
        )

        planner.plans["test-plan"] = plan

        assert "test-plan" in planner.plans
        assert planner.plans["test-plan"].plan_id == "test-plan"
        assert len(planner.plans) == 1

    def test_plan_removal(self):
        """Test removing plans from storage."""
        planner = CommandPlanner()

        steps = [
            PlanStep(step_id=1, description="Step 1", action_type="test")
        ]
        plan = ExecutionPlan(
            plan_id="test-plan",
            command="Test command",
            steps=steps
        )

        planner.plans["test-plan"] = plan
        assert len(planner.plans) == 1

        del planner.plans["test-plan"]
        assert len(planner.plans) == 0
        assert "test-plan" not in planner.plans

    def test_multiple_plans_management(self):
        """Test managing multiple plans simultaneously."""
        planner = CommandPlanner()

        for i in range(5):
            steps = [
                PlanStep(step_id=1, description=f"Step {i}", action_type="test")
            ]
            plan = ExecutionPlan(
                plan_id=f"plan-{i}",
                command=f"Command {i}",
                steps=steps
            )
            planner.plans[f"plan-{i}"] = plan

        assert len(planner.plans) == 5
        assert all(f"plan-{i}" in planner.plans for i in range(5))

    def test_case_insensitive_keyword_detection(self):
        """Test that keyword detection is case-insensitive."""
        planner = CommandPlanner()

        case_variations = [
            "Check Balance THEN Swap",
            "GET PRICE AFTER THAT make payment",
            "approve Next execute"
        ]

        for command in case_variations:
            result = planner.should_plan(command, "swap")
            assert result is True, f"Failed for case variation: {command}"

    def test_planning_with_empty_command(self):
        """Test planning detection with empty command."""
        planner = CommandPlanner()

        result = planner.should_plan("", "swap")
        assert result is False

    def test_planning_with_unknown_intent(self):
        """Test planning detection with unknown intent."""
        planner = CommandPlanner()

        result = planner.should_plan("check balance then swap", "unknown_intent")
        # Should still detect sequential keywords
        assert result is True
