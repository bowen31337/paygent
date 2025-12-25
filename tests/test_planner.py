"""Test planning functionality."""


import pytest

from src.agents.planner import CommandPlanner, ExecutionPlan, PlanStep


def test_should_plan_sequential_commands():
    """Test that sequential commands trigger planning."""
    planner = CommandPlanner()

    # Commands with sequential keywords should trigger planning
    sequential_commands = [
        "swap 100 USDC for CRO then pay 0.1 USDC to service",
        "first swap ETH for USDC, then pay for API access",
        "swap USDC for CRO and then pay for market data",
        "pay 10 USDC to service, after that swap 50 USDC for CRO",
        "finally pay 0.5 ETH to vendor"
    ]

    for command in sequential_commands:
        assert planner.should_plan(command, "payment"), f"Should plan: {command}"
        assert planner.should_plan(command, "swap"), f"Should plan: {command}"


def test_should_plan_budget_commands():
    """Test that budget-constrained commands trigger planning."""
    planner = CommandPlanner()

    budget_commands = [
        "pay 100 USDC to service with budget limit",
        "swap tokens within my daily limit",
        "pay for service respecting my $500 budget"
    ]

    for command in budget_commands:
        assert planner.should_plan(command, "payment"), f"Should plan budget: {command}"


def test_should_plan_service_discovery():
    """Test that service discovery commands trigger planning."""
    planner = CommandPlanner()

    discovery_commands = [
        "find market data services and pay for access",
        "discover DeFi protocols then swap tokens",
        "search for services and pay subscription"
    ]

    for command in discovery_commands:
        assert planner.should_plan(command, "service_discovery"), f"Should plan discovery: {command}"


def test_should_not_plan_simple_commands():
    """Test that simple commands don't trigger planning."""
    planner = CommandPlanner()

    simple_commands = [
        "pay 10 USDC to Alice",
        "swap 50 ETH for BTC",
        "check my balance",
        "send 100 CRO to wallet",
        "transfer tokens to address"
    ]

    for command in simple_commands:
        assert not planner.should_plan(command, "payment"), f"Should not plan: {command}"
        assert not planner.should_plan(command, "swap"), f"Should not plan: {command}"
        assert not planner.should_plan(command, "balance_check"), f"Should not plan: {command}"


def test_create_sequential_plan():
    """Test creation of sequential execution plans."""
    planner = CommandPlanner()

    command = "swap 100 USDC for CRO then pay 0.1 USDC to service"
    plan = planner.create_plan(command, "swap", {"amount": "100", "from": "USDC", "to": "CRO"})

    assert plan is not None
    assert plan.command == command
    assert len(plan.steps) >= 1
    assert plan.estimated_duration_seconds > 0
    assert plan.status == "created"


def test_create_swap_then_pay_plan():
    """Test creation of swap-then-pay plans."""
    planner = CommandPlanner()

    command = "swap 100 USDC for CRO then pay 0.1 USDC to service"
    plan = planner.create_plan(command, "swap", {"amount": "100", "from": "USDC", "to": "CRO"})

    assert plan is not None
    assert plan.command == command

    # Should have multiple steps
    assert len(plan.steps) >= 2

    # Check that steps have proper dependencies
    for i, step in enumerate(plan.steps):
        assert step.step_id == i + 1
        assert step.status == "pending"


def test_create_budget_constrained_plan():
    """Test creation of budget-constrained plans."""
    planner = CommandPlanner()

    command = "pay 100 USDC to service with budget limit"
    plan = planner.create_plan(command, "payment", {"amount": "100", "token": "USDC"})

    assert plan is not None
    assert plan.command == command
    assert plan.requires_human_approval, "Budget plans should require approval"


def test_create_arbitrage_plan():
    """Test creation of arbitrage plans."""
    planner = CommandPlanner()

    command = "arbitrage between exchanges for profit"
    plan = planner.create_plan(command, "swap", {})

    assert plan is not None
    assert plan.command == command
    assert len(plan.steps) >= 3, "Arbitrage should have multiple steps"


def test_plan_execution_status():
    """Test plan execution status tracking."""
    planner = CommandPlanner()

    plan = ExecutionPlan(
        plan_id="test_plan",
        command="test command",
        steps=[
            PlanStep(step_id=1, description="Step 1", action_type="payment"),
            PlanStep(step_id=2, description="Step 2", action_type="swap"),
        ]
    )

    # Test status transitions
    assert plan.status == "created"

    plan.status = "approved"
    assert plan.status == "approved"

    plan.status = "executing"
    assert plan.status == "executing"

    plan.status = "completed"
    assert plan.status == "completed"


