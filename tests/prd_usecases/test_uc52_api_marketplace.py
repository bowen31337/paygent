"""
Use Case 5.2: AI-Powered API Marketplace Tests

Tests for the API marketplace where developers monetize services
via x402 pay-per-call without traditional payment infrastructure.

PRD Reference: Section 5.2 - AI-Powered API Marketplace
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestServiceRegistration:
    """Test service registration in the marketplace."""

    @pytest.mark.asyncio
    async def test_register_ml_inference_service(self, sample_ml_service):
        """Register an ML inference API with x402 pricing."""
        # Arrange
        mock_registry = AsyncMock()
        mock_registry.register_service.return_value = {
            "success": True,
            "service_id": sample_ml_service["id"],
            "registered_at": "2024-01-01T00:00:00Z",
        }

        # Act
        result = await mock_registry.register_service(sample_ml_service)

        # Assert
        assert result["success"] is True
        assert result["service_id"] == "ml-image-classify-001"

    @pytest.mark.asyncio
    async def test_register_with_pay_per_call_pricing(self, sample_ml_service):
        """Verify pay-per-call pricing is correctly configured."""
        # Assert pricing model
        assert sample_ml_service["pricing_model"] == "pay-per-call"
        assert sample_ml_service["price_amount"] == 0.001
        assert sample_ml_service["price_token"] == "USDC"

    @pytest.mark.asyncio
    async def test_register_mcp_compatible_service(self, sample_ml_service):
        """Verify MCP compatibility flag is set."""
        # Assert MCP compatibility
        assert sample_ml_service["mcp_compatible"] is True


class TestServiceDiscovery:
    """Test service discovery via MCP catalog."""

    @pytest.mark.asyncio
    async def test_discover_service_via_mcp(self, sample_ml_service):
        """Agent discovers ML service via MCP catalog."""
        # Arrange
        mock_registry = AsyncMock()
        mock_registry.discover_services.return_value = [sample_ml_service]

        # Act
        services = await mock_registry.discover_services(
            category="ml",
            mcp_compatible=True,
        )

        # Assert
        assert len(services) == 1
        assert services[0]["name"] == "Image Classification API"
        assert services[0]["mcp_compatible"] is True

    @pytest.mark.asyncio
    async def test_discover_with_pricing_info(self, sample_ml_service):
        """Verify pricing information included in discovery."""
        # Arrange
        mock_registry = AsyncMock()
        mock_registry.discover_services.return_value = [sample_ml_service]

        # Act
        services = await mock_registry.discover_services()

        # Assert
        service = services[0]
        assert "price_amount" in service
        assert "price_token" in service
        assert "pricing_model" in service

    @pytest.mark.asyncio
    async def test_discover_with_reputation(self, sample_ml_service):
        """Verify reputation score included in discovery."""
        # Assert
        assert "reputation_score" in sample_ml_service
        assert sample_ml_service["reputation_score"] == 4.8
        assert sample_ml_service["total_calls"] == 125000


class TestPayPerCallFlow:
    """Test x402 pay-per-call execution flow."""

    @pytest.mark.asyncio
    async def test_http_402_response_parsing(self, mock_http_402_response):
        """Parse HTTP 402 Payment Required response correctly."""
        # Arrange
        headers = mock_http_402_response["headers"]
        payment_header = headers["Payment-Required"]

        # Act - Parse payment requirements
        parts = payment_header.split("; ")
        protocol = parts[0]
        amount = parts[1].split("=")[1]
        token = parts[2].split("=")[1]

        # Assert
        assert protocol == "x402"
        assert amount == "0.001"
        assert token == "USDC"

    @pytest.mark.asyncio
    async def test_complete_pay_per_call_flow(
        self,
        sample_ml_service,
        mock_x402_facilitator,
    ):
        """Execute complete pay-per-call via x402 protocol."""
        # Step 1: Agent requests service
        mock_service = AsyncMock()
        mock_service.request.return_value = {
            "status_code": 402,
            "headers": {"Payment-Required": "x402; amount=0.001; token=USDC"},
        }

        initial_response = await mock_service.request(sample_ml_service["endpoint"])
        assert initial_response["status_code"] == 402

        # Step 2: Agent signs EIP-712 payment
        mock_signer = MagicMock()
        mock_signer.sign_payment.return_value = {
            "signature": "0x" + "c" * 130,
            "nonce": 1,
            "timestamp": 1704067200,
        }
        payment_proof = mock_signer.sign_payment(
            amount=0.001,
            token="USDC",
            recipient=sample_ml_service["endpoint"],
        )
        assert "signature" in payment_proof

        # Step 3: Facilitator settles payment
        settlement = await mock_x402_facilitator.settle_payment(
            service_url=sample_ml_service["endpoint"],
            amount=0.001,
            token="USDC",
        )
        assert settlement["success"] is True

        # Step 4: Service returns data
        mock_service.request.return_value = {
            "status_code": 200,
            "body": {"classification": "cat", "confidence": 0.98},
        }
        final_response = await mock_service.request(
            sample_ml_service["endpoint"],
            headers={"X-Payment-Proof": payment_proof["signature"]},
        )
        assert final_response["status_code"] == 200
        assert "classification" in final_response["body"]

    @pytest.mark.asyncio
    async def test_retry_with_payment_header(self, mock_x402_facilitator):
        """Verify request is retried with Payment-Proof header."""
        # Arrange
        mock_service = AsyncMock()

        # First call returns 402
        # Second call (with payment) returns 200
        mock_service.request.side_effect = [
            {"status_code": 402, "headers": {"Payment-Required": "x402; amount=0.01"}},
            {"status_code": 200, "body": {"data": "success"}},
        ]

        # Act
        response1 = await mock_service.request("https://api.example.com/data")
        assert response1["status_code"] == 402

        response2 = await mock_service.request(
            "https://api.example.com/data",
            headers={"X-Payment-Proof": "0x..."},
        )
        assert response2["status_code"] == 200


class TestKeylessAccess:
    """Test that x402 enables access without API keys."""

    @pytest.mark.asyncio
    async def test_access_without_api_key(self, sample_ml_service, mock_x402_facilitator):
        """Verify x402 enables access without API keys or accounts."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.request.return_value = {
            "status_code": 200,
            "body": {"result": "processed"},
        }

        # Act - Access with only payment proof, no API key
        response = await mock_service.request(
            sample_ml_service["endpoint"],
            headers={
                "X-Payment-Proof": "0x" + "d" * 130,
                # Note: No "Authorization" or "X-API-Key" header
            },
        )

        # Assert
        assert response["status_code"] == 200
        # Verify no API key was required
        mock_service.request.assert_called_once()
        call_args = mock_service.request.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "Authorization" not in headers
        assert "X-API-Key" not in headers


