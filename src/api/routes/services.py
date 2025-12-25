"""
Service discovery and registry API routes.

This module provides endpoints for discovering, registering, and managing
services in the Paygent marketplace.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func as sql_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.services import Service
from src.services.service_registry import ServiceRegistryService

router = APIRouter()


class ServiceInfo(BaseModel):
    """Information about a service in the registry."""

    id: UUID
    name: str
    description: str | None = None
    endpoint: str
    pricing_model: str = Field(
        ..., description="pay-per-call, subscription, or metered"
    )
    price_amount: float
    price_token: str
    mcp_compatible: bool = False
    reputation_score: float = Field(default=0.0, ge=0.0)
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
    description: str | None = Field(default=None, max_length=2000)
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

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    endpoint: str | None = Field(default=None, min_length=1, max_length=512)
    pricing_model: str | None = None
    price_amount: float | None = Field(default=None, gt=0)
    mcp_compatible: bool | None = None


@router.get(
    "/discover",
    response_model=ServiceListResponse,
    summary="Discover services",
    description="Discover available services with optional filtering. Results are cached for 5 minutes.",
)
async def discover_services(
    category: str | None = Query(default=None, description="Filter by category"),
    min_price: float | None = Query(default=None, ge=0, description="Minimum price"),
    max_price: float | None = Query(default=None, ge=0, description="Maximum price"),
    min_reputation: float | None = Query(
        default=None, ge=0, description="Minimum reputation score"
    ),
    mcp_compatible: bool | None = Query(
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

    Results are cached for 5 minutes for performance.
    """
    # Use ServiceRegistryService which includes caching
    registry = ServiceRegistryService(db)
    services = await registry.discover_services(
        query="",  # No text query, just filters
        category=category,
        min_price=min_price,
        max_price=max_price,
        min_reputation=min_reputation,
        mcp_compatible=mcp_compatible,
        limit=limit,
        offset=offset,
    )

    # Get total count (uncached for accuracy)
    count_query = select(sql_func.count()).select_from(Service)
    # Apply same filters for count
    if min_price is not None:
        count_query = count_query.where(Service.price_amount >= min_price)
    if max_price is not None:
        count_query = count_query.where(Service.price_amount <= max_price)
    if min_reputation is not None:
        count_query = count_query.where(Service.reputation_score >= min_reputation)
    if mcp_compatible is not None:
        count_query = count_query.where(Service.mcp_compatible == mcp_compatible)
    # Note: category filter removed - Service model doesn't have category field

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Handle both Service objects (from DB) and dicts (from cache)
    service_list = []
    for service in services:
        if isinstance(service, dict):
            # Cached data is already in dict format
            service_list.append(ServiceInfo(**service))
        else:
            # Service object from database
            service_list.append(
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
            )

    return ServiceListResponse(
        services=service_list,
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
    description="Get current pricing information for a service. Cached for 1 minute.",
)
async def get_service_pricing(
    service_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ServicePricing:
    """Get current pricing for a service (with caching)."""
    registry = ServiceRegistryService(db)
    pricing = await registry.get_service_pricing(str(service_id))

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )

    return ServicePricing(
        service_id=UUID(pricing["service_id"]),
        pricing_model=pricing["pricing_model"],
        price_amount=pricing["price_amount"],
        price_token=pricing["price_token"],
        token_symbol=pricing["currency"],
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
