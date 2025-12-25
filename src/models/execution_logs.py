"""
Execution log models for agent audit trail.

This module defines the SQLAlchemy models for tracking agent execution logs,
commands, tool calls, and results for complete audit trails.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ExecutionLog(Base):
    """Execution log model for tracking agent command executions.

    This model stores complete audit trails of all agent executions including:
    - Natural language commands
    - Agent plans (write_todos)
    - Tool calls made during execution
    - Final results
    - Cost and timing information
    """

    __tablename__ = "execution_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=lambda: uuid4())
    session_id: Mapped[UUID] = mapped_column(ForeignKey("agent_sessions.id"), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[dict | None] = mapped_column(JSON)  # Agent's execution plan (write_todos)
    tool_calls: Mapped[list | None] = mapped_column(JSON)  # List of tool invocations
    result: Mapped[dict | None] = mapped_column(JSON)  # Final execution result
    total_cost_usd: Mapped[float | None] = mapped_column(Float)  # Total LLM + transaction costs
    duration_ms: Mapped[int | None] = mapped_column(Integer)  # Execution duration in milliseconds
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.id}, command='{self.command[:50]}...', duration_ms={self.duration_ms})>"


class ToolCall(Base):
    """Tool call model for tracking individual tool invocations.

    This model stores detailed information about each tool call made during
    agent execution, including inputs, outputs, and timing.
    """

    __tablename__ = "tool_calls"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=lambda: uuid4())
    execution_log_id: Mapped[UUID] = mapped_column(ForeignKey("execution_logs.id"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_args: Mapped[dict] = mapped_column(JSON, nullable=False)  # Tool input arguments
    tool_result: Mapped[dict | None] = mapped_column(JSON)  # Tool output/result
    success: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ToolCall(id={self.id}, tool='{self.tool_name}', success={self.success})>"


class AgentSession(Base):
    """Agent session model for tracking agent execution sessions.

    This model stores session information for agent executions,
    including wallet address, configuration, and timing.
    """

    __tablename__ = "agent_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=lambda: uuid4())
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))  # User who initiated session
    wallet_address: Mapped[str | None] = mapped_column(String(42))
    config: Mapped[dict | None] = mapped_column(JSON)  # Session config (budget limits, approval thresholds, etc.)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AgentSession(id={self.id}, wallet={self.wallet_address})>"