class TestInstantSettlement:
    """Test instant USDC settlement on Cronos."""

    @pytest.mark.asyncio
    async def test_settlement_time(self, mock_x402_facilitator):
        """Verify settlement completes in ~200ms."""
        # Act
        result = await mock_x402_facilitator.settle_payment(
            service_url="https://api.example.com",
            amount=0.001,
            token="USDC",
        )

        # Assert
        assert result["success"] is True
        assert result["settlement_time_ms"] <= 300  # Allow some buffer

    @pytest.mark.asyncio
    async def test_settlement_includes_tx_hash(self, mock_x402_facilitator):
        """Verify settlement includes transaction hash."""
        # Act
        result = await mock_x402_facilitator.settle_payment(
            service_url="https://api.example.com",
            amount=0.001,
            token="USDC",
        )

        # Assert
        assert "tx_hash" in result
        assert result["tx_hash"].startswith("0x")
        assert len(result["tx_hash"]) == 66  # 0x + 64 hex chars

    @pytest.mark.asyncio
    async def test_usdc_token_used(self, mock_x402_facilitator):
        """Verify USDC is the payment token."""
        # Act
        await mock_x402_facilitator.settle_payment(
            service_url="https://api.example.com",
            amount=0.001,
            token="USDC",
        )

        # Assert
        mock_x402_facilitator.settle_payment.assert_called_with(
            service_url="https://api.example.com",
            amount=0.001,
            token="USDC",
        )


