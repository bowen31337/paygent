"""
Agent execution API routes.

This module provides endpoints for executing natural language commands
via AI agents and managing agent sessions.
"""

import asyncio
import json
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.agent_executor_enhanced import AgentExecutorEnhanced, execute_agent_command_enhanced
from src.agents.command_parser import CommandParser
from src.core.database import get_db
from src.core.errors import validate_command_input
from src.models.agent_sessions import AgentSession
from src.services.metrics_service import metrics_collector
from src.tools.simple_tools import (
    CheckBalanceTool,
    DiscoverServicesTool,
    SwapTokensTool,
    X402PaymentTool,
)

router = APIRouter()


class ExecuteCommandRequest(BaseModel):
    """Request body for executing an agent command."""

    command: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Natural language command to execute",
        examples=["Pay 0.10 USDC to access the market data API"],
    )
    session_id: UUID | None = Field(
        default=None,
        description="Existing session ID to use, or None to create new session",
    )
    budget_limit_usd: float | None = Field(
        default=None,
        ge=0,
        description="Maximum budget for this command execution in USD",
    )


class ExecuteCommandResponse(BaseModel):
    """Response from executing an agent command."""

    session_id: UUID = Field(..., description="Session ID for this execution")
    status: str = Field(..., description="Execution status")
    result: dict | None = Field(default=None, description="Execution result")
    total_cost_usd: float | None = Field(
        default=None, description="Total cost of execution in USD"
    )


class SessionInfo(BaseModel):
    """Information about an agent session."""

    id: UUID
    user_id: UUID | None = None
    wallet_address: str | None = None
    config: dict | None = None
    created_at: str
    last_active: str
    status: str


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionInfo]
    total: int
    offset: int
    limit: int


