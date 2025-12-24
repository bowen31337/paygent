"""
WebSocket endpoints for real-time agent execution and HITL workflows.

Provides WebSocket support for:
- Real-time agent execution streaming
- Human-in-the-loop approval workflows
- Agent state management
- Event broadcasting
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from starlette.status import WS_1008_POLICY_VIOLATION

from src.core.config import settings
from src.core.auth import get_current_user, get_current_user_optional
from src.schemas.websocket import (
    WebSocketMessage,
    ExecuteMessage,
    ApproveMessage,
    RejectMessage,
    EditMessage,
    CancelMessage,
    WebSocketEvent,
    ThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
    ApprovalRequiredEvent,
    CompleteEvent,
    ErrorEvent,
    SubagentStartEvent,
    SubagentEndEvent,
)
from src.services.agent_service import AgentService
from src.services.approval_service import ApprovalService
from src.services.session_service import SessionService
from src.services.execution_log_service import ExecutionLogService
from src.agents.agent_executor_enhanced import AgentExecutorEnhanced
from src.services.metrics_service import metrics_collector
from src.core.database import get_db
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time communication."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.execution_tasks: Dict[str, asyncio.Task] = {}  # session_id -> task

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        # Record metrics
        metrics_collector.record_websocket_connection()
        logger.info(f"WebSocket connected for session {session_id}, user {user_id}")

    def disconnect(self, session_id: str, user_id: str):
        """Disconnect a WebSocket client."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        # Cancel any active execution task
        if session_id in self.execution_tasks:
            task = self.execution_tasks[session_id]
            if not task.done():
                task.cancel()
            del self.execution_tasks[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}, user {user_id}")

    async def send_personal_message(self, message: Dict[str, Any], session_id: str):
        """Send a message to a specific client."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(message))
                # Record sent message metric
                metrics_collector.record_websocket_message(received=False)
                logger.debug(f"Sent message to session {session_id}: {message['type']}")
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {e}")
                # Remove broken connection
                self.disconnect(session_id, self.get_user_id_by_session(session_id))

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
                logger.debug(f"Broadcasted message to session {session_id}: {message['type']}")
            except Exception as e:
                logger.error(f"Failed to broadcast to session {session_id}: {e}")
                self.disconnect(session_id, self.get_user_id_by_session(session_id))

    def get_session_by_user(self, user_id: str) -> Optional[str]:
        """Get session ID by user ID."""
        return self.user_sessions.get(user_id)

    def get_user_id_by_session(self, session_id: str) -> Optional[str]:
        """Get user ID by session ID."""
        for user_id, sess_id in self.user_sessions.items():
            if sess_id == session_id:
                return user_id
        return None

    def register_execution_task(self, session_id: str, task: asyncio.Task):
        """Register an active execution task for a session."""
        self.execution_tasks[session_id] = task

    def get_execution_task(self, session_id: str) -> Optional[asyncio.Task]:
        """Get the active execution task for a session."""
        return self.execution_tasks.get(session_id)


manager = ConnectionManager()


@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time agent execution and HITL workflows.

    Args:
        websocket: WebSocket connection
        session_id: Agent session ID
        token: Optional authentication token
    """
    logger.info(f"WebSocket connection attempt - session_id: {session_id}, type: {type(session_id)}, debug: {settings.debug}")

    # Get user_id from token if provided
    user_id = None
    if token:
        try:
            from src.core.auth import verify_token
            token_data = verify_token(token)
            user_id = token_data.user_id if token_data else None
        except Exception:
            logger.warning("Token validation failed, continuing without auth")

    # If no user_id and not in debug mode, require authentication
    if not user_id and not settings.debug:
        logger.warning("WebSocket: Authentication required")
        await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return

    # Use a default user ID if not authenticated (for testing)
    if not user_id:
        user_id = "test-user-123"

    # Convert UUID to string for manager operations
    session_id_str = str(session_id)

    # Validate session exists - get db session for validation
    async for db in get_db():
        session_service = SessionService(db)
        # Convert session_id string to UUID for get_session
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            logger.warning(f"WebSocket: Invalid session ID format: {session_id}")
            await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="Invalid session ID format")
            return
        session = await session_service.get_session(session_uuid)
        break
    logger.info(f"WebSocket: Session lookup result: {session}")
    if not session:
        logger.warning(f"WebSocket: Invalid session {session_id}")
        await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="Invalid session")
        return

    # Connect to manager
    await manager.connect(websocket, session_id_str, user_id)

    try:
        # Send connection established event
        await manager.send_personal_message(
            WebSocketEvent(
                type="connected",
                data={"session_id": session_id_str, "user_id": user_id}
            ).dict(),
            session_id_str
        )

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                # Record received message metric
                metrics_collector.record_websocket_message(received=True)
                message = WebSocketMessage.parse_raw(data)
                # Get database session for message handling
                async for db in get_db():
                    await handle_websocket_message(websocket, message, session_id_str, user_id, db)
                    break
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from session {session_id_str}")
                await manager.send_personal_message(
                    ErrorEvent(
                        type="error",
                        data={"message": "Invalid JSON format"}
                    ).dict(),
                    session_id_str
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message(
                    ErrorEvent(
                        type="error",
                        data={"message": str(e)}
                    ).dict(),
                    session_id_str
                )

    finally:
        manager.disconnect(session_id_str, user_id)


async def handle_websocket_message(
    websocket: WebSocket,
    message: WebSocketMessage,
    session_id: str,
    user_id: str,
    db: AsyncSession
):
    """Handle incoming WebSocket messages based on type."""
    message_type = message.type

    if message_type == "execute":
        await handle_execute_message(message, session_id, user_id, db)
    elif message_type == "approve":
        await handle_approve_message(message, session_id, user_id, db)
    elif message_type == "reject":
        await handle_reject_message(message, session_id, user_id, db)
    elif message_type == "edit":
        await handle_edit_message(message, session_id, user_id, db)
    elif message_type == "cancel":
        await handle_cancel_message(message, session_id, user_id, db)
    else:
        logger.warning(f"Unknown WebSocket message type: {message_type}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={"message": f"Unknown message type: {message_type}"}
            ).dict(),
            session_id
        )


