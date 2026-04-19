"""
stock_validator.py - Stock availability validation tool.

Aggregates pricing data to determine stock status, best price,
and flags suspicious entries.
"""

from __future__ import annotations

from src.state import PricingEntry, StockStatus
from src.utils.logger import logger


def validate_stock(pricing_data: list[PricingEntry]) -> StockStatus:
    """
    Validate stock availability across all distributors.

    Aggregates stock counts, identifies the best deal, and flags
    suspicious entries (e.g., price = $0, unrealistically high stock).

    Args:
        pricing_data: List of PricingEntry from the pricing lookup tool.

    Returns:
        StockStatus model with aggregated availability info.
    """
    if not pricing_data:
        logger.warning("No pricing data to validate stock")
        return StockStatus(
            in_stock=False,
            total_stock_across_distributors=0,
            best_price=0.0,
            best_distributor="N/A",
        )

    logger.info(f"Validating stock across {len(pricing_data)} distributors")

    total_stock = 0
    best_price = float("inf")
    best_distributor = ""
    suspicious_entries = []

    for entry in pricing_data:
        # Flag suspicious entries
        if entry.unit_price == 0 and entry.stock_quantity > 0:
            suspicious_entries.append(
                f"{entry.distributor}: $0 price with stock (suspicious)"
            )
            logger.warning(
                f"Suspicious: {entry.distributor} has $0 price with "
                f"{entry.stock_quantity} stock"
            )
            continue

        if entry.stock_quantity > 1_000_000:
            suspicious_entries.append(
                f"{entry.distributor}: Unrealistic stock ({entry.stock_quantity})"
            )
            logger.warning(
                f"Suspicious: {entry.distributor} claims {entry.stock_quantity} stock"
            )
            # Still count it but flag it

        total_stock += entry.stock_quantity

        # Track best price (only from in-stock distributors)
        if entry.stock_quantity > 0 and entry.unit_price < best_price:
            best_price = entry.unit_price
            best_distributor = entry.distributor

    # Handle edge case where no valid entries found
    if best_price == float("inf"):
        best_price = 0.0
        best_distributor = "N/A"

    in_stock = total_stock > 0

    if suspicious_entries:
        logger.warning(
            f"Found {len(suspicious_entries)} suspicious entries: "
            f"{suspicious_entries}"
        )

    status = StockStatus(
        in_stock=in_stock,
        total_stock_across_distributors=total_stock,
        best_price=best_price,
        best_distributor=best_distributor,
    )

    logger.info(
        f"Stock validation: in_stock={in_stock}, "
        f"total={total_stock}, "
        f"best=${best_price:.2f} @ {best_distributor}"
    )

    return status
