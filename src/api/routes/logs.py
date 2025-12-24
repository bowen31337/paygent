"""
Execution logs API routes.

This module provides endpoints for viewing agent execution logs
and session summaries.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.agent_sessions import ExecutionLog as ExecutionLogModel, AgentSession

router = APIRouter()


class ToolCall(BaseModel):
    """Information about a tool invocation."""

    tool_name: str
    arguments: dict
    result: Optional[dict] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class ExecutionLog(BaseModel):
    """Information about an agent execution."""

    id: UUID
    session_id: UUID
    command: str
    plan: Optional[dict] = None
    tool_calls: list[ToolCall] = []
    result: Optional[dict] = None
    total_cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    status: str = Field(..., description="running, completed, failed")
    created_at: str


class LogListResponse(BaseModel):
    """Response for listing execution logs."""

    logs: list[ExecutionLog]
    total: int
    offset: int
    limit: int


class SessionSummary(BaseModel):
    """Summary of a session's execution history."""

    session_id: UUID
    total_commands: int
    successful_commands: int
    failed_commands: int
    total_cost_usd: float
    total_duration_ms: int
    success_rate: float = Field(..., ge=0, le=1)
    most_used_tools: list[str]
    created_at: str
    last_activity: str


@router.get(
    "",
    response_model=LogListResponse,
    summary="Get execution logs",
    description="Get execution logs with optional filtering.",
)
async def get_logs(
    session_id: Optional[UUID] = Query(default=None, description="Filter by session"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> LogListResponse:
    """
    Get execution logs with filtering.

    Supports filtering by:
    - session_id: Specific session
    - status: Execution status
    - start_date/end_date: Date range
    """
    # Build query
    query = select(ExecutionLog)

    # Apply filters
    if session_id:
        query = query.where(ExecutionLog.session_id == session_id)
    if status_filter:
        query = query.where(ExecutionLog.status == status_filter)
    if start_date:
        query = query.where(ExecutionLog.created_at >= start_date)
    if end_date:
        query = query.where(ExecutionLog.created_at <= end_date)

    # Order by most recent first
    query = query.order_by(ExecutionLog.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    # Convert to response format
    log_list = []
    for log in logs:
        # Parse tool_calls if it's stored as JSON
        tool_calls = log.tool_calls if log.tool_calls else []

        log_list.append(
            ExecutionLog(
                id=log.id,
                session_id=log.session_id,
                command=log.command,
                plan=log.plan,
                tool_calls=[ToolCall(**tc) for tc in tool_calls],
                result=log.result,
                total_cost_usd=float(log.total_cost) if log.total_cost else None,
                duration_ms=log.duration_ms,
                status=log.status,
                created_at=log.created_at.isoformat(),
            )
        )

    return LogListResponse(
        logs=log_list,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{log_id}",
    response_model=ExecutionLog,
    summary="Get specific log",
    description="Get detailed information about a specific execution log.",
)
async def get_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ExecutionLog:
    """Get details of a specific execution log."""
    result = await db.execute(
        select(ExecutionLog).where(ExecutionLog.id == log_id)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log {log_id} not found",
        )

    # Parse tool_calls if it's stored as JSON
    tool_calls = log.tool_calls if log.tool_calls else []

    return ExecutionLog(
        id=log.id,
        session_id=log.session_id,
        command=log.command,
        plan=log.plan,
        tool_calls=[ToolCall(**tc) for tc in tool_calls],
        result=log.result,
        total_cost_usd=float(log.total_cost) if log.total_cost else None,
        duration_ms=log.duration_ms,
        status=log.status,
        created_at=log.created_at.isoformat(),
    )


@router.get(
    "/sessions/{session_id}/summary",
    response_model=SessionSummary,
    summary="Get session summary",
    description="Get aggregate summary of a session's execution history.",
)
async def get_session_summary(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    """
    Get summary statistics for a session.

    Includes:
    - Total commands executed
    - Success/failure counts
    - Total cost
    - Most used tools
    """
    # Check if session exists
    session_result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    # Get all logs for this session
    logs_result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.session_id == session_id)
        .order_by(ExecutionLog.created_at.asc())
    )
    logs = logs_result.scalars().all()

    if not logs:
        # Return empty summary for session with no logs
        return SessionSummary(
            session_id=session_id,
            total_commands=0,
            successful_commands=0,
            failed_commands=0,
            total_cost_usd=0.0,
            total_duration_ms=0,
            success_rate=0.0,
            most_used_tools=[],
            created_at=session.created_at.isoformat(),
            last_activity=session.last_active.isoformat(),
        )

    # Calculate statistics
    total_commands = len(logs)
    successful_commands = sum(1 for log in logs if log.status == "completed")
    failed_commands = sum(1 for log in logs if log.status == "failed")
    total_cost_usd = sum(float(log.total_cost or 0) for log in logs)
    total_duration_ms = sum(log.duration_ms or 0 for log in logs)
    success_rate = successful_commands / total_commands if total_commands > 0 else 0.0

    # Find most used tools
    tool_usage = {}
    for log in logs:
        if log.tool_calls:
            for tool_call in log.tool_calls:
                tool_name = tool_call.get("tool_name", "unknown")
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

    most_used_tools = sorted(tool_usage.keys(), key=lambda x: tool_usage[x], reverse=True)[:5]

    return SessionSummary(
        session_id=session_id,
        total_commands=total_commands,
        successful_commands=successful_commands,
        failed_commands=failed_commands,
        total_cost_usd=total_cost_usd,
        total_duration_ms=total_duration_ms,
        success_rate=success_rate,
        most_used_tools=most_used_tools,
        created_at=session.created_at.isoformat(),
        last_activity=session.last_active.isoformat(),
    )
