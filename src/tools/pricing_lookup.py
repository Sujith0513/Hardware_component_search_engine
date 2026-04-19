"""
pricing_lookup.py - Distributor pricing lookup tool.

Uses a mock JSON database for reliable demos, with architecture
designed for easy swap to real distributor APIs (DigiKey, Mouser).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.state import PricingEntry
from src.utils.cache import TTLCache
from src.utils.logger import logger

# Module-level cache (shared across calls within a session)
_pricing_cache = TTLCache(default_ttl=3600)

# Path to mock pricing data
_MOCK_DATA_PATH = Path(__file__).parent.parent / "data" / "mock_pricing.json"


def _load_mock_data() -> dict[str, list[dict[str, Any]]]:
    """Load the mock pricing database from JSON."""
    try:
        with open(_MOCK_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Mock pricing data not found at: {_MOCK_DATA_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in mock pricing data: {e}")
        return {}


def _normalize_component_name(name: str) -> str:
    """
    Normalize component name for fuzzy matching.
    E.g., 'esp32-wroom-32' -> 'ESP32-WROOM-32'
    """
    return name.strip().upper().replace(" ", "-")


def _fuzzy_match(query: str, candidates: list[str]) -> str | None:
    """
    Find the best matching component name from available candidates.
    Supports partial matching (e.g., 'ESP32' matches 'ESP32-WROOM-32').
    """
    query_norm = _normalize_component_name(query)

    # Exact match first
    for c in candidates:
        if _normalize_component_name(c) == query_norm:
            return c

    # Partial match: query is contained in candidate
    for c in candidates:
        if query_norm in _normalize_component_name(c):
            return c

    # Partial match: candidate is contained in query
    for c in candidates:
        if _normalize_component_name(c) in query_norm:
            return c

    return None


def lookup_pricing(component_name: str) -> list[PricingEntry]:
    """
    Look up pricing data for an electronic component.

    Uses a mock database for reliable demos. The interface is designed
    so that swapping to real DigiKey/Mouser APIs requires changing only
    this function's internals.

    Args:
        component_name: Component name or part number.

    Returns:
        List of PricingEntry models from various distributors.
    """
    logger.info(f"Looking up pricing for: {component_name}")

    # Check cache first
    cache_key = f"pricing:{_normalize_component_name(component_name)}"
    cached = _pricing_cache.get(cache_key)
    if cached is not None:
        logger.info(f"Cache hit for {component_name}")
        return cached

    # Load mock data
    mock_data = _load_mock_data()

    if not mock_data:
        logger.warning("No mock pricing data available")
        return []

    # Find matching component
    matched_name = _fuzzy_match(component_name, list(mock_data.keys()))

    if matched_name is None:
        logger.warning(
            f"Component '{component_name}' not found in mock database. "
            f"Available: {list(mock_data.keys())}"
        )
        # Return a generic fallback entry so the agent can still produce output
        fallback = [
            PricingEntry(
                distributor="Generic Supplier",
                country="Global",
                currency="USD",
                unit_price=5.00,
                moq=1,
                stock_quantity=100,
                url=f"https://www.findchips.com/search/{component_name}",
            )
        ]
        _pricing_cache.set(cache_key, fallback)
        return fallback

    # Parse matched entries into Pydantic models
    raw_entries = mock_data[matched_name]
    entries = []

    for raw in raw_entries:
        try:
            entry = PricingEntry(**raw)
            entries.append(entry)
        except Exception as e:
            logger.warning(f"Skipping invalid pricing entry: {e}")

    logger.info(
        f"Found {len(entries)} pricing entries for '{matched_name}'"
    )

    # Cache the result
    _pricing_cache.set(cache_key, entries)
    return entries
