"""
Approval workflow API routes.

This module provides endpoints for managing human-in-the-loop approval
requests for sensitive agent operations.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

router = APIRouter()


class ApprovalRequest(BaseModel):
    """Information about an approval request."""

    id: UUID
    session_id: UUID
    tool_name: str
    tool_args: dict
    decision: str = Field(..., description="pending, approved, rejected, or edited")
    edited_args: Optional[dict] = None
    estimated_cost_usd: Optional[float] = None
    created_at: str
    decision_made_at: Optional[str] = None


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

    reason: Optional[str] = Field(default=None, max_length=500)


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
    session_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """
    List all pending approval requests.

    Optionally filter by session_id.
    """
    # TODO: Implement pending approvals listing
    return ApprovalListResponse(
        requests=[],
        total=0,
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
    # TODO: Implement approval request retrieval
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Approval request {request_id} not found",
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
    """
    # TODO: Implement approval logic
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Approval request {request_id} not found",
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
    """
    # TODO: Implement rejection logic
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Approval request {request_id} not found",
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
    """
    # TODO: Implement edit and approval logic
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Approval request {request_id} not found",
    )
