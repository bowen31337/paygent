"""
Agent command and result schemas.

This module defines the Pydantic schemas for agent commands and results.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCommand(BaseModel):
    """Schema for agent commands."""
    session_id: str = Field(..., description="Unique identifier for the agent session")
    command: str = Field(..., description="Natural language command to be executed by the agent")
    plan: list[dict[str, Any]] | None = Field(None, description="Optional pre-defined execution plan")


class AgentResult(BaseModel):
    """Schema for agent execution results."""
    success: bool = Field(..., description="Whether the execution was successful")
    message: str = Field(..., description="Human-readable result message")
    data: dict[str, Any] | None = Field(None, description="Result data payload")
    tool_calls: list[dict[str, Any]] | None = Field(None, description="List of tool calls made during execution")
    total_cost: float | None = Field(None, description="Total cost of execution in USD")
    duration_ms: int | None = Field(None, description="Execution duration in milliseconds")
    execution_id: str | None = Field(None, description="Unique identifier for this execution")

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
    id: UUID = Field(..., description="Unique session identifier")
    user_id: UUID = Field(..., description="User who owns this session")
    wallet_address: str | None = Field(None, description="Associated wallet address for payments")
    config: dict[str, Any] | None = Field(None, description="Session configuration and limits")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_active: datetime = Field(..., description="Last activity timestamp")


class AgentExecutionSummary(BaseModel):
    """Schema for agent execution summary."""
    session_id: str = Field(..., description="Session identifier")
    total_executions: int = Field(..., description="Total number of executions")
    successful_executions: int = Field(..., description="Number of successful executions")
    success_rate: float = Field(..., description="Success rate as a decimal (0-1)")
    total_cost: float = Field(..., description="Total cost across all executions")
    total_duration_ms: int = Field(..., description="Total duration in milliseconds")
    average_duration_ms: int = Field(..., description="Average duration per execution")
    most_used_tool: str | None = Field(None, description="Most frequently used tool name")
    tool_usage_count: int = Field(..., description="Total number of tool calls")


class AgentToolUsageStats(BaseModel):
    """Schema for agent tool usage statistics."""
    session_id: str = Field(..., description="Session identifier")
    tool_name: str = Field(..., description="Name of the tool")
    usage_count: int = Field(..., description="Number of times tool was used")
    total_cost: float = Field(..., description="Total cost for this tool")
    average_duration_ms: int = Field(..., description="Average duration per tool call")
