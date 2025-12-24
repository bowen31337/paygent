"""
Agent execution API routes.

This module provides endpoints for executing natural language commands
via AI agents and managing agent sessions.
"""

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


async def mock_agent_execution(command: str, session_id: UUID) -> dict:
    """
    Mock agent execution for testing purposes.
    
    In a real implementation, this would:
    - Use an LLM to parse the command
    - Create a plan using write_todos
    - Execute tools (payments, swaps, etc.)
    - Return structured results
    
    For now, we return a simple mock response based on the command content.
    """
    command_lower = command.lower()
    
    # Simple command parsing for mock responses
    if "pay" in command_lower or "transfer" in command_lower:
        return {
            "action": "payment",
            "description": f"Executed payment: {command}",
            "amount": "0.10",
            "token": "USDC",
            "recipient": "0x1234...5678",
            "tx_hash": "0xmocktxhash1234567890abcdef1234567890abcdef1234567890abcdef12345678",
            "status": "confirmed"
        }
    elif "swap" in command_lower or "exchange" in command_lower:
        return {
            "action": "swap",
            "description": f"Executed swap: {command}",
            "from_token": "CRO",
            "to_token": "USDC",
            "amount": "100",
            "received": "42.50",
            "status": "completed"
        }
    elif "balance" in command_lower or "check" in command_lower:
        return {
            "action": "query",
            "description": f"Balance check: {command}",
            "balances": [
                {"token": "CRO", "amount": "1000.00"},
                {"token": "USDC", "amount": "250.00"}
            ],
            "status": "completed"
        }
    else:
        return {
            "action": "general",
            "description": f"Processed command: {command}",
            "status": "completed",
            "note": "This is a mock response. Real agent execution would use LLM and tools."
        }


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
    
    # Execute the command (mock implementation)
    try:
        result = await mock_agent_execution(request.command, session.id)
        
        # Update execution log
        execution_log.status = "completed"
        execution_log.result = result
        execution_log.duration_ms = 100  # Mock duration
        execution_log.total_cost = 0.01  # Mock cost
        await db.commit()
        
        return ExecuteCommandResponse(
            session_id=session.id,
            status="completed",
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
    """
    # TODO: Implement streaming execution
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Streaming execution not yet implemented",
    )


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
    # TODO: Implement session listing
    return SessionListResponse(
        sessions=[],
        total=0,
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
    # TODO: Implement session retrieval
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session {session_id} not found",
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
    # TODO: Implement session termination
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session {session_id} not found",
    )
