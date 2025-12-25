"""
Service registry service.

This service manages MCP-compatible service discovery and registry
for the Paygent platform.
"""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.services import Service
from src.services.cache import CacheService

logger = logging.getLogger(__name__)


class ServiceRegistryService:
    """Service for managing MCP-compatible service registry."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the service registry.

        Args:
            db: Database session
        """
        self.db = db
        self.cache_service = CacheService()

    async def discover_services(
        self,
        query: str = "",
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_reputation: float | None = None,
        mcp_compatible: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Service | dict[str, Any]]:
        """
        Discover services based on search criteria with caching.

        Args:
            query: Search query
            category: Optional service category
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_reputation: Minimum reputation score filter
            mcp_compatible: Filter for MCP-compatible services
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching services
        """
        try:
            # Create cache key from all parameters
            import hashlib
            cache_params = f"{query}:{category}:{min_price}:{max_price}:{min_reputation}:{mcp_compatible}:{limit}:{offset}"
            cache_key = f"services:discover:{hashlib.md5(cache_params.encode()).hexdigest()}"

            # Try cache first (5 minute TTL)
            cached = await self.cache_service.get(cache_key)
            if cached:
                logger.info(f"Cache hit for services discovery: {query}")
                # Convert cached dicts back to Service objects if needed
                # For now, return as-is since API expects dicts or objects
                return cached

            # Build query
            stmt = select(Service)

            # Apply filters
            if query:
                stmt = stmt.where(
                    Service.name.contains(query) | Service.description.contains(query)
                )

            # Note: category filter removed - Service model doesn't have category field

            if min_price is not None:
                stmt = stmt.where(Service.price_amount >= min_price)

            if max_price is not None:
                stmt = stmt.where(Service.price_amount <= max_price)

            if min_reputation is not None:
                stmt = stmt.where(Service.reputation_score >= min_reputation)

            if mcp_compatible is not None:
                stmt = stmt.where(Service.mcp_compatible == mcp_compatible)

            # Apply ordering and pagination
            stmt = stmt.order_by(Service.reputation_score.desc()).limit(limit).offset(offset)

            # Execute query
            result = await self.db.execute(stmt)
            services = result.scalars().all()

            logger.info(f"Found {len(services)} services for query: {query}")

            # Cache results for 5 minutes (300 seconds)
            if services:
                # Convert Service objects to dictionaries for JSON serialization
                services_data = [
                    {
                        "id": str(service.id),
                        "name": service.name,
                        "description": service.description,
                        "endpoint": service.endpoint,
                        "pricing_model": service.pricing_model,
                        "price_amount": float(service.price_amount),
                        "price_token": service.price_token,
                        "mcp_compatible": service.mcp_compatible,
                        "reputation_score": float(service.reputation_score),
                        "total_calls": service.total_calls,
                        "created_at": service.created_at.isoformat(),
                        "updated_at": service.updated_at.isoformat(),
                    }
                    for service in services
                ]
                await self.cache_service.set(cache_key, services_data, expiration=300)
                logger.info(f"Cached {len(services)} services for {cache_key}")

            return services

        except Exception as e:
            logger.error(f"Service discovery failed: {e}")
            return []

    async def get_service(self, service_id: str) -> Service | None:
        """
        Get service by ID.

        Args:
            service_id: Service ID

        Returns:
            Service object if found
        """
        try:
            stmt = select(Service).where(Service.id == service_id)
            result = await self.db.execute(stmt)
            service = result.scalar_one_or_none()

            return service

        except Exception as e:
            logger.error(f"Failed to get service {service_id}: {e}")
            return None

    async def register_service(
        self,
        name: str,
        description: str,
        endpoint: str,
        pricing_model: str,
        price_amount: float,
        price_token: str,
        category: str | None = None,
        mcp_compatible: bool = False,
    ) -> Service | None:
        """
        Register a new service.

        Args:
            name: Service name
            description: Service description
            endpoint: Service endpoint URL
            pricing_model: Pricing model (pay-per-call, subscription, metered)
            price_amount: Price amount
            price_token: Price token symbol
            category: Optional service category
            mcp_compatible: Whether service supports MCP protocol

        Returns:
            Created service object
        """
        try:
            service = Service(
                name=name,
                description=description,
                endpoint=endpoint,
                pricing_model=pricing_model,
                price_amount=price_amount,
                price_token=price_token,
                category=category,
                mcp_compatible=mcp_compatible,
                reputation_score=0.0,
                total_calls=0,
            )

            self.db.add(service)
            await self.db.commit()
            await self.db.refresh(service)

            # Invalidate cache
            await self.cache_service.delete_pattern("services:*")

            logger.info(f"Registered service: {name}")
            return service

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to register service: {e}")
            return None

    async def update_service(
        self,
        service_id: str,
        **kwargs,
    ) -> Service | None:
        """
        Update service information.

        Args:
            service_id: Service ID
            **kwargs: Fields to update

        Returns:
            Updated service object
        """
        try:
            service = await self.get_service(service_id)
            if not service:
                return None

            # Update fields
            for key, value in kwargs.items():
                if hasattr(service, key):
                    setattr(service, key, value)

            await self.db.commit()
            await self.db.refresh(service)

            # Invalidate cache
            await self.cache_service.delete_pattern(f"service:{service_id}")
            await self.cache_service.delete_pattern("services:*")

            logger.info(f"Updated service: {service_id}")
            return service

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update service {service_id}: {e}")
            return None

    async def get_service_pricing(self, service_id: str) -> dict[str, Any] | None:
        """
        Get current pricing for a service.

        Args:
            service_id: Service ID

        Returns:
            Pricing information
        """
        try:
            service = await self.get_service(service_id)
            if not service:
                return None

            # Check cache first
            cache_key = f"price:{service_id}"
            cached_price = await self.cache_service.get(cache_key)
            if cached_price:
                return json.loads(cached_price)

            # Get current price
            pricing = {
                "service_id": str(service.id),
                "name": service.name,
                "pricing_model": service.pricing_model,
                "price_amount": float(service.price_amount),
                "price_token": service.price_token,
                "currency": "USD",  # TODO: Implement actual currency conversion
                "last_updated": service.updated_at.isoformat(),
            }

            # Cache for 1 minute
            await self.cache_service.set(
                cache_key, json.dumps(pricing), expiration=60
            )

            return pricing

        except Exception as e:
            logger.error(f"Failed to get service pricing: {e}")
            return None

    async def update_service_reputation(
        self, service_id: str, rating: float
    ) -> Service | None:
        """
        Update service reputation score.

        Args:
            service_id: Service ID
            rating: New rating (0.0 to 5.0)

        Returns:
            Updated service object
        """
        try:
            # Convert string to UUID if needed
            from uuid import UUID
            service_id_uuid = UUID(service_id) if isinstance(service_id, str) else service_id

            service = await self.get_service(service_id_uuid)
            if not service:
                return None

            # Update reputation (simple moving average)
            current_score = service.reputation_score or 0.0
            total_calls = service.total_calls or 0

            new_score = ((current_score * total_calls) + rating) / (total_calls + 1)

            service.reputation_score = new_score
            service.total_calls = total_calls + 1

            await self.db.commit()
            await self.db.refresh(service)

            # Invalidate cache
            await self.cache_service.delete_pattern(f"service:{service_id}")
            await self.cache_service.delete_pattern("services:*")

            logger.info(f"Updated reputation for service {service_id}: {new_score}")
            return service

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update service reputation: {e}")
            return None

    async def get_mcp_services(self) -> list[Service]:
        """
        Get all MCP-compatible services.

        Returns:
            List of MCP-compatible services
        """
        try:
            # Check cache first
            cached_services = await self.cache_service.get("mcp_services")
            if cached_services:
                return json.loads(cached_services)

            # Query MCP-compatible services
            stmt = select(Service).where(Service.mcp_compatible)
            result = await self.db.execute(stmt)
            services = result.scalars().all()

            # Cache for 5 minutes
            services_data = [
                {
                    "id": str(service.id),
                    "name": service.name,
                    "description": service.description,
                    "endpoint": service.endpoint,
                    "pricing_model": service.pricing_model,
                    "price_amount": float(service.price_amount),
                    "price_token": service.price_token,
                    "reputation_score": float(service.reputation_score),
                    "total_calls": service.total_calls,
                }
                for service in services
            ]

            await self.cache_service.set(
                "mcp_services", json.dumps(services_data), expiration=300
            )

            return services

        except Exception as e:
            logger.error(f"Failed to get MCP services: {e}")
            return []

    async def search_services(self, query: str, **filters) -> list[Service]:
        """
        Advanced service search with filters.

        Args:
            query: Search query
            **filters: Additional filters (category, pricing_model, etc.)

        Returns:
            List of matching services
        """
        try:
            stmt = select(Service).where(
                Service.name.contains(query) | Service.description.contains(query)
            )

            # Apply filters
            for key, value in filters.items():
                if hasattr(Service, key):
                    stmt = stmt.where(getattr(Service, key) == value)

            result = await self.db.execute(stmt)
            services = result.scalars().all()

            return services

        except Exception as e:
            logger.error(f"Service search failed: {e}")
            return []

    async def get_service_stats(self, service_id: str) -> dict[str, Any]:
        """
        Get service usage statistics.

        Args:
            service_id: Service ID

        Returns:
            Service statistics
        """
        try:
            service = await self.get_service(service_id)
            if not service:
                return {"error": f"Service {service_id} not found"}

            return {
                "service_id": str(service.id),
                "name": service.name,
                "total_calls": service.total_calls,
                "reputation_score": float(service.reputation_score),
                "pricing_model": service.pricing_model,
                "price_amount": float(service.price_amount),
                "price_token": service.price_token,
            }

        except Exception as e:
            logger.error(f"Failed to get service stats: {e}")
            return {"error": str(e)}


class MCPClient:
    """Client for interacting with MCP-compatible services."""

    def __init__(self, service_registry: ServiceRegistryService):
        """
        Initialize MCP client.

        Args:
            service_registry: Service registry service
        """
        self.service_registry = service_registry
        self.client = None  # TODO: Implement MCP client
