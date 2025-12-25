"""
Pydantic schemas for execution logs.

This module defines the Pydantic schemas for creating, updating, and responding
with execution log data.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ExecutionLogCreate(BaseModel):
    """Schema for creating execution logs."""
    session_id: str
    command: str
    plan: list[dict[str, Any]] | None = None
    result: dict[str, Any] | None = None
    total_cost: float | None = None
    duration_ms: int | None = None


class ExecutionLogUpdate(BaseModel):
    """Schema for updating execution logs."""
    plan: list[dict[str, Any]] | None = None
    result: dict[str, Any] | None = None
    total_cost: float | None = None
    duration_ms: int | None = None
    status: str | None = None


class ExecutionLogResponse(BaseModel):
    """Schema for execution log responses."""
    id: UUID
    session_id: str
    command: str
    plan: list[dict[str, Any]] | None = None
    result: dict[str, Any] | None = None
    total_cost: float | None = None
    duration_ms: int | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