async def handle_execute_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str,
    db: AsyncSession
):
    """Handle execute command message with streaming events."""
    execute_msg = ExecuteMessage.parse_obj(message.data)

    # Create execution log entry
    execution_log_service = ExecutionLogService(db)
    execution_log = await execution_log_service.create_execution_log(
        session_id=session_id,
        command=execute_msg.command,
        plan=execute_msg.plan
    )
    execution_id = execution_log.id if execution_log else uuid4()

    # Send thinking event
    await manager.send_personal_message(
        ThinkingEvent(
            type="thinking",
            data={
                "session_id": session_id,
                "command": execute_msg.command,
                "timestamp": execution_log.created_at.isoformat() if execution_log else None
            }
        ).dict(),
        session_id
    )

    # Execute the agent command using enhanced executor
    try:
        executor = AgentExecutorEnhanced(UUID(session_id), db)
        result = await executor.execute_command(
            command=execute_msg.command,
            budget_limit_usd=None  # Could be added to ExecuteMessage if needed
        )

        # Check if approval is required
        if result.get("requires_approval") and result.get("approval_id"):
            # Send approval required event
            await manager.send_personal_message(
                ApprovalRequiredEvent(
                    type="approval_required",
                    data={
                        "session_id": session_id,
                        "execution_id": str(execution_id),
                        "request_id": result.get("approval_id"),
                        "tool_name": result.get("tool_name", "x402_payment"),
                        "tool_args": result.get("tool_args", {}),
                        "reason": result.get("message", "High-value transaction requires approval"),
                        "amount": str(result.get("amount", 0)),
                        "currency": result.get("token", "USDC"),
                        "estimated_cost": f"{result.get('amount', 0)} {result.get('token', 'USDC')}"
                    }
                ).dict(),
                session_id
            )
            return

        # If successful, send tool events and complete
        if result.get("tool_calls"):
            for tool_call in result["tool_calls"]:
                # Send tool call event
                await manager.send_personal_message(
                    ToolCallEvent(
                        type="tool_call",
                        data={
                            "session_id": session_id,
                            "tool_name": tool_call.get("tool_name", "unknown"),
                            "tool_args": tool_call.get("tool_args", {}),
                            "timestamp": tool_call.get("timestamp")
                        }
                    ).dict(),
                    session_id
                )

                # Send tool result event
                await manager.send_personal_message(
                    ToolResultEvent(
                        type="tool_result",
                        data={
                            "session_id": session_id,
                            "tool_id": str(uuid4()),
                            "result": tool_call.get("result", {}),
                            "success": True
                        }
                    ).dict(),
                    session_id
                )

                await asyncio.sleep(0.05)  # Small delay for streaming effect

        # Send complete event
        await manager.send_personal_message(
            CompleteEvent(
                type="complete",
                data={
                    "session_id": session_id,
                    "execution_id": str(execution_id),
                    "result": result,
                    "success": result.get("success", False),
                    "total_cost": f"{result.get('total_cost_usd', 0.0)} USD",
                    "duration_ms": result.get("duration_ms"),
                    "tool_calls": result.get("tool_calls", [])
                }
            ).dict(),
            session_id
        )

    except Exception as e:
        logger.error(f"Error executing command for session {session_id}: {e}", exc_info=True)
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "session_id": session_id,
                    "execution_id": str(execution_id),
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                }
            ).dict(),
            session_id
        )


async def handle_approve_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str,
    db: AsyncSession
):
    """Handle approval message for pending requests."""
    approve_msg = ApproveMessage.parse_obj(message.data)

    approval_service = ApprovalService(db)

    try:
        # Approve the request
        approval = await approval_service.approve_request(
            approval_id=approve_msg.request_id
        )

        if approval:
            # Send success event
            await manager.send_personal_message(
                WebSocketEvent(
                    type="approved",
                    data={
                        "request_id": str(approve_msg.request_id),
                        "decision": "approved"
                    }
                ).dict(),
                session_id
            )
        else:
            raise HTTPException(status_code=404, detail="Approval request not found or already processed")

    except Exception as e:
        logger.error(f"Error approving request {approve_msg.request_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "request_id": str(approve_msg.request_id),
                    "message": str(e)
                }
            ).dict(),
            session_id
        )


