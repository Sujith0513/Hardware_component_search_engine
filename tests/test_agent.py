"""
test_agent.py - Integration tests for the LangGraph agent.

Tests the graph construction, node wiring, and end-to-end execution
with both known and unknown components.
"""

import pytest
from src.agent import build_graph, compile_graph, get_graph_mermaid
from src.state import AgentState


class TestGraphConstruction:
    """Test that the LangGraph StateGraph is correctly wired."""

    def test_graph_builds(self):
        """Graph should build without errors."""
        graph = build_graph()
        assert graph is not None

    def test_graph_compiles(self):
        """Graph should compile into a runnable."""
        app = compile_graph()
        assert app is not None

    def test_graph_has_mermaid(self):
        """Graph should produce a Mermaid diagram."""
        mermaid = get_graph_mermaid()
        assert isinstance(mermaid, str)
        assert len(mermaid) > 50
        # Should contain our node names
        assert "planner" in mermaid.lower() or "Planner" in mermaid

    def test_graph_nodes_exist(self):
        """All expected nodes should be in the graph."""
        graph = build_graph()
        compiled = graph.compile()
        mermaid = compiled.get_graph().draw_mermaid()
        expected_nodes = [
            "planner", "searcher", "extractor",
            "pricing", "validator", "formatter",
        ]
        mermaid_lower = mermaid.lower()
        for node in expected_nodes:
            assert node in mermaid_lower, f"Node '{node}' not found in graph"


class TestPricingLookup:
    """Test the pricing tool independently."""

    def test_known_component(self):
        from src.tools.pricing_lookup import lookup_pricing

        entries = lookup_pricing("ESP32-WROOM-32")
        assert len(entries) >= 1
        assert all(e.unit_price >= 0 for e in entries)
        assert all(e.stock_quantity >= 0 for e in entries)

    def test_unknown_component_fallback(self):
        from src.tools.pricing_lookup import lookup_pricing

        entries = lookup_pricing("NONEXISTENT_PART_XYZ")
        # Should return fallback entry
        assert len(entries) >= 1

    def test_fuzzy_match(self):
        from src.tools.pricing_lookup import lookup_pricing

        # Lowercase should still match
        entries = lookup_pricing("esp32-wroom-32")
        assert len(entries) >= 1

    def test_partial_match(self):
        from src.tools.pricing_lookup import lookup_pricing

        # "ESP32" should partially match "ESP32-WROOM-32"
        entries = lookup_pricing("ESP32")
        assert len(entries) >= 1


class TestStockValidator:
    """Test stock validation logic."""

    def test_normal_stock(self):
        from src.state import PricingEntry
        from src.tools.stock_validator import validate_stock

        entries = [
            PricingEntry(
                distributor="Mouser",
                unit_price=2.80,
                moq=1,
                stock_quantity=14523,
                url="https://mouser.com/test",
            ),
        ]
        status = validate_stock(entries)
        assert status.in_stock is True
        assert status.best_price == 2.80

    def test_suspicious_zero_price(self):
        from src.state import PricingEntry
        from src.tools.stock_validator import validate_stock

        entries = [
            PricingEntry(
                distributor="Sketchy",
                unit_price=0.0,
                moq=1,
                stock_quantity=9999,
                url="https://sketchy.com",
            ),
            PricingEntry(
                distributor="Legit",
                unit_price=5.00,
                moq=1,
                stock_quantity=100,
                url="https://legit.com",
            ),
        ]
        status = validate_stock(entries)
        # Should skip the $0 entry for best price
        assert status.best_price == 5.00
        assert status.best_distributor == "Legit"


class TestEndToEnd:
    """
    End-to-end agent tests.

    NOTE: These tests require API keys (TAVILY_API_KEY, GOOGLE_API_KEY).
    They will be skipped if keys are not available.
    """

    @pytest.fixture
    def check_api_keys(self):
        import os
        from dotenv import load_dotenv
        load_dotenv()

        tavily = os.getenv("TAVILY_API_KEY", "")
        google = os.getenv("GOOGLE_API_KEY", "")
        openai = os.getenv("OPENAI_API_KEY", "")

        if not tavily or tavily.startswith("tvly-xxx"):
            pytest.skip("TAVILY_API_KEY not configured")
        if not google and not openai:
            pytest.skip("No LLM API key configured (GOOGLE_API_KEY or OPENAI_API_KEY)")

    def test_esp32_full_pipeline(self, check_api_keys):
        """Full end-to-end test with ESP32-WROOM-32."""
        from src.agent import run_agent

        final_state = run_agent("ESP32-WROOM-32")
        report = final_state.get("final_output")

        assert report is not None, "Agent should produce a report"
        assert report["component_name"] == "ESP32-WROOM-32"
        assert report["manufacturer"] != "Unknown"
        assert len(report["key_pins_summary"]) > 0
        assert report["average_price"] > 0
        assert report["in_stock"] is True

    def test_ne555_full_pipeline(self, check_api_keys):
        """Full end-to-end test with NE555."""
        from src.agent import run_agent

        final_state = run_agent("NE555")
        report = final_state.get("final_output")

        assert report is not None
        assert report["average_price"] > 0
