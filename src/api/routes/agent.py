"""
Agent execution API routes.

This module provides endpoints for executing natural language commands
via AI agents and managing agent sessions.
"""

import asyncio
import json
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.models.agent_sessions import AgentSession, ExecutionLog
from src.agents.agent_executor import execute_agent_command

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
    session_id: Optional[UUID] = Field(
        default=None,
        description="Existing session ID to use, or None to create new session",
    )
    budget_limit_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum budget for this command execution in USD",
    )


class ExecuteCommandResponse(BaseModel):
    """Response from executing an agent command."""

    session_id: UUID = Field(..., description="Session ID for this execution")
    status: str = Field(..., description="Execution status")
    result: Optional[dict] = Field(default=None, description="Execution result")
    total_cost_usd: Optional[float] = Field(
        default=None, description="Total cost of execution in USD"
    )


class SessionInfo(BaseModel):
    """Information about an agent session."""

    id: UUID
    user_id: Optional[UUID] = None
    wallet_address: Optional[str] = None
    config: Optional[dict] = None
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
    session_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    config: Optional[dict] = None,
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


async def enhanced_agent_execution(command: str, session_id: UUID, budget_limit_usd: Optional[float] = None) -> dict:
    """
    Enhanced agent execution using command parsing and tools.

    This implementation:
    - Parses the natural language command to extract intent
    - Routes to appropriate tool (payment, swap, balance, etc.)
    - Executes the tool with extracted parameters
    - Returns structured results
    """
    # Use the enhanced agent executor
    result = await execute_agent_command(
        command=command,
        session_id=session_id,
        budget_limit_usd=budget_limit_usd
    )

    return result


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
    2. Create an execution plan
    3. Execute tools as needed (payments, swaps, etc.)
    4. Return the result

    For high-value operations, human-in-the-loop approval may be required.
    """
    # Get or create session
    session = await get_or_create_session(
        db,
        session_id=request.session_id,
        config={"budget_limit": request.budget_limit_usd} if request.budget_limit_usd else None
    )

    # Create execution log
    execution_log = ExecutionLog(
        id=uuid4(),
        session_id=session.id,
        command=request.command,
        status="running",
    )
    db.add(execution_log)
    await db.commit()
    await db.refresh(execution_log)

    # Execute the command using enhanced agent
    try:
        result = await enhanced_agent_execution(
            request.command,
            session.id,
            request.budget_limit_usd
        )

        # Update execution log
        execution_log.status = "completed" if result.get("success") else "failed"
        execution_log.result = result
        execution_log.duration_ms = 150  # Mock duration
        execution_log.total_cost = 0.01  # Mock cost
        await db.commit()

        return ExecuteCommandResponse(
            session_id=session.id,
            status="completed" if result.get("success") else "failed",
            result=result,
            total_cost_usd=0.01,
        )
    except Exception as e:
        # Update execution log with error
        execution_log.status = "failed"
        execution_log.result = {"error": str(e)}
        await db.commit()

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

    # Create execution log
    execution_log = ExecutionLog(
        id=uuid4(),
        session_id=session.id,
        command=request.command,
        status="running",
    )
    db.add(execution_log)
    await db.commit()
    await db.refresh(execution_log)

    async def event_generator():
        """
        Generator function that yields Server-Sent Events.
        """
        try:
            # Event 1: Thinking
            yield f"event: thinking\ndata: {dict_to_json({'message': 'Analyzing your command...', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            await asyncio.sleep(0.1)

            # Event 2: Tool call (simulated based on command)
            command_lower = request.command.lower()
            if "pay" in command_lower or "transfer" in command_lower:
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'x402_payment', 'arguments': {'amount': 0.10, 'token': 'USDC', 'recipient': 'service'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.2)

                # Event 3: Tool result
                yield f"event: tool_result\ndata: {dict_to_json({'tool': 'x402_payment', 'result': {'status': 'confirmed', 'tx_hash': '0xmocktxhash1234567890abcdef1234567890abcdef1234567890abcdef12345678'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.1)

            elif "swap" in command_lower or "exchange" in command_lower:
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'vvs_swap', 'arguments': {'from': 'CRO', 'to': 'USDC', 'amount': 100}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.2)

                yield f"event: tool_result\ndata: {dict_to_json({'tool': 'vvs_swap', 'result': {'received': 42.50, 'status': 'completed'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.1)

            elif "balance" in command_lower or "check" in command_lower:
                yield f"event: tool_call\ndata: {dict_to_json({'tool': 'check_balance', 'arguments': {}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.15)

                yield f"event: tool_result\ndata: {dict_to_json({'tool': 'check_balance', 'result': {'balances': {'CRO': 1000.0, 'USDC': 250.0}}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(0.1)
            else:
                # General command - just thinking
                await asyncio.sleep(0.3)

            # Event 4: Complete
            result = await enhanced_agent_execution(request.command, session.id)
            yield f"event: complete\ndata: {dict_to_json({'result': result, 'session_id': str(session.id), 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Update execution log
            execution_log.status = "completed" if result.get("success") else "failed"
            execution_log.result = result
            execution_log.duration_ms = 150
            execution_log.total_cost = 0.01
            await db.commit()

        except Exception as e:
            # Update execution log with error
            execution_log.status = "failed"
            execution_log.result = {"error": str(e)}
            await db.commit()

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
    limit: int = 20,
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

    return {"message": f"Session {session_id} terminated successfully", "session_id": str(session_id)}