async def handle_reject_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str,
    db: AsyncSession
):
    """Handle rejection message for pending requests."""
    reject_msg = RejectMessage.parse_obj(message.data)

    approval_service = ApprovalService(db)

    try:
        # Reject the request
        approval = await approval_service.reject_request(
            approval_id=reject_msg.request_id
        )

        if approval:
            # Send rejection event
            await manager.send_personal_message(
                WebSocketEvent(
                    type="rejected",
                    data={
                        "request_id": str(reject_msg.request_id),
                        "decision": "rejected"
                    }
                ).dict(),
                session_id
            )
        else:
            raise HTTPException(status_code=404, detail="Approval request not found or already processed")

    except Exception as e:
        logger.error(f"Error rejecting request {reject_msg.request_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "request_id": str(reject_msg.request_id),
                    "message": str(e)
                }
            ).dict(),
            session_id
        )


async def handle_edit_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str,
    db: AsyncSession
):
    """Handle edit and approve message for pending requests."""
    edit_msg = EditMessage.parse_obj(message.data)

    approval_service = ApprovalService(db)

    try:
        # Get the approval request first
        approval = await approval_service.get_approval_request(edit_msg.request_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")

        # Update with edited args and approve
        approval = await approval_service.approve_request(
            approval_id=edit_msg.request_id,
            edited_args=edit_msg.edited_args
        )

        if approval:
            # Send edit approved event
            await manager.send_personal_message(
                WebSocketEvent(
                    type="edit_approved",
                    data={
                        "request_id": str(edit_msg.request_id),
                        "decision": "edited",
                        "edited_args": edit_msg.edited_args
                    }
                ).dict(),
                session_id
            )
        else:
            raise HTTPException(status_code=400, detail="Could not edit and approve request")

    except Exception as e:
        logger.error(f"Error editing request {edit_msg.request_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "request_id": str(edit_msg.request_id),
                    "message": str(e)
                }
            ).dict(),
            session_id
        )


async def handle_cancel_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str,
    db: AsyncSession
):
    """Handle cancellation message for ongoing execution."""
    cancel_msg = CancelMessage.parse_obj(message.data)

    try:
        # Get the active execution task
        task = manager.get_execution_task(session_id)

        if task and not task.done():
            # Cancel the task
            task.cancel()
            logger.info(f"Cancelled execution {cancel_msg.execution_id} for session {session_id}")
        else:
            logger.info(f"No active execution to cancel for session {session_id}")

        # Send cancellation event
        await manager.send_personal_message(
            WebSocketEvent(
                type="cancelled",
                data={
                    "execution_id": str(cancel_msg.execution_id),
                    "session_id": session_id,
                    "message": "Cancellation request received"
                }
            ).dict(),
            session_id
        )

    except Exception as e:
        logger.error(f"Error handling cancellation for execution {cancel_msg.execution_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "execution_id": str(cancel_msg.execution_id),
                    "message": str(e)
                }
            ).dict(),
            session_id
        )


# Helper functions for sending events to clients
async def send_thinking_event(session_id: str, data: Dict[str, Any]):
    """Send a thinking event to the client."""
    await manager.send_personal_message(
        ThinkingEvent(type="thinking", data=data).dict(),
        session_id
    )


async def send_tool_call_event(session_id: str, data: Dict[str, Any]):
    """Send a tool call event to the client."""
    await manager.send_personal_message(
        ToolCallEvent(type="tool_call", data=data).dict(),
        session_id
    )


async def send_tool_result_event(session_id: str, data: Dict[str, Any]):
    """Send a tool result event to the client."""
    await manager.send_personal_message(
        ToolResultEvent(type="tool_result", data=data).dict(),
        session_id
    )


async def send_approval_required_event(session_id: str, data: Dict[str, Any]):
    """Send an approval required event to the client."""
    await manager.send_personal_message(
        ApprovalRequiredEvent(type="approval_required", data=data).dict(),
        session_id
    )


async def send_complete_event(session_id: str, data: Dict[str, Any]):
    """Send a complete event to the client."""
    await manager.send_personal_message(
        CompleteEvent(type="complete", data=data).dict(),
        session_id
    )


async def send_error_event(session_id: str, data: Dict[str, Any]):
    """Send an error event to the client."""
    await manager.send_personal_message(
        ErrorEvent(type="error", data=data).dict(),
        session_id
    )


async def send_subagent_start_event(session_id: str, data: Dict[str, Any]):
    """Send a subagent start event to the client."""
    await manager.send_personal_message(
        SubagentStartEvent(type="subagent_start", data=data).dict(),
        session_id
    )


async def send_subagent_end_event(session_id: str, data: Dict[str, Any]):
    """Send a subagent end event to the client."""
    await manager.send_personal_message(
        SubagentEndEvent(type="subagent_end", data=data).dict(),
        session_id
    )