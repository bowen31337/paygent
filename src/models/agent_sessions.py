"""
Agent session models.

This module defines the SQLAlchemy models for agent sessions and execution tracking.
"""

from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

from src.core.database import Base


class AgentSession(Base):
    """Agent session model for tracking agent execution contexts."""

    __tablename__ = "agent_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    wallet_address: Mapped[Optional[str]] = mapped_column(String(42))
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # budget limits, approval thresholds, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AgentSession(id={self.id}, wallet='{self.wallet_address}')>"


class ExecutionLog(Base):
    """Execution log model for tracking agent command execution."""

    __tablename__ = "execution_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("agent_sessions.id"))
    command: Mapped[str] = mapped_column(String, nullable=False)
    plan: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # write_todos plan structure
    tool_calls: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON)  # array of tool invocations
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)  # final execution result
    total_cost: Mapped[Optional[float]] = mapped_column(Float)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running, completed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.id}, session={self.session_id}, status='{self.status}')>"


class ApprovalRequest(Base):
    """Approval request model for human-in-the-loop workflows."""

    __tablename__ = "approval_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("agent_sessions.id"))
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_args: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision: Mapped[Optional[str]] = mapped_column(String(20))  # pending, approved, rejected, edited
    edited_args: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    decision_made_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ApprovalRequest(id={self.id}, tool='{self.tool_name}', decision='{self.decision}')>"


class ServiceSubscription(Base):
    """Service subscription model for recurring service access."""

    __tablename__ = "service_subscriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("agent_sessions.id"))
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, cancelled, expired
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ServiceSubscription(id={self.id}, status='{self.status}')>"
