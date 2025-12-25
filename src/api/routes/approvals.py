"""
Approval workflow API routes.

This module provides endpoints for managing human-in-the-loop approval
requests for sensitive agent operations.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.agent_sessions import ApprovalRequest as ApprovalRequestModel

router = APIRouter()


class ApprovalRequest(BaseModel):
    """Information about an approval request."""

    id: UUID
    session_id: UUID
    tool_name: str
    tool_args: dict
    decision: str = Field(..., description="pending, approved, rejected, or edited")
    edited_args: dict | None = None
    created_at: str
    decision_made_at: str | None = None


class ApprovalListResponse(BaseModel):
    """Response for listing approval requests."""

    requests: list[ApprovalRequest]
    total: int


class ApproveRequest(BaseModel):
    """Request body for approving a request."""

    # No additional fields needed for simple approval
    pass


class RejectRequest(BaseModel):
    """Request body for rejecting a request."""

    reason: str | None = Field(default=None, max_length=500)


class EditApproveRequest(BaseModel):
    """Request body for editing and approving a request."""

    edited_args: dict = Field(..., description="Modified tool arguments")


class ApprovalResponse(BaseModel):
    """Response after processing an approval decision."""

    request_id: UUID
    decision: str
    message: str


@router.get(
    "/pending",
    response_model=ApprovalListResponse,
    summary="List pending approvals",
    description="Get all pending approval requests.",
)
async def list_pending_approvals(
    session_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """
    List all pending approval requests.

    Optionally filter by session_id.
    """
    # Build query
    query = select(ApprovalRequestModel).where(ApprovalRequestModel.decision == "pending")

    if session_id:
        query = query.where(ApprovalRequestModel.session_id == session_id)

    # Order by oldest first
    query = query.order_by(ApprovalRequestModel.created_at.asc())

    result = await db.execute(query)
    requests = result.scalars().all()

    # Convert to response format
    request_list = [
        ApprovalRequest(
            id=req.id,
            session_id=req.session_id,
            tool_name=req.tool_name,
            tool_args=req.tool_args,
            decision=req.decision,
            edited_args=req.edited_args,
            created_at=req.created_at.isoformat(),
            decision_made_at=req.decision_made_at.isoformat() if req.decision_made_at else None,
        )
        for req in requests
    ]

    return ApprovalListResponse(
        requests=request_list,
        total=len(request_list),
    )


@router.get(
    "/{request_id}",
    response_model=ApprovalRequest,
    summary="Get approval request",
    description="Get details of a specific approval request.",
)
async def get_approval_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApprovalRequest:
    """Get details of a specific approval request."""
    result = await db.execute(
        select(ApprovalRequestModel).where(ApprovalRequestModel.id == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found",
        )

    return ApprovalRequest(
        id=req.id,
        session_id=req.session_id,
        tool_name=req.tool_name,
        tool_args=req.tool_args,
        decision=req.decision,
        edited_args=req.edited_args,
        created_at=req.created_at.isoformat(),
        decision_made_at=req.decision_made_at.isoformat() if req.decision_made_at else None,
    )


@router.post(
    "/{request_id}/approve",
    response_model=ApprovalResponse,
    summary="Approve request",
    description="Approve a pending request and resume agent execution.",
)
async def approve_request(
    request_id: UUID,
    request: ApproveRequest = None,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    Approve a pending request.

    This will resume the paused agent execution with the original arguments.

    NOTE: This is a mock implementation. In production, this would
    signal the agent to resume execution.
    """
    result = await db.execute(
        select(ApprovalRequestModel).where(ApprovalRequestModel.id == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found",
        )

    if req.decision != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request has already been {req.decision}",
        )

    # Update status
    req.decision = "approved"
    req.decision_made_at = datetime.utcnow()
    await db.commit()

    return ApprovalResponse(
        request_id=request_id,
        decision="approved",
        message="Request approved. Agent execution will resume.",
    )


@router.post(
    "/{request_id}/reject",
    response_model=ApprovalResponse,
    summary="Reject request",
    description="Reject a pending request and stop agent execution.",
)
async def reject_request(
    request_id: UUID,
    request: RejectRequest = None,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    Reject a pending request.

    This will stop the agent execution and log the rejection.

    NOTE: This is a mock implementation. In production, this would
    signal the agent to stop execution.
    """
    result = await db.execute(
        select(ApprovalRequestModel).where(ApprovalRequestModel.id == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found",
        )

    if req.decision != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request has already been {req.decision}",
        )

    # Update status
    req.decision = "rejected"
    req.decision_made_at = datetime.utcnow()
    await db.commit()

    return ApprovalResponse(
        request_id=request_id,
        decision="rejected",
        message=f"Request rejected. Reason: {request.reason if request and request.reason else 'No reason provided'}",
    )


@router.post(
    "/{request_id}/edit",
    response_model=ApprovalResponse,
    summary="Edit and approve",
    description="Edit the request arguments and approve.",
)
async def edit_and_approve(
    request_id: UUID,
    request: EditApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    Edit the tool arguments and approve the request.

    This allows modifying parameters (e.g., reducing payment amount)
    before approving the operation.

    NOTE: This is a mock implementation. In production, this would
    signal the agent to resume execution with edited arguments.
    """
    result = await db.execute(
        select(ApprovalRequestModel).where(ApprovalRequestModel.id == request_id)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found",
        )

    if req.decision != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request has already been {req.decision}",
        )

    # Update status with edited args
    req.decision = "edited"
    req.edited_args = request.edited_args
    req.decision_made_at = datetime.utcnow()
    await db.commit()

    return ApprovalResponse(
        request_id=request_id,
        decision="edited",
        message="Request edited and approved. Agent will resume with modified arguments.",
    )
