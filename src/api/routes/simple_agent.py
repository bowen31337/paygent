"""
Simple Agent Execution API routes.

This module provides simplified endpoints for executing natural language commands
via the basic agent implementation that doesn't rely on problematic dependencies.
"""

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.agent_execution_service import AgentExecutionService
from src.services.metrics_service import metrics_collector

router = APIRouter()


class SimpleExecuteCommandRequest:
    """Request body for executing an agent command."""

    def __init__(
        self,
        command: str,
        session_id: UUID | None = None,
        budget_limit_usd: float | None = None,
        llm_model: str = "mock",
    ):
        self.command = command
        self.session_id = session_id
        self.budget_limit_usd = budget_limit_usd
        self.llm_model = llm_model


class SimpleExecuteCommandResponse:
    """Response body for executing an agent command."""

    def __init__(
        self,
        success: bool,
        result: dict | str,
        session_id: UUID | None = None,
        total_cost_usd: float = 0.0,
        session_info: dict | None = None,
        execution_summary: dict | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.result = result
        self.session_id = session_id
        self.total_cost_usd = total_cost_usd
        self.session_info = session_info
        self.execution_summary = execution_summary
        self.error = error

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        result = {
            "success": self.success,
            "session_id": str(self.session_id) if self.session_id else None,
            "total_cost_usd": self.total_cost_usd,
        }

        if self.success:
            result["result"] = self.result
            if self.session_info:
                result["session_info"] = self.session_info
            if self.execution_summary:
                result["execution_summary"] = self.execution_summary
        else:
            result["error"] = self.error

        return result


@router.post(
    "/api/v1/agent/execute",
    summary="Execute agent command",
    description="Execute a natural language command using the AI agent",
    response_description="Command execution result",
    tags=["Agent"],
)
async def execute_agent_command(
    request: SimpleExecuteCommandRequest = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Execute a natural language command using the AI agent.

    The agent will parse the command and execute the appropriate action.
    Supports commands like:
    - "Check my balance"
    - "What can you do?"
    - "Pay 0.10 USDC to access the market data API"
    - "Swap 100 USDC for CRO"

    Args:
        command: Natural language command to execute
        session_id: Optional existing session ID (currently ignored for simplicity)
        budget_limit_usd: Optional budget limit in USD
        llm_model: LLM model to use (mock for now)

    Returns:
        Command execution result with session information
    """
    try:
        # Validate input
        if not request.command or len(request.command.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Command is required and cannot be empty"
            )

        if len(request.command) > 10000:
            raise HTTPException(
                status_code=400,
                detail="Command too long (max 10000 characters)"
            )

        # Execute command
        service = AgentExecutionService(db)
        result = await service.execute_command(
            command=request.command,
            budget_limit_usd=request.budget_limit_usd,
            llm_model=request.llm_model,
        )

        # Update metrics
        metrics_collector.record_command_execution(
            command=request.command,
            success=result.get("success", False),
            response_time=0.0,  # TODO: Add timing
            cost_usd=result.get("total_cost_usd", 0.0),
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Command execution failed: {str(e)}"
        )


@router.post(
    "/api/v1/agent/stream",
    summary="Execute agent command with streaming",
    description="Execute a natural language command with real-time streaming responses",
    response_description="Streaming command execution result",
    tags=["Agent"],
)
async def execute_agent_command_stream(
    request: SimpleExecuteCommandRequest = Depends(),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Execute a natural language command with real-time streaming responses.

    Returns a Server-Sent Events (SSE) stream with real-time updates
    as the agent processes the command.

    Args:
        command: Natural language command to execute
        session_id: Optional existing session ID
        budget_limit_usd: Optional budget limit in USD
        llm_model: LLM model to use (mock for now)

    Returns:
        Streaming response with real-time updates
    """
    async def event_stream():
        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Execute command
            service = AgentExecutionService(db)
            result = await service.execute_command(
                command=request.command,
                budget_limit_usd=request.budget_limit_usd,
                llm_model=request.llm_model,
            )

            # Send result events
            if result.get("success"):
                yield f"data: {json.dumps({'type': 'complete', 'result': result.get('result'), 'session_id': str(result.get('session_id'))})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'error': result.get('error')})}\n\n"

            # Send end event
            yield f"data: {json.dumps({'type': 'end', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/api/v1/agent/sessions",
    summary="List agent sessions",
    description="List all agent sessions for the current user",
    response_description="List of agent sessions",
    tags=["Agent"],
)
async def list_agent_sessions(
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all agent sessions.

    Args:
        user_id: Optional user ID to filter sessions

    Returns:
        List of agent sessions
    """
    try:
        service = AgentExecutionService(db)
        result = await service.list_sessions(user_id=user_id)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get(
    "/api/v1/agent/sessions/{session_id}",
    summary="Get agent session",
    description="Get details of a specific agent session",
    response_description="Agent session details",
    tags=["Agent"],
)
async def get_agent_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get details of a specific agent session.

    Args:
        session_id: Session ID to retrieve

    Returns:
        Agent session details
    """
    try:
        service = AgentExecutionService(db)
        result = await service.get_session_status(session_id)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session: {str(e)}"
        )


@router.delete(
    "/api/v1/agent/sessions/{session_id}",
    summary="Terminate agent session",
    description="Terminate an active agent session",
    response_description="Session termination result",
    tags=["Agent"],
)
async def terminate_agent_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Terminate an active agent session.

    Args:
        session_id: Session ID to terminate

    Returns:
        Session termination result
    """
    try:
        service = AgentExecutionService(db)
        result = await service.terminate_session(session_id)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to terminate session: {str(e)}"
        )
