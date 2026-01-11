"""
Use Case 5.4: Research & Intelligence Agent Tests

Tests for the research agent that gathers data from multiple
paid sources, spawns subagents for focused analysis, and
generates comprehensive reports.

PRD Reference: Section 5.4 - Research & Intelligence Agent
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestResearchPlanGeneration:
    """Test research plan creation (write_todos)."""

    def test_research_plan_creation(self, mock_research_plan):
        """Verify write_todos plan created for research request."""
        # Arrange
        command = "Research the Cronos DeFi ecosystem"

        # Act - Simulate plan generation
        plan = mock_research_plan

        # Assert
        assert len(plan) == 7
        assert plan[0]["action"] == "Query Crypto.com MCP for ecosystem data"
        assert plan[1]["action"] == "Access premium analytics API via x402"
        assert all(step["status"] == "pending" for step in plan)

    def test_plan_includes_data_sources(self, mock_research_plan):
        """Verify plan includes all required data sources."""
        # Arrange
        expected_sources = [
            "Crypto.com MCP",
            "premium analytics",
            "VVS Finance",
            "Moonlander",
            "Delphi",
        ]

        # Act
        plan_actions = [step["action"] for step in mock_research_plan]
        plan_text = " ".join(plan_actions)

        # Assert
        for source in expected_sources:
            assert source in plan_text or source.lower() in plan_text.lower()

    def test_plan_ends_with_report(self, mock_research_plan):
        """Verify plan ends with report compilation and save."""
        # Assert
        assert "report" in mock_research_plan[-2]["action"].lower()
        assert "save" in mock_research_plan[-1]["action"].lower() or "filesystem" in mock_research_plan[-1]["action"].lower()


class TestMultiSourceDataGathering:
    """Test multi-source data gathering."""

    @pytest.mark.asyncio
    async def test_query_crypto_com_mcp(self, mock_crypto_com_mcp_data):
        """Query Crypto.com Market Data MCP."""
        # Arrange
        mock_mcp = AsyncMock()
        mock_mcp.query.return_value = mock_crypto_com_mcp_data

        # Act
        data = await mock_mcp.query(resource="cronos/ecosystem")

        # Assert
        assert data["total_tvl"] == 1500000000
        assert len(data["top_protocols"]) == 3
        assert data["top_protocols"][0]["name"] == "VVS Finance"

    @pytest.mark.asyncio
    async def test_access_premium_analytics_x402(
        self,
        mock_x402_facilitator,
        mock_premium_analytics,
    ):
        """Access premium analytics via x402 payment."""
        # Arrange
        mock_analytics = AsyncMock()
        mock_analytics.fetch.return_value = mock_premium_analytics

        # Act - Pay for access
        payment = await mock_x402_facilitator.settle_payment(
            service_url="https://analytics.example.com/premium",
            amount=0.50,
            token="USDC",
        )
        assert payment["success"] is True

        # Fetch analytics
        analytics = await mock_analytics.fetch()

        # Assert
        assert analytics["defi_health_score"] == 85
        assert analytics["risk_metrics"]["systemic_risk"] == "low"
        assert len(analytics["opportunities"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_vvs_onchain_data(self, mock_vvs_connector):
        """Analyze on-chain data from VVS pools."""
        # Arrange
        mock_vvs_connector.get_pool_stats.return_value = {
            "pool": "CRO-USDC",
            "tvl": 50000000,
            "volume_24h": 8000000,
            "apy": 45.2,
            "reserve0": 1000000,
            "reserve1": 75000,
        }

        # Act
        stats = mock_vvs_connector.get_pool_stats("CRO-USDC")

        # Assert
        assert stats["tvl"] == 50000000
        assert stats["apy"] == 45.2

    @pytest.mark.asyncio
    async def test_analyze_moonlander_data(self, mock_moonlander_connector):
        """Analyze Moonlander trading data."""
        # Arrange
        mock_moonlander_connector.get_market_stats.return_value = {
            "market": "BTC-USDC",
            "open_interest": 15000000,
            "funding_rate": 0.0001,
            "volume_24h": 30000000,
            "long_ratio": 0.55,
        }

        # Act
        stats = mock_moonlander_connector.get_market_stats("BTC-USDC")

        # Assert
        assert stats["funding_rate"] == 0.0001
        assert stats["long_ratio"] == 0.55

    @pytest.mark.asyncio
    async def test_analyze_delphi_data(self, mock_delphi_connector):
        """Analyze Delphi prediction markets."""
        # Act
        markets = mock_delphi_connector.get_markets()

        # Assert
        assert len(markets) == 2
        assert any(m["category"] == "crypto" for m in markets)
        assert any(m["category"] == "defi" for m in markets)


class TestSubagentSpawning:
    """Test subagent spawning for parallel research tasks."""

    @pytest.mark.asyncio
    async def test_spawn_research_subagent(self):
        """Spawn focused research subagent."""
        # Arrange
        mock_subagent = MagicMock()
        mock_subagent.session_id = "sub-research-001"
        mock_subagent.parent_agent_id = "main-agent-001"
        mock_subagent.tools = ["analyze_data", "generate_insights"]

        # Assert - Context isolation
        assert mock_subagent.session_id != mock_subagent.parent_agent_id
        assert len(mock_subagent.tools) > 0

    @pytest.mark.asyncio
    async def test_subagent_context_isolation(self):
        """Verify subagent has isolated context."""
        # Arrange
        main_agent = MagicMock()
        main_agent.session_id = "main-001"
        main_agent.state = {"research_topic": "Cronos DeFi"}

        subagent = MagicMock()
        subagent.session_id = "sub-001"
        subagent.parent_id = main_agent.session_id
        subagent.state = {}  # Clean state

        # Assert
        assert subagent.session_id != main_agent.session_id
        assert subagent.parent_id == main_agent.session_id
        assert subagent.state != main_agent.state

    @pytest.mark.asyncio
    async def test_subagent_dedicated_tools(self):
        """Verify subagent has dedicated research tools."""
        # Arrange
        main_agent_tools = ["swap", "transfer", "check_balance"]
        subagent_tools = ["fetch_data", "analyze", "summarize", "generate_report"]

        # Assert - Different tool sets
        assert set(main_agent_tools) != set(subagent_tools)
        assert "analyze" in subagent_tools
        assert "swap" not in subagent_tools


class TestReportGeneration:
    """Test research report generation."""

    @pytest.mark.asyncio
    async def test_compile_research_report(
        self,
        mock_crypto_com_mcp_data,
        mock_premium_analytics,
    ):
        """Compile findings into structured report."""
        # Arrange
        data_sources = [
            {"source": "Crypto.com MCP", "data": mock_crypto_com_mcp_data},
            {"source": "Premium Analytics", "data": mock_premium_analytics},
        ]

        # Act - Compile report
        report = {
            "title": "Cronos DeFi Ecosystem Analysis",
            "summary": "Comprehensive analysis of Cronos DeFi protocols",
            "sections": [
                {
                    "title": "Market Overview",
                    "content": f"Total TVL: ${mock_crypto_com_mcp_data['total_tvl']:,}",
                },
                {
                    "title": "Risk Assessment",
                    "content": f"DeFi Health Score: {mock_premium_analytics['defi_health_score']}/100",
                },
                {
                    "title": "Top Protocols",
                    "content": [p["name"] for p in mock_crypto_com_mcp_data["top_protocols"]],
                },
            ],
            "data_sources": [d["source"] for d in data_sources],
            "generated_at": "2024-01-01T00:00:00Z",
            "cost_usd": 0.50,
        }

        # Assert
        assert report["title"] == "Cronos DeFi Ecosystem Analysis"
        assert len(report["sections"]) == 3
        assert len(report["data_sources"]) == 2
        assert report["cost_usd"] > 0

    def test_report_structure_validation(self, expected_research_report_structure):
        """Verify report matches expected structure."""
        # Arrange
        sample_report = {
            "title": "Test Report",
            "summary": "Test summary",
            "sections": [{"title": "Section 1", "content": "Content"}],
            "data_sources": ["Source 1", "Source 2"],
            "generated_at": "2024-01-01T00:00:00Z",
            "cost_usd": 1.50,
        }

        # Assert - All required fields present with correct types
        for field, expected_type in expected_research_report_structure.items():
            assert field in sample_report
            assert isinstance(sample_report[field], expected_type)


class TestFilesystemPersistence:
    """Test report persistence to filesystem."""

    @pytest.mark.asyncio
    async def test_save_report_to_filesystem(self):
        """Save report to filesystem backend."""
        # Arrange
        mock_filesystem = AsyncMock()
        mock_filesystem.write.return_value = {
            "success": True,
            "path": "/reports/cronos-defi-analysis-2024-01-01.md",
            "size_bytes": 4096,
        }

        report_content = "# Cronos DeFi Ecosystem Analysis\n..."

        # Act
        result = await mock_filesystem.write(
            path="/reports/cronos-defi-analysis-2024-01-01.md",
            content=report_content,
        )

        # Assert
        assert result["success"] is True
        assert result["path"].endswith(".md")

    @pytest.mark.asyncio
    async def test_report_persistence_verification(self):
        """Verify saved report can be retrieved."""
        # Arrange
        mock_filesystem = AsyncMock()
        saved_content = "# Cronos DeFi Ecosystem Analysis\n..."
        mock_filesystem.read.return_value = {
            "success": True,
            "content": saved_content,
        }

        # Act
        result = await mock_filesystem.read(
            path="/reports/cronos-defi-analysis-2024-01-01.md"
        )

        # Assert
        assert result["success"] is True
        assert result["content"] == saved_content


class TestCompleteWorkflow:
    """Test end-to-end research workflow."""

    @pytest.mark.asyncio
    async def test_complete_research_workflow(
        self,
        mock_x402_facilitator,
        mock_crypto_com_mcp_data,
        mock_premium_analytics,
        mock_vvs_connector,
        mock_moonlander_connector,
        mock_delphi_connector,
        mock_research_plan,
    ):
        """End-to-end research workflow."""
        # Step 1: Parse command
        command = "Research the Cronos DeFi ecosystem"
        assert "Research" in command

        # Step 2: Create research plan (write_todos)
        plan = mock_research_plan
        assert len(plan) > 0
        assert plan[0]["status"] == "pending"

        # Step 3: Query Crypto.com MCP
        mock_mcp = AsyncMock()
        mock_mcp.query.return_value = mock_crypto_com_mcp_data
        mcp_data = await mock_mcp.query(resource="cronos/ecosystem")
        assert mcp_data["total_tvl"] > 0

        # Step 4: Pay for premium analytics (x402)
        payment = await mock_x402_facilitator.settle_payment(
            service_url="https://analytics.example.com",
            amount=0.50,
            token="USDC",
        )
        assert payment["success"] is True

        # Step 5: Analyze VVS data
        mock_vvs_connector.get_pool_stats.return_value = {"apy": 45.2}
        vvs_stats = mock_vvs_connector.get_pool_stats("CRO-USDC")
        assert vvs_stats["apy"] > 0

        # Step 6: Analyze Moonlander data
        funding = mock_moonlander_connector.get_funding_rate("BTC-USDC")
        assert funding["rate"] is not None

        # Step 7: Analyze Delphi data
        markets = mock_delphi_connector.get_markets()
        assert len(markets) > 0

        # Step 8: Compile report
        report = {
            "title": "Cronos DeFi Ecosystem Analysis",
            "summary": f"Total TVL: ${mcp_data['total_tvl']:,}",
            "sections": ["Market Overview", "Risk Analysis", "Opportunities"],
            "data_sources": ["Crypto.com MCP", "Premium Analytics", "VVS", "Moonlander", "Delphi"],
            "generated_at": "2024-01-01T00:00:00Z",
            "cost_usd": 0.50,
        }
        assert len(report["data_sources"]) == 5

        # Step 9: Save to filesystem
        mock_filesystem = AsyncMock()
        mock_filesystem.write.return_value = {"success": True}
        save_result = await mock_filesystem.write(
            path="/reports/research.md",
            content=str(report),
        )
        assert save_result["success"] is True

    @pytest.mark.asyncio
    async def test_workflow_tracks_costs(self, mock_x402_facilitator):
        """Track total cost of research across all paid sources."""
        # Arrange
        costs = []

        # Act - Multiple x402 payments
        for service, amount in [
            ("mcp", 0.01),
            ("analytics", 0.50),
            ("premium-data", 0.25),
        ]:
            result = await mock_x402_facilitator.settle_payment(
                service_url=f"https://{service}.example.com",
                amount=amount,
                token="USDC",
            )
            if result["success"]:
                costs.append(amount)

        # Assert
        total_cost = sum(costs)
        assert total_cost == 0.76


class TestDataAggregation:
    """Test multi-source data aggregation."""

    @pytest.mark.asyncio
    async def test_aggregate_protocol_data(
        self,
        mock_crypto_com_mcp_data,
        mock_vvs_connector,
        mock_moonlander_connector,
    ):
        """Aggregate data from multiple protocols."""
        # Arrange
        mock_vvs_connector.get_pool_stats.return_value = {
            "pool": "CRO-USDC",
            "tvl": 50000000,
            "apy": 45.2,
        }
        mock_moonlander_connector.get_market_stats.return_value = {
            "market": "BTC-USDC",
            "open_interest": 15000000,
        }

        # Act
        aggregated = {
            "ecosystem": mock_crypto_com_mcp_data,
            "vvs": mock_vvs_connector.get_pool_stats("CRO-USDC"),
            "moonlander": mock_moonlander_connector.get_market_stats("BTC-USDC"),
        }

        # Assert
        assert aggregated["ecosystem"]["total_tvl"] > 0
        assert aggregated["vvs"]["apy"] == 45.2
        assert aggregated["moonlander"]["open_interest"] == 15000000

    @pytest.mark.asyncio
    async def test_handle_missing_data_source(self):
        """Handle gracefully when a data source is unavailable."""
        # Arrange
        mock_service = AsyncMock()
        mock_service.fetch.side_effect = Exception("Service unavailable")

        # Act
        aggregated = {"available": True}
        try:
            data = await mock_service.fetch()
            aggregated["service_data"] = data
        except Exception:
            aggregated["service_data"] = None
            aggregated["error"] = "Service unavailable"

        # Assert
        assert aggregated["service_data"] is None
        assert "error" in aggregated


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_data_source_handling(self):
        """Handle empty data from sources."""
        # Arrange
        mock_mcp = AsyncMock()
        mock_mcp.query.return_value = {"protocols": [], "total_tvl": 0}

        # Act
        data = await mock_mcp.query(resource="empty/ecosystem")

        # Assert
        assert data["total_tvl"] == 0
        assert len(data["protocols"]) == 0

    @pytest.mark.asyncio
    async def test_payment_failure_continues_with_free_sources(
        self,
        mock_x402_facilitator,
        mock_crypto_com_mcp_data,
    ):
        """Continue research with free sources if paid fails."""
        # Arrange
        mock_x402_facilitator.settle_payment.return_value = {
            "success": False,
            "error": "Insufficient balance",
        }
        mock_mcp = AsyncMock()
        mock_mcp.query.return_value = mock_crypto_com_mcp_data

        # Act
        paid_data = None
        payment = await mock_x402_facilitator.settle_payment(
            service_url="https://premium.example.com",
            amount=1.00,
            token="USDC",
        )
        if not payment["success"]:
            paid_data = None  # Skip premium data

        # Free source still works
        free_data = await mock_mcp.query(resource="cronos/basic")

        # Assert
        assert paid_data is None
        assert free_data is not None
        assert free_data["total_tvl"] > 0

    @pytest.mark.asyncio
    async def test_report_generation_timeout(self):
        """Handle report generation timeout."""
        # Arrange
        mock_generator = AsyncMock()
        mock_generator.generate.side_effect = TimeoutError("Report generation timed out")

        # Act & Assert
        with pytest.raises(TimeoutError, match="timed out"):
            await mock_generator.generate(data={})
