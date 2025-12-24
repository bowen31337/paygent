"""
Service discovery and registry API routes.

This module provides endpoints for discovering, registering, and managing
services in the Paygent marketplace.
"""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func

from src.core.database import get_db
from src.models.services import Service
from src.services.service_registry import ServiceRegistryService

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
    # Build query with filters
    query = select(Service)

    # Apply filters
    if min_price is not None:
        query = query.where(Service.price_amount >= min_price)
    if max_price is not None:
        query = query.where(Service.price_amount <= max_price)
    if min_reputation is not None:
        query = query.where(Service.reputation_score >= min_reputation)
    if mcp_compatible is not None:
        query = query.where(Service.mcp_compatible == mcp_compatible)

    # Get total count
    count_query = select(sql_func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(Service.reputation_score.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    services = result.scalars().all()

    return ServiceListResponse(
        services=[
            ServiceInfo(
                id=service.id,
                name=service.name,
                description=service.description,
                endpoint=service.endpoint,
                pricing_model=service.pricing_model,
                price_amount=service.price_amount,
                price_token=service.price_token,
                mcp_compatible=service.mcp_compatible,
                reputation_score=service.reputation_score,
                total_calls=service.total_calls,
                created_at=service.created_at.isoformat(),
                updated_at=service.updated_at.isoformat(),
            )
            for service in services
        ],
        total=total,
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
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )

    return ServiceInfo(
        id=service.id,
        name=service.name,
        description=service.description,
        endpoint=service.endpoint,
        pricing_model=service.pricing_model,
        price_amount=service.price_amount,
        price_token=service.price_token,
        mcp_compatible=service.mcp_compatible,
        reputation_score=service.reputation_score,
        total_calls=service.total_calls,
        created_at=service.created_at.isoformat(),
        updated_at=service.updated_at.isoformat(),
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
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )

    # Map token address to symbol (simplified - in production, use a registry)
    token_symbol = "USDC" if "usdc" in service.price_token.lower() else service.price_token[:6]

    return ServicePricing(
        service_id=service.id,
        pricing_model=service.pricing_model,
        price_amount=service.price_amount,
        price_token=service.price_token,
        token_symbol=token_symbol,
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
    # Create new service
    new_service = Service(
        id=uuid4(),
        name=request.name,
        description=request.description,
        endpoint=request.endpoint,
        pricing_model=request.pricing_model,
        price_amount=request.price_amount,
        price_token=request.price_token,
        mcp_compatible=request.mcp_compatible,
        reputation_score=0.0,
        total_calls=0,
    )
    db.add(new_service)
    await db.commit()
    await db.refresh(new_service)

    return ServiceInfo(
        id=new_service.id,
        name=new_service.name,
        description=new_service.description,
        endpoint=new_service.endpoint,
        pricing_model=new_service.pricing_model,
        price_amount=new_service.price_amount,
        price_token=new_service.price_token,
        mcp_compatible=new_service.mcp_compatible,
        reputation_score=new_service.reputation_score,
        total_calls=new_service.total_calls,
        created_at=new_service.created_at.isoformat(),
        updated_at=new_service.updated_at.isoformat(),
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
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )

    # Update fields if provided
    if request.name is not None:
        service.name = request.name
    if request.description is not None:
        service.description = request.description
    if request.endpoint is not None:
        service.endpoint = request.endpoint
    if request.pricing_model is not None:
        service.pricing_model = request.pricing_model
    if request.price_amount is not None:
        service.price_amount = request.price_amount
    if request.mcp_compatible is not None:
        service.mcp_compatible = request.mcp_compatible

    await db.commit()
    await db.refresh(service)

    return ServiceInfo(
        id=service.id,
        name=service.name,
        description=service.description,
        endpoint=service.endpoint,
        pricing_model=service.pricing_model,
        price_amount=service.price_amount,
        price_token=service.price_token,
        mcp_compatible=service.mcp_compatible,
        reputation_score=service.reputation_score,
        total_calls=service.total_calls,
        created_at=service.created_at.isoformat(),
        updated_at=service.updated_at.isoformat(),
    )
