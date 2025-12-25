"""
Agent command and result schemas.

This module defines the Pydantic schemas for agent commands and results.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AgentCommand(BaseModel):
    """Schema for agent commands."""
    session_id: str
    command: str
    plan: list[dict[str, Any]] | None = None


class AgentResult(BaseModel):
    """Schema for agent execution results."""
    success: bool
    message: str
    data: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    total_cost: float | None = None
    duration_ms: int | None = None
    execution_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "tool_calls": self.tool_calls,
            "total_cost": self.total_cost,
            "duration_ms": self.duration_ms,
            "execution_id": self.execution_id
        }


class AgentSessionInfo(BaseModel):
    """Schema for agent session information."""
    id: UUID
    user_id: UUID
    wallet_address: str | None = None
    config: dict[str, Any] | None = None
    created_at: datetime
    last_active: datetime


class AgentExecutionSummary(BaseModel):
    """Schema for agent execution summary."""
    session_id: str
    total_executions: int
    successful_executions: int
    success_rate: float
    total_cost: float
    total_duration_ms: int
    average_duration_ms: int
    most_used_tool: str | None = None
    tool_usage_count: int


class AgentToolUsageStats(BaseModel):
    """Schema for agent tool usage statistics."""
    session_id: str
    tool_name: str
    usage_count: int
    total_cost: float
    average_duration_ms: int
