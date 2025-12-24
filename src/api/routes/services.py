"""
Service discovery and registry API routes.

This module provides endpoints for discovering, registering, and managing
services in the Paygent marketplace.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

router = APIRouter()


class ServiceInfo(BaseModel):
    """Information about a service in the registry."""

    id: UUID
    name: str
    description: Optional[str] = None
    endpoint: str
    pricing_model: str = Field(
        ..., description="pay-per-call, subscription, or metered"
    )
    price_amount: float
    price_token: str
    mcp_compatible: bool = False
    reputation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    total_calls: int = 0
    created_at: str
    updated_at: str


class ServicePricing(BaseModel):
    """Pricing information for a service."""

    service_id: UUID
    pricing_model: str
    price_amount: float
    price_token: str
    token_symbol: str


class ServiceListResponse(BaseModel):
    """Response for listing services."""

    services: list[ServiceInfo]
    total: int
    offset: int
    limit: int


class CreateServiceRequest(BaseModel):
    """Request body for creating a new service."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    endpoint: str = Field(..., min_length=1, max_length=512)
    pricing_model: str = Field(
        default="pay-per-call",
        description="pay-per-call, subscription, or metered",
    )
    price_amount: float = Field(..., gt=0)
    price_token: str = Field(..., description="Token address for payment")
    mcp_compatible: bool = False


class UpdateServiceRequest(BaseModel):
    """Request body for updating a service."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    endpoint: Optional[str] = Field(default=None, min_length=1, max_length=512)
    pricing_model: Optional[str] = None
    price_amount: Optional[float] = Field(default=None, gt=0)
    mcp_compatible: Optional[bool] = None


@router.get(
    "/discover",
    response_model=ServiceListResponse,
    summary="Discover services",
    description="Discover available services with optional filtering.",
)
async def discover_services(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    min_price: Optional[float] = Query(default=None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(default=None, ge=0, description="Maximum price"),
    min_reputation: Optional[float] = Query(
        default=None, ge=0, le=1, description="Minimum reputation score"
    ),
    mcp_compatible: Optional[bool] = Query(
        default=None, description="Filter MCP-compatible services"
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ServiceListResponse:
    """
    Discover services in the registry.

    Supports filtering by:
    - category: Service category
    - min_price/max_price: Price range
    - min_reputation: Minimum reputation score
    - mcp_compatible: MCP protocol compatibility
    """
    # TODO: Implement service discovery
    return ServiceListResponse(
        services=[],
        total=0,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{service_id}",
    response_model=ServiceInfo,
    summary="Get service details",
    description="Get detailed information about a specific service.",
)
async def get_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ServiceInfo:
    """Get details of a specific service."""
    # TODO: Implement service retrieval
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Service {service_id} not found",
    )


@router.get(
    "/{service_id}/pricing",
    response_model=ServicePricing,
    summary="Get service pricing",
    description="Get current pricing information for a service.",
)
async def get_service_pricing(
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ServicePricing:
    """Get current pricing for a service."""
    # TODO: Implement pricing retrieval
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Service {service_id} not found",
    )


@router.post(
    "",
    response_model=ServiceInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Register new service",
    description="Register a new service in the registry (admin only).",
)
async def create_service(
    request: CreateServiceRequest,
    db: AsyncSession = Depends(get_db),
) -> ServiceInfo:
    """
    Register a new service in the registry.

    Requires admin authentication.
    """
    # TODO: Implement service creation with admin auth
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Service creation not yet implemented",
    )


@router.put(
    "/{service_id}",
    response_model=ServiceInfo,
    summary="Update service",
    description="Update an existing service (admin only).",
)
async def update_service(
    service_id: UUID,
    request: UpdateServiceRequest,
    db: AsyncSession = Depends(get_db),
) -> ServiceInfo:
    """
    Update an existing service.

    Requires admin authentication.
    """
    # TODO: Implement service update with admin auth
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Service {service_id} not found",
    )
