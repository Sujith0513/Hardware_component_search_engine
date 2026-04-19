"""
state.py - Pydantic Models & Agent State Schema

All data contracts for the Hardware Sourcing & Specs Agent.
Uses Pydantic v2 BaseModel for strict validation at every boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field, HttpUrl


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Component Data Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Dimensions(BaseModel):
    """Physical dimensions of the component."""
    length: float = Field(..., description="Length in mm")
    width: float = Field(..., description="Width in mm")
    height: float = Field(..., description="Height in mm")

class PinInfo(BaseModel):
    """Describes a single pin on an electronic component."""

    pin_name: str = Field(..., description="Pin label, e.g. GPIO0, VCC, GND")
    pin_number: str = Field(..., description="Physical pin number or pad ID")
    function: str = Field(
        ..., description="Primary function, e.g. ADC, UART_TX, Power"
    )


class DatasheetInfo(BaseModel):
    """Structured information extracted from datasheet search results."""

    manufacturer: str = Field(..., description="Component manufacturer name")
    datasheet_url: str = Field(
        ..., description="URL to the official datasheet PDF"
    )
    description: str = Field(
        ..., description="Brief description of the component"
    )
    key_pins: list[PinInfo] = Field(
        ..., min_length=1, description="Key pins and their functions"
    )
    package_type: Optional[str] = Field(
        None, description="Package type, e.g. QFN-48, DIP-8"
    )
    dimensions_mm: Optional[Dimensions] = Field(
        None, description="Physical dimensions in mm"
    )
    operating_voltage: Optional[str] = Field(
        None, description="Operating voltage range, e.g. 2.2V-3.6V"
    )


class PricingEntry(BaseModel):
    """Pricing data from a single distributor."""

    distributor: str = Field(..., description="Distributor name, e.g. Mouser")
    country: str = Field(default="Global", description="Country of operations")
    currency: str = Field(default="USD", description="Currency symbol/code")
    unit_price: float = Field(
        ..., ge=0, description="Unit price"
    )
    moq: int = Field(
        ..., ge=1, description="Minimum order quantity"
    )
    stock_quantity: int = Field(
        ..., ge=0, description="Number of units in stock"
    )
    url: str = Field(..., description="Product page URL at the distributor")


class StockStatus(BaseModel):
    """Aggregated stock availability analysis."""

    in_stock: bool = Field(
        ..., description="True if at least one distributor has stock > 0"
    )
    total_stock_across_distributors: int = Field(
        ..., ge=0, description="Sum of stock across all distributors"
    )
    best_price: float = Field(..., ge=0, description="Lowest unit price")
    best_distributor: str = Field(
        ..., description="Distributor offering the best price"
    )


class CrossValidationResult(BaseModel):
    """Result of dual-LLM cross-validation for data reliability."""

    primary_llm: str = Field(..., description="Primary LLM used, e.g. 'gemini-2.5-flash'")
    secondary_llm: str = Field(..., description="Secondary LLM used, e.g. 'gpt-4o-mini'")
    manufacturer_match: bool = Field(..., description="Whether both LLMs agree on manufacturer")
    description_match: bool = Field(..., description="Whether descriptions are semantically similar")
    pin_count_match: bool = Field(..., description="Whether both found similar number of pins")
    voltage_match: bool = Field(..., description="Whether operating voltage agrees")
    confidence_score: float = Field(
        ..., ge=0, le=1.0,
        description="Overall confidence score (0-1). 1.0 = full agreement"
    )
    discrepancies: list[str] = Field(
        default_factory=list,
        description="List of fields where the two LLMs disagreed"
    )
    verdict: str = Field(
        ..., description="Human-readable verdict: 'HIGH CONFIDENCE', 'MEDIUM CONFIDENCE', or 'LOW CONFIDENCE - MANUAL REVIEW RECOMMENDED'"
    )


class ComponentReport(BaseModel):
    """
    Final structured output - the deliverable.
    Contains all sourced information about an electronic component.
    """

    component_name: str = Field(..., description="Queried component name")
    manufacturer: str = Field(..., description="Component manufacturer")
    datasheet_url: str = Field(..., description="Link to the official datasheet")
    description: str = Field(..., description="Brief component description")
    key_pins_summary: list[PinInfo] = Field(
        ..., description="Summary of key pins and their functions"
    )
    average_price: float = Field(
        ..., ge=0, description="Average price across distributors"
    )
    price_range: str = Field(
        ..., description="Price range string, e.g. '$2.50 - $4.80'"
    )
    pricing_breakdown: list[PricingEntry] = Field(
        ..., description="Detailed pricing from each distributor"
    )
    in_stock: bool = Field(
        ..., description="Whether the component is currently in stock"
    )
    total_available_stock: int = Field(
        ..., ge=0, description="Total stock across all distributors"
    )
    best_deal: str = Field(
        ..., description="Best deal summary, e.g. 'Mouser @ $2.50 (MOQ: 1)'"
    )
    package_type: Optional[str] = Field(None, description="Package type")
    dimensions_mm: Optional[dict[str, float]] = Field(None, description="Physical dimensions in mm (length, width, height)")
    operating_voltage: Optional[str] = Field(
        None, description="Operating voltage range"
    )
    image_url: Optional[str] = Field(
        None, description="URL to a representative image of the component"
    )
    youtube_links: list[str] = Field(
        default_factory=list, description="YouTube tutorial links"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this report was generated",
    )
    cross_validation: Optional[dict[str, Any]] = Field(
        None, description="Dual-LLM cross-validation results (if secondary LLM available)"
    )
    agent_reasoning_trace: list[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning trace from the agent",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LangGraph Agent State
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AgentState(TypedDict):
    """
    Shared state schema for the LangGraph StateGraph.
    Passed between nodes; each node reads and writes specific keys.
    """

    # ── Inputs ──
    component_query: str  # Original user query

    # ── Intermediate data ──
    search_plan: str  # Generated by the Planner node
    search_results: list[dict[str, Any]]  # Raw Tavily search results
    search_images: list[str]  # Image URLs found by Tavily
    youtube_links: list[str]  # YouTube tutorial URLs
    datasheet_info: Optional[dict[str, Any]]  # Parsed DatasheetInfo (as dict)
    secondary_datasheet_info: Optional[dict[str, Any]]  # From secondary LLM
    cross_validation: Optional[dict[str, Any]]  # CrossValidationResult as dict
    pricing_data: list[dict[str, Any]]  # List of PricingEntry dicts
    stock_status: Optional[dict[str, Any]]  # StockStatus as dict

    # ── Output ──
    final_output: Optional[dict[str, Any]]  # ComponentReport as dict

    # ── Control flow ──
    error_log: list[str]  # Accumulated error messages
    retry_count: int  # Number of retries attempted (max 2)
    current_step: str  # Current node name (for UI streaming)
    reasoning_trace: list[str]  # Step-by-step agent decisions