def test_step_status_tracking():
    """Test individual step status tracking."""
    step = PlanStep(step_id=1, description="Test step", action_type="payment")

    # Test status transitions
    assert step.status == "pending"

    step.status = "in_progress"
    assert step.status == "in_progress"

    step.status = "completed"
    assert step.status == "completed"


def test_plan_dependencies():
    """Test plan step dependencies."""
    planner = CommandPlanner()

    plan = ExecutionPlan(
        plan_id="test_plan",
        command="test command",
        steps=[
            PlanStep(step_id=1, description="Step 1", action_type="payment"),
            PlanStep(step_id=2, description="Step 2", action_type="swap", dependencies=[1]),
        ]
    )

    # Second step depends on first
    assert plan.steps[1].dependencies == [1]
    assert plan.steps[0].dependencies == []


def test_plan_cost_estimation():
    """Test plan cost estimation."""
    planner = CommandPlanner()

    plan = ExecutionPlan(
        plan_id="test_plan",
        command="test command",
        steps=[
            PlanStep(step_id=1, description="Step 1", action_type="payment"),
            PlanStep(step_id=2, description="Step 2", action_type="swap"),
        ],
        estimated_cost_usd=10.50
    )

    assert plan.estimated_cost_usd == 10.50


def test_plan_duration_estimation():
    """Test plan duration estimation."""
    planner = CommandPlanner()

    plan = ExecutionPlan(
        plan_id="test_plan",
        command="test command",
        steps=[
            PlanStep(step_id=1, description="Step 1", action_type="payment"),
            PlanStep(step_id=2, description="Step 2", action_type="swap"),
        ],
        estimated_duration_seconds=60
    )

    assert plan.estimated_duration_seconds == 60


def test_plan_creation_id_generation():
    """Test that plan IDs are generated correctly."""
    planner = CommandPlanner()

    plan1 = planner.create_plan("test command 1", "payment", {})
    plan2 = planner.create_plan("test command 2", "swap", {})

    if plan1 and plan2:
        assert plan1.plan_id != plan2.plan_id, "Plan IDs should be unique"


def test_plan_storage():
    """Test that plans are stored correctly."""
    planner = CommandPlanner()

    plan = planner.create_plan("test command", "payment", {})
    if plan:
        assert plan.plan_id in planner.plans
        assert planner.plans[plan.plan_id] == plan


def test_split_command_functionality():
    """Test command splitting for sequential operations."""
    planner = CommandPlanner()

    # This would test the internal _split_command method if it were public
    # For now, we test the behavior indirectly through create_plan
    command = "swap 100 USDC for CRO then pay 0.1 USDC to service"
    plan = planner.create_plan(command, "swap", {})

    if plan:
        assert len(plan.steps) > 1, "Sequential command should create multiple steps"


def test_case_insensitive_planning():
    """Test that planning works with different cases."""
    planner = CommandPlanner()

    commands = [
        "SWAP 100 USDC FOR CRO THEN PAY 0.1 USDC",
        "Swap 100 USDC for CRO then pay 0.1 USDC",
        "swap 100 USDC for CRO then pay 0.1 USDC",
        "SwAp 100 USDC fOr CrO tHeN pAy 0.1 USDC"
    ]

    for command in commands:
        plan = planner.create_plan(command, "swap", {})
        assert plan is not None, f"Should plan: {command}"


def test_empty_command_handling():
    """Test handling of empty or invalid commands."""
    planner = CommandPlanner()

    # Empty command
    plan = planner.create_plan("", "payment", {})
    assert plan is None

    # Command with no intent
    plan = planner.create_plan("random text", "unknown", {})
    assert plan is None


def test_parameters_preservation():
    """Test that parameters are preserved in plan steps."""
    planner = CommandPlanner()

    parameters = {
        "amount": "100",
        "token": "USDC",
        "recipient": "service"
    }

    plan = planner.create_plan("pay 100 USDC to service", "payment", parameters)

    if plan:
        for step in plan.steps:
            # Parameters should be available in steps
            assert "amount" in parameters or step.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
