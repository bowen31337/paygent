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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
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

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time communication."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        logger.info(f"WebSocket connected for session {session_id}, user {user_id}")

    def disconnect(self, session_id: str, user_id: str):
        """Disconnect a WebSocket client."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        logger.info(f"WebSocket disconnected for session {session_id}, user {user_id}")

    async def send_personal_message(self, message: Dict[str, Any], session_id: str):
        """Send a message to a specific client."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(message))
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


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    """
    WebSocket endpoint for real-time agent execution and HITL workflows.

    Args:
        websocket: WebSocket connection
        session_id: Agent session ID
        user_id: Current authenticated user (optional)
    """
    # If no user_id and not in debug mode, require authentication
    if not user_id and not settings.debug:
        await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return

    # Use a default user ID if not authenticated (for testing)
    if not user_id:
        user_id = "test-user-123"

    # Validate session exists
    session_service = SessionService()
    session = await session_service.get_session(session_id)
    if not session:
        await websocket.close(code=WS_1008_POLICY_VIOLATION, reason="Invalid session")
        return

    # Connect to manager
    await manager.connect(websocket, session_id, user_id)

    try:
        # Send connection established event
        await manager.send_personal_message(
            WebSocketEvent(
                type="connected",
                data={"session_id": session_id, "user_id": user_id}
            ).dict(),
            session_id
        )

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = WebSocketMessage.parse_raw(data)
                await handle_websocket_message(websocket, message, session_id, user_id)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from session {session_id}")
                await manager.send_personal_message(
                    ErrorEvent(
                        type="error",
                        data={"message": "Invalid JSON format"}
                    ).dict(),
                    session_id
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message(
                    ErrorEvent(
                        type="error",
                        data={"message": str(e)}
                    ).dict(),
                    session_id
                )

    finally:
        manager.disconnect(session_id, user_id)


async def handle_websocket_message(
    websocket: WebSocket,
    message: WebSocketMessage,
    session_id: str,
    user_id: str
):
    """Handle incoming WebSocket messages based on type."""
    message_type = message.type

    if message_type == "execute":
        await handle_execute_message(message, session_id, user_id)
    elif message_type == "approve":
        await handle_approve_message(message, session_id, user_id)
    elif message_type == "reject":
        await handle_reject_message(message, session_id, user_id)
    elif message_type == "edit":
        await handle_edit_message(message, session_id, user_id)
    elif message_type == "cancel":
        await handle_cancel_message(message, session_id, user_id)
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
    user_id: str
):
    """Handle execute command message."""
    execute_msg = ExecuteMessage.parse_obj(message.data)

    agent_service = AgentService()
    execution_log_service = ExecutionLogService()

    try:
        # Create execution log entry
        execution_log = await execution_log_service.create_execution_log(
            session_id=session_id,
            command=execute_msg.command,
            plan=execute_msg.plan
        )

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

        # Execute agent command
        # Note: For now, we'll just send a placeholder response
        # TODO: Integrate with actual agent execution
        result_data = {
            "success": True,
            "message": f"Command '{execute_msg.command}' executed successfully",
            "execution_id": str(execution_log.id) if execution_log else None
        }

        # Send complete event
        await manager.send_personal_message(
            CompleteEvent(
                type="complete",
                data=result_data
            ).dict(),
            session_id
        )

    except Exception as e:
        logger.error(f"Error executing command for session {session_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "session_id": session_id,
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                }
            ).dict(),
            session_id
        )


async def handle_approve_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str
):
    """Handle approval message for pending requests."""
    approve_msg = ApproveMessage.parse_obj(message.data)

    approval_service = ApprovalService()

    try:
        # Approve the request
        await approval_service.approve_request(
            request_id=approve_msg.request_id,
            decision="approved"
        )

        # Send success event
        await manager.send_personal_message(
            WebSocketEvent(
                type="approved",
                data={
                    "request_id": approve_msg.request_id,
                    "decision": "approved"
                }
            ).dict(),
            session_id
        )

    except Exception as e:
        logger.error(f"Error approving request {approve_msg.request_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "request_id": approve_msg.request_id,
                    "message": str(e)
                }
            ).dict(),
            session_id
        )


async def handle_reject_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str
):
    """Handle rejection message for pending requests."""
    reject_msg = RejectMessage.parse_obj(message.data)

    approval_service = ApprovalService()

    try:
        # Reject the request
        await approval_service.approve_request(
            request_id=reject_msg.request_id,
            decision="rejected"
        )

        # Send rejection event
        await manager.send_personal_message(
            WebSocketEvent(
                type="rejected",
                data={
                    "request_id": reject_msg.request_id,
                    "decision": "rejected"
                }
            ).dict(),
            session_id
        )

    except Exception as e:
        logger.error(f"Error rejecting request {reject_msg.request_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "request_id": reject_msg.request_id,
                    "message": str(e)
                }
            ).dict(),
            session_id
        )


async def handle_edit_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str
):
    """Handle edit and approve message for pending requests."""
    edit_msg = EditMessage.parse_obj(message.data)

    approval_service = ApprovalService()

    try:
        # Edit and approve the request
        await approval_service.approve_request(
            request_id=edit_msg.request_id,
            decision="edited",
            edited_args=edit_msg.edited_args
        )

        # Send edit approved event
        await manager.send_personal_message(
            WebSocketEvent(
                type="edit_approved",
                data={
                    "request_id": edit_msg.request_id,
                    "decision": "edited",
                    "edited_args": edit_msg.edited_args
                }
            ).dict(),
            session_id
        )

    except Exception as e:
        logger.error(f"Error editing request {edit_msg.request_id}: {e}")
        await manager.send_personal_message(
            ErrorEvent(
                type="error",
                data={
                    "request_id": edit_msg.request_id,
                    "message": str(e)
                }
            ).dict(),
            session_id
        )


async def handle_cancel_message(
    message: WebSocketMessage,
    session_id: str,
    user_id: str
):
    """Handle cancellation message for ongoing execution."""
    cancel_msg = CancelMessage.parse_obj(message.data)

    try:
        # For now, just log the cancellation request
        # TODO: Integrate with actual agent execution cancellation
        logger.info(f"Cancellation requested for execution {cancel_msg.execution_id}")

        # Send cancellation event
        await manager.send_personal_message(
            WebSocketEvent(
                type="cancelled",
                data={
                    "execution_id": cancel_msg.execution_id,
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
                    "execution_id": cancel_msg.execution_id,
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