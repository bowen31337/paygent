"""
Agent session models.

This module defines the SQLAlchemy models for agent sessions and execution tracking.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class AgentSession(Base):
    """Agent session model for tracking agent execution contexts."""

    __tablename__ = "agent_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    wallet_address: Mapped[str | None] = mapped_column(String(42))
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # budget limits, approval thresholds, etc.
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
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # write_todos plan structure
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)  # array of tool invocations
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # final execution result
    total_cost: Mapped[float | None] = mapped_column(Float)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
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
    decision: Mapped[str | None] = mapped_column(String(20))  # pending, approved, rejected, edited
    edited_args: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    decision_made_at: Mapped[datetime | None] = mapped_column(DateTime)
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
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ServiceSubscription(id={self.id}, status='{self.status}')>"


class AgentMemory(Base):
    """Agent memory model for storing conversation history across sessions."""

    __tablename__ = "agent_memory"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("agent_sessions.id"))
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)  # human, ai, system
    content: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, name="metadata")  # Renamed to avoid SQLAlchemy conflict

    def __repr__(self) -> str:
        return f"<AgentMemory(id={self.id}, session={self.session_id}, type='{self.message_type}')>"