async def get_or_create_session(
    db: AsyncSession,
    session_id: UUID | None = None,
    user_id: UUID | None = None,
    config: dict | None = None,
) -> AgentSession:
    """
    Get an existing session or create a new one.

    For testing purposes, we use a fixed user_id if not provided.
    """
    if session_id:
        result = await db.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            # Update last_active
            session.last_active = datetime.utcnow()
            await db.commit()
            return session

    # Create new session
    new_session = AgentSession(
        id=uuid4(),
        user_id=user_id or uuid4(),  # Generate user_id if not provided
        wallet_address=None,
        config=config or {},
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


@router.post(
    "/execute",
    response_model=ExecuteCommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute agent command",
    description="Execute a natural language command using the AI agent.",
)
async def execute_command(
    request: ExecuteCommandRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteCommandResponse:
    """
    Execute a natural language payment command.

    The agent will:
    1. Parse the command to understand intent
    2. Create an execution plan (write_todos)
    3. Execute tools as needed (payments, swaps, etc.)
    4. Log all tool calls to database
    5. Return the result

    For high-value operations, human-in-the-loop approval may be required.
    """
    # Validate and sanitize command input to prevent injection attacks
    try:
        safe_command = validate_command_input(request.command)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Get or create session
    session = await get_or_create_session(
        db,
        session_id=request.session_id,
        config={"budget_limit": request.budget_limit_usd} if request.budget_limit_usd else None
    )

    # Execute using enhanced agent executor (which handles all logging internally)
    try:
        result = await execute_agent_command_enhanced(
            command=safe_command,  # Use validated command
            session_id=session.id,
            db=db,
            budget_limit_usd=request.budget_limit_usd
        )

        return ExecuteCommandResponse(
            session_id=session.id,
            status="completed" if result.get("success") else "failed",
            result=result,
            total_cost_usd=result.get("total_cost_usd", 0.0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )


@router.post(
    "/stream",
    response_class=StreamingResponse,
    summary="Execute command with streaming",
    description="Execute a command and stream events via Server-Sent Events.",
)
async def execute_command_stream(
    request: ExecuteCommandRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Execute a command and stream execution events.

    Events include:
    - thinking: Agent is processing
    - tool_call: Agent invoked a tool
    - tool_result: Tool returned a result
    - approval_required: Human approval needed
    - complete: Execution finished
    - error: An error occurred

    Returns:
        StreamingResponse: Server-Sent Events stream with execution events
    """
    # Get or create session
    session = await get_or_create_session(
        db,
        session_id=request.session_id,
        config={"budget_limit": request.budget_limit_usd} if request.budget_limit_usd else None
    )

    async def event_generator():
        """
        Generator function that yields Server-Sent Events.
        """
        try:
            # Event 1: Thinking
            yield f"event: thinking\ndata: {dict_to_json({'message': 'Analyzing your command...', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Event 2: Parse command
            parser = CommandParser()
            parsed = parser.parse(request.command)

            # Event 3: Tool call based on intent
            if parsed.intent == "payment":
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'x402_payment', 'arguments': parsed.parameters, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.2)

                # Tool result
                tool = X402PaymentTool()
                temp_executor = AgentExecutorEnhanced(session.id, db)
                service_url = temp_executor._resolve_service_endpoint(parsed.parameters.get('recipient', 'api'))
                result = tool.run(
                    service_url=service_url,
                    amount=parsed.parameters['amount'],
                    token=parsed.parameters.get('token', 'USDC')
                )
                yield f"event: tool_result\ndata: {dict_to_json({'tool': 'x402_payment', 'result': result, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.1)

            elif parsed.intent == "swap":
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'swap_tokens', 'arguments': parsed.parameters, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.2)

                tool = SwapTokensTool()
                result = tool.run(
                    from_token=parsed.parameters['from_token'],
                    to_token=parsed.parameters['to_token'],
                    amount=parsed.parameters['amount']
                )
                yield f"event: tool_result\ndata: {dict_to_json({'tool': 'swap_tokens', 'result': result, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.1)

            elif parsed.intent == "balance_check":
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'check_balance', 'arguments': parsed.parameters, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.15)

                tool = CheckBalanceTool()
                result = tool.run(tokens=parsed.parameters.get('tokens', ['CRO', 'USDC']))
                yield f"event: tool_result\ndata: {dict_to_json({'tool': 'check_balance', 'result': result, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.1)

            elif parsed.intent == "service_discovery":
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'discover_services', 'arguments': parsed.parameters, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.15)

                tool = DiscoverServicesTool()
                result = tool.run(category=parsed.parameters.get('category'), mcp_compatible=True)
                yield f"event: tool_result\ndata: {dict_to_json({'tool': 'discover_services', 'result': result, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.1)

            elif parsed.intent == "perpetual_trade":
                # Event: Spawn Moonlander subagent
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'moonlander_trader_subagent', 'arguments': parsed.parameters, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.3)

                # Event: Execute trade
                direction = parsed.parameters.get('direction', 'long')
                symbol = parsed.parameters.get('symbol', 'BTC')
                yield f"event: thinking\ndata: {dict_to_json({'message': f'Opening {direction} position on {symbol}...', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.2)

            else:
                # General command - just thinking
                await asyncio.sleep(0.3)

            # Event 4: Complete - use enhanced executor for final result with logging
            result = await execute_agent_command_enhanced(
                command=request.command,
                session_id=session.id,
                db=db,
                budget_limit_usd=request.budget_limit_usd
            )
            yield f"event: complete\ndata: {dict_to_json({'result': result, 'session_id': str(session.id), 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        except Exception as e:
            # Error event
            yield f"event: error\ndata: {dict_to_json({'error': str(e), 'timestamp': datetime.utcnow().isoformat()})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def dict_to_json(data: dict) -> str:
    """Convert dict to JSON string for SSE."""
    return json.dumps(data)


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List agent sessions",
    description="Get a list of agent sessions with optional pagination.",
)
async def list_sessions(
    offset: int = 0,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """List all agent sessions with pagination."""
    # Build query
    query = select(AgentSession).offset(offset).limit(limit)
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Get total count
    count_query = select(AgentSession.id)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return SessionListResponse(
        sessions=[
            SessionInfo(
                id=session.id,
                user_id=session.user_id,
                wallet_address=session.wallet_address,
                config=session.config,
                created_at=session.created_at.isoformat(),
                last_active=session.last_active.isoformat(),
                status="active",
            )
            for session in sessions
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionInfo,
    summary="Get session details",
    description="Get detailed information about a specific agent session.",
)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionInfo:
    """Get details of a specific agent session."""
    result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return SessionInfo(
        id=session.id,
        user_id=session.user_id,
        wallet_address=session.wallet_address,
        config=session.config,
        created_at=session.created_at.isoformat(),
        last_active=session.last_active.isoformat(),
        status="active",
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Terminate session",
    description="Terminate an active agent session.",
)
async def terminate_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Terminate an active agent session."""
    result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Delete the session
    await db.delete(session)
    await db.commit()

    # Record metrics
    metrics_collector.record_session_terminated()

    return {"message": f"Session {session_id} terminated successfully", "session_id": str(session_id)}


class ExecuteStepRequest(BaseModel):
    """Request body for executing a single step in a workflow."""

    stepId: str = Field(..., description="Unique identifier for the step")
    stepName: str = Field(..., description="Human-readable name of the step")
    args: dict = Field(default={}, description="Arguments for the step execution")


class ExecuteStepResponse(BaseModel):
    """Response from executing a single step."""

    success: bool
    stepId: str
    stepName: str
    result: dict | None = None
    error: str | None = None
    executionTimeMs: int | None = None


@router.post(
    "/execute-step",
    response_model=ExecuteStepResponse,
    summary="Execute single workflow step",
    description="Execute a single step within a Vercel Workflow. This endpoint is used by workflows to execute individual steps with retry logic.",
)
async def execute_step(
    request: ExecuteStepRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteStepResponse:
    """
    Execute a single step within a Vercel Workflow.

    This endpoint is designed for use by Vercel Workflows to execute individual
    steps with proper error handling and retry logic. Each step represents a
    discrete operation that can be retried independently.

    Args:
        request: Step execution request with step ID, name, and arguments
        db: Database session dependency

    Returns:
        ExecuteStepResponse with success status and result or error
    """
    start_time = datetime.utcnow()

    try:
        step_id = request.stepId
        step_name = request.stepName
        args = request.args

        # Log step execution start
        print(f"Executing step {step_id}: {step_name} with args: {args}")

        # Execute step based on type
        if step_name == "parse-payment":
            result = await _execute_parse_payment_step(args)
        elif step_name == "check-balance":
            result = await _execute_check_balance_step(args)
        elif step_name == "execute-payment":
            result = await _execute_payment_step(args, db)
        elif step_name == "parse-swap":
            result = await _execute_parse_swap_step(args)
        elif step_name == "get-quote":
            result = await _execute_get_quote_step(args)
        elif step_name == "execute-swap":
            result = await _execute_swap_step(args, db)
        elif step_name == "parse-command":
            result = await _execute_parse_command_step(args)
        else:
            raise ValueError(f"Unknown step type: {step_name}")

        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ExecuteStepResponse(
            success=True,
            stepId=step_id,
            stepName=step_name,
            result=result,
            executionTimeMs=execution_time
        )

    except Exception as e:
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ExecuteStepResponse(
            success=False,
            stepId=request.stepId,
            stepName=request.stepName,
            error=str(e),
            executionTimeMs=execution_time
        )


async def _execute_parse_payment_step(args: dict) -> dict:
    """Execute payment parsing step."""
    from src.agents.command_parser import CommandParser

    command = args.get("command", "")
    parser = CommandParser()
    parsed = parser.parse(command)

    return {
        "intent": parsed.intent,
        "parameters": parsed.parameters,
        "confidence": parsed.confidence
    }


async def _execute_check_balance_step(args: dict) -> dict:
    """Execute balance checking step."""
    from src.tools.simple_tools import CheckBalanceTool

    tool = CheckBalanceTool()
    result = tool.run(tokens=args.get("tokens", ["CRO", "USDC"]))

    return {
        "balances": result.get("balances", {}),
        "total_usd_value": result.get("total_usd_value", 0.0)
    }


async def _execute_payment_step(args: dict, db: AsyncSession) -> dict:
    """Execute payment execution step."""
    from src.agents.agent_executor_enhanced import AgentExecutorEnhanced
    from src.tools.simple_tools import X402PaymentTool

    tool = X402PaymentTool()
    executor = AgentExecutorEnhanced(session_id=uuid4(), db=db)

    command = args.get("command", "")
    parser = CommandParser()
    parsed = parser.parse(command)

    service_url = executor._resolve_service_endpoint(parsed.parameters.get('recipient', 'api'))

    result = tool.run(
        service_url=service_url,
        amount=parsed.parameters['amount'],
        token=parsed.parameters.get('token', 'USDC')
    )

    return {
        "payment_result": result,
        "tx_hash": result.get("tx_hash"),
        "status": result.get("status")
    }


async def _execute_parse_swap_step(args: dict) -> dict:
    """Execute swap parsing step."""
    from src.agents.command_parser import CommandParser

    command = args.get("command", "")
    parser = CommandParser()
    parsed = parser.parse(command)

    return {
        "intent": parsed.intent,
        "parameters": parsed.parameters,
        "confidence": parsed.confidence
    }


async def _execute_get_quote_step(args: dict) -> dict:
    """Execute price quote step."""
    from src.connectors.vvs import VVSConnector

    connector = VVSConnector()
    result = await connector.get_quote(
        from_token=args.get("from_token", "CRO"),
        to_token=args.get("to_token", "USDC"),
        amount=args.get("amount", "10")
    )

    return {
        "quote": result,
        "slippage_tolerance": "0.5%"
    }


async def _execute_swap_step(args: dict, db: AsyncSession) -> dict:
    """Execute token swap step."""
    from src.tools.simple_tools import SwapTokensTool

    tool = SwapTokensTool()
    result = tool.run(
        from_token=args.get("from_token", "CRO"),
        to_token=args.get("to_token", "USDC"),
        amount=args.get("amount", "10")
    )

    return {
        "swap_result": result,
        "tx_hash": result.get("tx_hash"),
        "status": result.get("status")
    }


async def _execute_parse_command_step(args: dict) -> dict:
    """Execute general command parsing step."""
    from src.agents.command_parser import CommandParser

    command = args.get("command", "")
    parser = CommandParser()
    parsed = parser.parse(command)

    return {
        "intent": parsed.intent,
        "parameters": parsed.parameters,
        "confidence": parsed.confidence,
        "requires_approval": parsed.requires_approval
    }
