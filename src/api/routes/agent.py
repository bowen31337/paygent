"""
Agent execution API routes.

This module provides endpoints for executing natural language commands
via AI agents and managing agent sessions.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

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
    # TODO: Implement agent execution
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Agent execution not yet implemented",
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
