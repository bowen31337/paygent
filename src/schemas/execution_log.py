"""
Pydantic schemas for execution logs.

This module defines the Pydantic schemas for creating, updating, and responding
with execution log data.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExecutionLogCreate(BaseModel):
    """Schema for creating execution logs."""
    session_id: str
    command: str
    plan: Optional[List[Dict[str, Any]]] = None
    result: Optional[Dict[str, Any]] = None
    total_cost: Optional[float] = None
    duration_ms: Optional[int] = None


class ExecutionLogUpdate(BaseModel):
    """Schema for updating execution logs."""
    plan: Optional[List[Dict[str, Any]]] = None
    result: Optional[Dict[str, Any]] = None
    total_cost: Optional[float] = None
    duration_ms: Optional[int] = None
    status: Optional[str] = None


class ExecutionLogResponse(BaseModel):
    """Schema for execution log responses."""
    id: UUID
    session_id: str
    command: str
    plan: Optional[List[Dict[str, Any]]] = None
    result: Optional[Dict[str, Any]] = None
    total_cost: Optional[float] = None
    duration_ms: Optional[int] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True