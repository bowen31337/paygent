"""
Pydantic schemas for execution logs.

This module defines the Pydantic schemas for creating, updating, and responding
with execution log data.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExecutionLogCreate(BaseModel):
    """Schema for creating execution logs."""
    session_id: str = Field(..., description="Session identifier for this execution")
    command: str = Field(..., description="The command that was executed")
    plan: list[dict[str, Any]] | None = Field(None, description="Execution plan used")
    result: dict[str, Any] | None = Field(None, description="Result of the execution")
    total_cost: float | None = Field(None, description="Total cost in USD")
    duration_ms: int | None = Field(None, description="Execution duration in milliseconds")


class ExecutionLogUpdate(BaseModel):
    """Schema for updating execution logs."""
    plan: list[dict[str, Any]] | None = Field(None, description="Updated execution plan")
    result: dict[str, Any] | None = Field(None, description="Updated result data")
    total_cost: float | None = Field(None, description="Updated total cost")
    duration_ms: int | None = Field(None, description="Updated duration in milliseconds")
    status: str | None = Field(None, description="Updated execution status")


class ExecutionLogResponse(BaseModel):
    """Schema for execution log responses."""
    id: UUID = Field(..., description="Unique execution log identifier")
    session_id: str = Field(..., description="Session identifier")
    command: str = Field(..., description="Executed command")
    plan: list[dict[str, Any]] | None = Field(None, description="Execution plan")
    result: dict[str, Any] | None = Field(None, description="Execution result")
    total_cost: float | None = Field(None, description="Total cost in USD")
    duration_ms: int | None = Field(None, description="Duration in milliseconds")
    status: str = Field(..., description="Execution status")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True
