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
    # Payment details for subscription
    amount: Mapped[float | None] = mapped_column(Float)
    token: Mapped[str | None] = mapped_column(String(20))
    renewal_interval_days: Mapped[int | None] = mapped_column(Integer, default=30)
    last_renewal_date: Mapped[datetime | None] = mapped_column(DateTime)
    last_tx_hash: Mapped[str | None] = mapped_column(String(100))
    renewal_count: Mapped[int | None] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ServiceSubscription(id={self.id}, status='{self.status}', expires={self.expires_at})>"


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
