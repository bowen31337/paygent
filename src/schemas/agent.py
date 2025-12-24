"""
Agent command and result schemas.

This module defines the Pydantic schemas for agent commands and results.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCommand(BaseModel):
    """Schema for agent commands."""
    session_id: str
    command: str
    plan: Optional[List[Dict[str, Any]]] = None


class AgentResult(BaseModel):
    """Schema for agent execution results."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    total_cost: Optional[float] = None
    duration_ms: Optional[int] = None
    execution_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
    wallet_address: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
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
    most_used_tool: Optional[str] = None
    tool_usage_count: int


class AgentToolUsageStats(BaseModel):
    """Schema for agent tool usage statistics."""
    session_id: str
    tool_name: str
    usage_count: int
    total_cost: float
    average_duration_ms: int