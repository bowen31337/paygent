"""
WebSocket message and event schemas for real-time communication.

Defines the data structures for WebSocket messages and events used in
agent execution streaming and HITL workflows.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    type: str = Field(..., description="Message type")
    data: dict[str, Any] = Field(..., description="Message data")


# Message Types for Client -> Server
class ExecuteMessage(BaseModel):
    """Execute agent command message."""
    command: str = Field(..., description="Natural language command to execute")
    plan: list[dict[str, Any]] | None = Field(None, description="Optional execution plan")


class ApproveMessage(BaseModel):
    """Approve approval request message."""
    request_id: UUID = Field(..., description="Approval request ID")


class RejectMessage(BaseModel):
    """Reject approval request message."""
    request_id: UUID = Field(..., description="Approval request ID")


class EditMessage(BaseModel):
    """Edit and approve approval request message."""
    request_id: UUID = Field(..., description="Approval request ID")
    edited_args: dict[str, Any] = Field(..., description="Edited tool arguments")


class CancelMessage(BaseModel):
    """Cancel execution message."""
    execution_id: UUID = Field(..., description="Execution ID to cancel")


# Event Types for Server -> Client
class WebSocketEvent(BaseModel):
    """Base WebSocket event structure."""
    type: str = Field(..., description="Event type")
    data: dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime | None = Field(default_factory=datetime.utcnow, description="Event timestamp")


class ThinkingEvent(WebSocketEvent):
    """Agent is processing/thinking."""
    type: str = "thinking"
    data: dict[str, Any] = Field(..., description="Thinking event data")


class ToolCallEvent(WebSocketEvent):
    """Agent called a tool."""
    type: str = "tool_call"
    data: dict[str, Any] = Field(..., description="Tool call data")


class ToolResultEvent(WebSocketEvent):
    """Agent received tool result."""
    type: str = "tool_result"
    data: dict[str, Any] = Field(..., description="Tool result data")


class ApprovalRequiredEvent(WebSocketEvent):
    """Approval required for operation."""
    type: str = "approval_required"
    data: dict[str, Any] = Field(..., description="Approval request data")


class CompleteEvent(WebSocketEvent):
    """Execution completed."""
    type: str = "complete"
    data: dict[str, Any] = Field(..., description="Completion data")


class ErrorEvent(WebSocketEvent):
    """Error occurred."""
    type: str = "error"
    data: dict[str, Any] = Field(..., description="Error data")


class SubagentStartEvent(WebSocketEvent):
    """Subagent started."""
    type: str = "subagent_start"
    data: dict[str, Any] = Field(..., description="Subagent start data")


class SubagentEndEvent(WebSocketEvent):
    """Subagent completed."""
    type: str = "subagent_end"
    data: dict[str, Any] = Field(..., description="Subagent end data")


# Event Data Schemas
class ThinkingEventData(BaseModel):
    """Data for thinking events."""
    session_id: str
    command: str
    step: int | None = None
    total_steps: int | None = None
    thought_process: str | None = None


class ToolCallEventData(BaseModel):
    """Data for tool call events."""
    session_id: str
    tool_name: str
    tool_args: dict[str, Any]
    tool_id: str | None = None


class ToolResultEventData(BaseModel):
    """Data for tool result events."""
    session_id: str
    tool_id: str
    result: Any
    success: bool
    error: str | None = None


class ApprovalRequiredEventData(BaseModel):
    """Data for approval required events."""
    session_id: str
    request_id: UUID
    tool_name: str
    tool_args: dict[str, Any]
    reason: str
    amount: str | None = None
    currency: str | None = None
    estimated_cost: str | None = None


class CompleteEventData(BaseModel):
    """Data for complete events."""
    session_id: str
    execution_id: UUID
    result: Any
    success: bool
    total_cost: str | None = None
    duration_ms: int | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ErrorEventData(BaseModel):
    """Data for error events."""
    session_id: str | None = None
    execution_id: UUID | None = None
    message: str
    error_type: str | None = None
    details: dict[str, Any] | None = None


class SubagentStartEventData(BaseModel):
    """Data for subagent start events."""
    session_id: str
    subagent_id: str
    subagent_type: str
    task: str
    parent_agent: str


class SubagentEndEventData(BaseModel):
    """Data for subagent end events."""
    session_id: str
    subagent_id: str
    result: Any
    success: bool
    duration_ms: int | None = None
    error: str | None = None


# Convenience functions for creating events
def create_thinking_event(session_id: str, command: str, step: int | None = None, total_steps: int | None = None, thought_process: str | None = None) -> ThinkingEvent:
    """Create a thinking event."""
    data = ThinkingEventData(
        session_id=session_id,
        command=command,
        step=step,
        total_steps=total_steps,
        thought_process=thought_process
    )
    return ThinkingEvent(type="thinking", data=data.model_dump(mode='json'))


def create_tool_call_event(session_id: str, tool_name: str, tool_args: dict[str, Any], tool_id: str | None = None) -> ToolCallEvent:
    """Create a tool call event."""
    data = ToolCallEventData(
        session_id=session_id,
        tool_name=tool_name,
        tool_args=tool_args,
        tool_id=tool_id
    )
    return ToolCallEvent(type="tool_call", data=data.model_dump(mode='json'))


def create_tool_result_event(session_id: str, tool_id: str, result: Any, success: bool, error: str | None = None) -> ToolResultEvent:
    """Create a tool result event."""
    data = ToolResultEventData(
        session_id=session_id,
        tool_id=tool_id,
        result=result,
        success=success,
        error=error
    )
    return ToolResultEvent(type="tool_result", data=data.model_dump(mode='json'))


def create_approval_required_event(
    session_id: str,
    request_id: UUID,
    tool_name: str,
    tool_args: dict[str, Any],
    reason: str,
    amount: str | None = None,
    currency: str | None = None,
    estimated_cost: str | None = None
) -> ApprovalRequiredEvent:
    """Create an approval required event."""
    data = ApprovalRequiredEventData(
        session_id=session_id,
        request_id=request_id,
        tool_name=tool_name,
        tool_args=tool_args,
        reason=reason,
        amount=amount,
        currency=currency,
        estimated_cost=estimated_cost
    )
    return ApprovalRequiredEvent(type="approval_required", data=data.model_dump(mode='json'))


def create_complete_event(
    session_id: str,
    execution_id: UUID,
    result: Any,
    success: bool,
    total_cost: str | None = None,
    duration_ms: int | None = None,
    tool_calls: list[dict[str, Any]] | None = None
) -> CompleteEvent:
    """Create a complete event."""
    data = CompleteEventData(
        session_id=session_id,
        execution_id=execution_id,
        result=result,
        success=success,
        total_cost=total_cost,
        duration_ms=duration_ms,
        tool_calls=tool_calls
    )
    return CompleteEvent(type="complete", data=data.model_dump(mode='json'))


def create_error_event(
    message: str,
    session_id: str | None = None,
    execution_id: UUID | None = None,
    error_type: str | None = None,
    details: dict[str, Any] | None = None
) -> ErrorEvent:
    """Create an error event."""
    data = ErrorEventData(
        session_id=session_id,
        execution_id=execution_id,
        message=message,
        error_type=error_type,
        details=details
    )
    return ErrorEvent(type="error", data=data.model_dump(mode='json'))


def create_subagent_start_event(
    session_id: str,
    subagent_id: str,
    subagent_type: str,
    task: str,
    parent_agent: str
) -> SubagentStartEvent:
    """Create a subagent start event."""
    data = SubagentStartEventData(
        session_id=session_id,
        subagent_id=subagent_id,
        subagent_type=subagent_type,
        task=task,
        parent_agent=parent_agent
    )
    return SubagentStartEvent(type="subagent_start", data=data.model_dump(mode='json'))


def create_subagent_end_event(
    session_id: str,
    subagent_id: str,
    result: Any,
    success: bool,
    duration_ms: int | None = None,
    error: str | None = None
) -> SubagentEndEvent:
    """Create a subagent end event."""
    data = SubagentEndEventData(
        session_id=session_id,
        subagent_id=subagent_id,
        result=result,
        success=success,
        duration_ms=duration_ms,
        error=error
    )
    return SubagentEndEvent(type="subagent_end", data=data.model_dump(mode='json'))