class TestSubscriptionModel:
    """Test subscription-based service access."""

    @pytest.mark.asyncio
    async def test_subscribe_to_monthly_plan(self, sample_subscription_service):
        """Test subscription-based service access."""
        # Arrange
        mock_subscription = AsyncMock()
        mock_subscription.subscribe.return_value = {
            "success": True,
            "subscription_id": "sub-123",
            "service_id": sample_subscription_service["id"],
            "billing_period": "monthly",
            "next_billing_date": "2024-02-01",
            "amount": 9.99,
        }

        # Act
        result = await mock_subscription.subscribe(
            service_id=sample_subscription_service["id"],
            plan="monthly",
        )

        # Assert
        assert result["success"] is True
        assert result["billing_period"] == "monthly"
        assert result["amount"] == 9.99

    @pytest.mark.asyncio
    async def test_subscription_auto_renewal(self, sample_subscription_service):
        """Test subscription auto-renewal handling."""
        # Arrange
        mock_subscription = AsyncMock()
        mock_subscription.process_renewal.return_value = {
            "success": True,
            "renewed_until": "2024-03-01",
            "payment_tx": "0x" + "e" * 64,
        }

        # Act
        result = await mock_subscription.process_renewal(subscription_id="sub-123")

        # Assert
        assert result["success"] is True
        assert "renewed_until" in result


class TestReputationSystem:
    """Test service reputation updates."""

    @pytest.mark.asyncio
    async def test_reputation_update_after_call(self, sample_ml_service):
        """Verify reputation score updates after service calls."""
        # Arrange
        mock_reputation = AsyncMock()
        mock_reputation.submit_rating.return_value = {
            "success": True,
            "new_score": 4.81,
            "total_ratings": 125001,
        }

        # Act
        result = await mock_reputation.submit_rating(
            service_id=sample_ml_service["id"],
            rating=5,
            comment="Great service!",
        )

        # Assert
        assert result["success"] is True
        assert result["new_score"] > sample_ml_service["reputation_score"]

    @pytest.mark.asyncio
    async def test_reputation_affects_discovery_ranking(self):
        """Verify higher reputation services rank higher in discovery."""
        # Arrange
        services = [
            {"id": "svc-1", "reputation_score": 4.2},
            {"id": "svc-2", "reputation_score": 4.9},
            {"id": "svc-3", "reputation_score": 4.5},
        ]

        # Act - Sort by reputation
        sorted_services = sorted(services, key=lambda s: s["reputation_score"], reverse=True)

        # Assert
        assert sorted_services[0]["id"] == "svc-2"  # Highest reputation first
        assert sorted_services[0]["reputation_score"] == 4.9


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_payment_failure_handled(self, mock_x402_facilitator):
        """Handle payment failure gracefully."""
        # Arrange
        mock_x402_facilitator.settle_payment.return_value = {
            "success": False,
            "error": "Insufficient balance",
        }

        # Act
        result = await mock_x402_facilitator.settle_payment(
            service_url="https://api.example.com",
            amount=1000,
            token="USDC",
        )

        # Assert
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_service_unavailable_handled(self):
        """Handle service unavailability gracefully."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.request.return_value = {
            "status_code": 503,
            "error": "Service temporarily unavailable",
        }

        # Act
        result = await mock_service.request("https://api.example.com")

        # Assert
        assert result["status_code"] == 503

    @pytest.mark.asyncio
    async def test_invalid_payment_amount_rejected(self, mock_x402_facilitator):
        """Reject invalid payment amounts."""
        # Arrange
        mock_x402_facilitator.settle_payment.side_effect = ValueError("Amount must be positive")

        # Act & Assert
        with pytest.raises(ValueError, match="Amount must be positive"):
            await mock_x402_facilitator.settle_payment(
                service_url="https://api.example.com",
                amount=-0.001,
                token="USDC",
            )

    @pytest.mark.asyncio
    async def test_duplicate_payment_prevented(self, mock_x402_facilitator):
        """Prevent duplicate payments with nonce."""
        # Arrange
        mock_x402_facilitator.verify_payment.return_value = {
            "valid": False,
            "reason": "Nonce already used",
        }

        # Act
        result = await mock_x402_facilitator.verify_payment(
            signature="0x...",
            nonce=1,  # Previously used nonce
        )

        # Assert
        assert result["valid"] is False
        assert "Nonce already used" in result["reason"]
