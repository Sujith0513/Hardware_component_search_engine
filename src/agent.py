"""
agent.py - LangGraph StateGraph: The Agentic Reasoning Core.

Defines a multi-node state graph with conditional edges, retry loops,
and dual-LLM cross-validation for autonomous hardware component research.

Architecture:
    START -> Planner -> Searcher -> Extractor -> Pricing -> Validator -> Formatter -> END
                           ^                                   |
                           |__________ retry (max 2) __________|
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from src.state import (
    AgentState,
    ComponentReport,
    DatasheetInfo,
    PricingEntry,
    StockStatus,
)
from src.tools.datasheet_extractor import extract_datasheet_info, extract_with_cross_validation
from src.tools.pricing_lookup import lookup_pricing
from src.tools.stock_validator import validate_stock
from src.tools.tavily_search import search_component
from src.utils.logger import logger

load_dotenv()

MAX_RETRIES = 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Node Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def plan_node(state: AgentState) -> dict[str, Any]:
    """
    PLANNER NODE: Analyze the query and create a research plan.
    Decides what information to search for based on the component name.
    """
    component = state["component_query"]
    logger.info(f"[PLANNER] Creating research plan for: {component}")

    plan = (
        f"Research plan for '{component}':\n"
        f"1. Search for official datasheet and manufacturer info\n"
        f"2. Extract key specifications (pins, voltage, package)\n"
        f"3. Look up pricing from major distributors\n"
        f"4. Validate stock availability\n"
        f"5. Compile structured report"
    )

    trace = state.get("reasoning_trace", [])
    trace.append(
        f"[PLANNER] Created research plan for '{component}'. "
        f"Will search for datasheet, extract specs, check pricing, and validate stock."
    )

    return {
        "search_plan": plan,
        "current_step": "planner",
        "reasoning_trace": trace,
    }


def search_node(state: AgentState) -> dict[str, Any]:
    """
    SEARCHER NODE: Execute web searches using Tavily.
    Performs two searches: one for datasheet, one for general specs.
    """
    component = state["component_query"]
    retry_count = state.get("retry_count", 0)
    logger.info(
        f"[SEARCHER] Searching for '{component}' (attempt {retry_count + 1})"
    )

    trace = state.get("reasoning_trace", [])
    all_results: list[dict[str, Any]] = []

    try:
        # Search for datasheet (Increased results for better extraction)
        trace.append(
            f"[SEARCHER] Executing datasheet search for '{component}'..."
        )
        ds_resp = search_component(component, search_type="datasheet", max_results=10)
        all_results.extend(ds_resp["results"])
        ds_images = ds_resp.get("images", [])

        # Search for general specs
        trace.append(
            f"[SEARCHER] Executing general specifications search for '{component}'..."
        )
        gen_resp = search_component(component, search_type="general", max_results=10)
        all_results.extend(gen_resp["results"])
        # Prioritize general images (hardware/pinouts) over datasheet cover PDFs
        found_images = gen_resp.get("images", []) + ds_images
        
        # Search for YouTube Tutorials
        yt_links = []
        try:
            trace.append(f"[SEARCHER] Executing YouTube tutorial search for '{component}'...")
            yt_resp = search_component(f"{component} site:youtube.com", search_type="youtube", max_results=5)
            yt_urls = [res["url"] for res in yt_resp.get("results", []) if "youtube.com/watch" in str(res.get("url", ""))]
            seen = set()
            for u in yt_urls:
                if u not in seen and len(yt_links) < 3:
                    seen.add(u)
                    yt_links.append(u)
            trace.append(f"[SEARCHER] Found {len(yt_links)} YouTube tutorials.")
        except Exception as e:
            logger.warning(f"[SEARCHER] YouTube search failed: {e}")

        trace.append(
            f"[SEARCHER] Found {len(all_results)} total search results and {len(found_images)} images."
        )
        logger.info(f"[SEARCHER] Collected {len(all_results)} results")

    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        logger.error(f"[SEARCHER] {error_msg}")
        trace.append(f"[SEARCHER] ERROR: {error_msg}")
        errors = state.get("error_log", [])
        errors.append(error_msg)
        return {
            "search_results": [],
            "error_log": errors,
            "current_step": "searcher",
            "reasoning_trace": trace,
        }

    return {
        "search_results": all_results,
        "search_images": found_images,
        "youtube_links": yt_links,
        "current_step": "searcher",
        "reasoning_trace": trace,
    }


def extract_node(state: AgentState) -> dict[str, Any]:
    """
    EXTRACTOR NODE: Use LLM(s) to extract structured datasheet info
    from raw search results. If secondary LLM is available, performs
    dual-LLM cross-validation for higher reliability.
    """
    component = state["component_query"]
    search_results = state.get("search_results", [])
    logger.info(f"[EXTRACTOR] Extracting datasheet info for: {component}")

    trace = state.get("reasoning_trace", [])
    trace.append(
        f"[EXTRACTOR] Analyzing {len(search_results)} search results "
        f"with LLM to extract structured component data..."
    )

    try:
        # Try dual-LLM cross-validation first
        primary_info, secondary_data, cv_result = extract_with_cross_validation(
            search_results, component
        )

        if primary_info:
            trace.append(
                f"[EXTRACTOR] Primary LLM extracted: "
                f"Manufacturer={primary_info.manufacturer}, "
                f"{len(primary_info.key_pins)} key pins, "
                f"Package={primary_info.package_type or 'N/A'}"
            )

            result = {
                "datasheet_info": primary_info.model_dump(),
                "current_step": "extractor",
                "reasoning_trace": trace,
            }

            # Add cross-validation results if available
            if cv_result:
                trace.append(
                    f"[CROSS-VALIDATION] Dual-LLM check: "
                    f"{cv_result.primary_llm} vs {cv_result.secondary_llm} | "
                    f"Confidence: {cv_result.confidence_score:.0%} | "
                    f"Verdict: {cv_result.verdict}"
                )
                if cv_result.discrepancies:
                    trace.append(
                        f"[CROSS-VALIDATION] Discrepancies found: "
                        f"{'; '.join(cv_result.discrepancies)}"
                    )
                else:
                    trace.append(
                        "[CROSS-VALIDATION] Both LLMs fully agree on all fields!"
                    )
                result["secondary_datasheet_info"] = secondary_data
                result["cross_validation"] = cv_result.model_dump()
            else:
                trace.append(
                    "[EXTRACTOR] Single-LLM mode (add OPENAI_API_KEY for "
                    "dual-LLM cross-validation)"
                )
                result["secondary_datasheet_info"] = None
                result["cross_validation"] = None

            return result
        else:
            trace.append(
                "[EXTRACTOR] WARNING: Could not extract datasheet info. "
                "Will retry search with different query if retries remain."
            )
            errors = state.get("error_log", [])
            errors.append("Datasheet extraction returned no results")
            return {
                "datasheet_info": None,
                "secondary_datasheet_info": None,
                "cross_validation": None,
                "error_log": errors,
                "current_step": "extractor",
                "reasoning_trace": trace,
            }

    except Exception as e:
        error_msg = f"Extraction failed: {str(e)}"
        logger.error(f"[EXTRACTOR] {error_msg}")
        trace.append(f"[EXTRACTOR] ERROR: {error_msg}")
        errors = state.get("error_log", [])
        errors.append(error_msg)
        return {
            "datasheet_info": None,
            "secondary_datasheet_info": None,
            "cross_validation": None,
            "error_log": errors,
            "current_step": "extractor",
            "reasoning_trace": trace,
        }


def pricing_node(state: AgentState) -> dict[str, Any]:
    """
    PRICING NODE: Look up pricing from distributors.
    """
    component = state["component_query"]
    logger.info(f"[PRICING] Looking up pricing for: {component}")

    trace = state.get("reasoning_trace", [])
    trace.append(
        f"[PRICING] Querying distributor pricing databases for '{component}'..."
    )

    try:
        entries = lookup_pricing(component)
        pricing_dicts = [e.model_dump() for e in entries]

        trace.append(
            f"[PRICING] Found pricing from {len(entries)} distributors. "
            + (
                f"Price range: {min(e.unit_price for e in entries):.2f} - "
                f"{max(e.unit_price for e in entries):.2f} (Local currencies)"
                if entries
                else "No pricing data."
            )
        )

        return {
            "pricing_data": pricing_dicts,
            "current_step": "pricing",
            "reasoning_trace": trace,
        }

    except Exception as e:
        error_msg = f"Pricing lookup failed: {str(e)}"
        logger.error(f"[PRICING] {error_msg}")
        trace.append(f"[PRICING] ERROR: {error_msg}")
        errors = state.get("error_log", [])
        errors.append(error_msg)
        return {
            "pricing_data": [],
            "error_log": errors,
            "current_step": "pricing",
            "reasoning_trace": trace,
        }


def validate_node(state: AgentState) -> dict[str, Any]:
    """
    VALIDATOR NODE: Check stock availability and validate data completeness.
    """
    logger.info("[VALIDATOR] Validating stock and data completeness")

    trace = state.get("reasoning_trace", [])
    pricing_dicts = state.get("pricing_data", [])

    # Reconstruct PricingEntry models
    entries = [PricingEntry(**p) for p in pricing_dicts]

    # Validate stock
    stock = validate_stock(entries)

    trace.append(
        f"[VALIDATOR] Stock check: "
        f"{'IN STOCK' if stock.in_stock else 'OUT OF STOCK'}, "
        f"Total available: {stock.total_stock_across_distributors}, "
        f"Best numerical price: {stock.best_price:.2f} @ {stock.best_distributor}"
    )

    # Check data completeness
    datasheet_info = state.get("datasheet_info")
    missing_fields = []
    if not datasheet_info:
        missing_fields.append("datasheet_info")
    if not pricing_dicts:
        missing_fields.append("pricing_data")

    if missing_fields:
        trace.append(
            f"[VALIDATOR] WARNING: Missing data for: {', '.join(missing_fields)}. "
            f"Retry count: {state.get('retry_count', 0)}/{MAX_RETRIES}"
        )

    return {
        "stock_status": stock.model_dump(),
        "current_step": "validator",
        "reasoning_trace": trace,
    }


def format_node(state: AgentState) -> dict[str, Any]:
    """
    FORMATTER NODE: Compile all gathered data into the final
    structured ComponentReport.
    """
    logger.info("[FORMATTER] Compiling final report")

    trace = state.get("reasoning_trace", [])
    trace.append("[FORMATTER] Compiling all data into final structured report...")

    # Extract data from state
    datasheet = state.get("datasheet_info") or {}
    pricing_dicts = state.get("pricing_data", [])
    stock = state.get("stock_status") or {}

    # Reconstruct Pydantic models
    pricing_entries = [PricingEntry(**p) for p in pricing_dicts]
    stock_status = StockStatus(**stock) if stock else StockStatus(
        in_stock=False, total_stock_across_distributors=0,
        best_price=0.0, best_distributor="N/A",
    )

    # Calculate averages
    if pricing_entries:
        prices = [e.unit_price for e in pricing_entries]
        avg_price = sum(prices) / len(prices)
        price_range = f"{min(prices):.2f} - {max(prices):.2f} (Mixed)"
    else:
        avg_price = 0.0
        price_range = "N/A"

    # Build best deal string
    if stock_status.in_stock:
        best_deal = (
            f"{stock_status.best_distributor} @ "
            f"${stock_status.best_price:.2f}"
        )
        # Find MOQ for best distributor
        for e in pricing_entries:
            if e.distributor == stock_status.best_distributor:
                best_deal += f" (MOQ: {e.moq})"
                break
    else:
        best_deal="Currently out of stock at all distributors"

    # Pick best image
    images = state.get("search_images", [])
    img_url = images[0] if images else None
    
    dims = datasheet.get("dimensions_mm")
    dimensions_dict = dims.model_dump() if hasattr(dims, "model_dump") else dims

    # Build the report
    cv_data = state.get("cross_validation")
    report = ComponentReport(
        component_name=state["component_query"],
        manufacturer=datasheet.get("manufacturer", "Unknown"),
        datasheet_url=datasheet.get("datasheet_url", "Not found"),
        description=datasheet.get("description", "No description available"),
        key_pins_summary=datasheet.get("key_pins", []),
        average_price=round(avg_price, 2),
        price_range=price_range,
        pricing_breakdown=pricing_entries,
        in_stock=stock_status.in_stock,
        total_available_stock=stock_status.total_stock_across_distributors,
        best_deal=best_deal,
        package_type=datasheet.get("package_type"),
        dimensions_mm=dimensions_dict,
        operating_voltage=datasheet.get("operating_voltage"),
        image_url=img_url,
        youtube_links=state.get("youtube_links", []),
        timestamp=datetime.now(),
        cross_validation=cv_data,
        agent_reasoning_trace=trace,
    )

    trace.append(
        f"[FORMATTER] Report compiled successfully. "
        f"Component: {report.component_name}, "
        f"Manufacturer: {report.manufacturer}, "
        f"Avg Price: ${report.average_price:.2f}, "
        f"In Stock: {report.in_stock}"
    )

    logger.info("[FORMATTER] Final report generated successfully")

    return {
        "final_output": report.model_dump(),
        "current_step": "formatter",
        "reasoning_trace": trace,
    }


def error_node(state: AgentState) -> dict[str, Any]:
    """
    ERROR HANDLER NODE: Produces a partial report with error details
    when retries are exhausted.
    """
    logger.warning("[ERROR] Generating partial report after exhausted retries")

    trace = state.get("reasoning_trace", [])
    errors = state.get("error_log", [])
    trace.append(
        f"[ERROR] Retries exhausted ({MAX_RETRIES}). "
        f"Generating partial report. Errors: {errors}"
    )

    # Build a partial report with whatever data we have
    datasheet = state.get("datasheet_info") or {}
    pricing_dicts = state.get("pricing_data", [])
    pricing_entries = [PricingEntry(**p) for p in pricing_dicts]

    if pricing_entries:
        prices = [e.unit_price for e in pricing_entries]
        avg_price = sum(prices) / len(prices)
        price_range = f"{min(prices):.2f} - {max(prices):.2f} (Mixed)"
    else:
        avg_price = 0.0
        price_range = "N/A"

    dims = datasheet.get("dimensions_mm")
    dimensions_dict = dims.model_dump() if hasattr(dims, "model_dump") else dims

    report = ComponentReport(
        component_name=state["component_query"],
        manufacturer=datasheet.get("manufacturer", "Unknown"),
        datasheet_url=datasheet.get("datasheet_url", "Not found"),
        description=datasheet.get(
            "description",
            f"Partial data - errors encountered: {'; '.join(errors)}",
        ),
        key_pins_summary=datasheet.get("key_pins", []),
        average_price=round(avg_price, 2),
        price_range=price_range,
        pricing_breakdown=pricing_entries,
        in_stock=False,
        total_available_stock=0,
        best_deal="Data incomplete - see error log",
        package_type=datasheet.get("package_type"),
        dimensions_mm=dimensions_dict,
        operating_voltage=datasheet.get("operating_voltage"),
        timestamp=datetime.now(),
        agent_reasoning_trace=trace,
    )

    return {
        "final_output": report.model_dump(),
        "current_step": "error_handler",
        "reasoning_trace": trace,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Conditional Edge Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def should_retry_search(state: AgentState) -> str:
    """
    After the Searcher node: decide whether to proceed or retry.
    - If search results are usable -> proceed to extractor
    - If no results and retries left -> retry search
    - If no results and retries exhausted -> go to error handler
    """
    results = state.get("search_results", [])
    retry_count = state.get("retry_count", 0)

    if results:
        logger.info("[ROUTER] Search successful, proceeding to extractor")
        return "extractor"
    elif retry_count < MAX_RETRIES:
        logger.warning(
            f"[ROUTER] No results, retrying ({retry_count + 1}/{MAX_RETRIES})"
        )
        return "retry_search"
    else:
        logger.error("[ROUTER] Search retries exhausted, going to error handler")
        return "error_handler"


def should_retry_or_finish(state: AgentState) -> str:
    """
    After the Validator node: decide if data is complete or needs retry.
    - If all critical data present -> proceed to formatter
    - If missing critical data and retries left -> retry from search
    - If retries exhausted -> go to error handler
    """
    datasheet_info = state.get("datasheet_info")
    pricing_data = state.get("pricing_data", [])
    retry_count = state.get("retry_count", 0)

    has_datasheet = datasheet_info is not None
    has_pricing = len(pricing_data) > 0

    if has_datasheet and has_pricing:
        logger.info("[ROUTER] All data complete, proceeding to formatter")
        return "formatter"
    elif retry_count < MAX_RETRIES:
        logger.warning(
            f"[ROUTER] Missing data (datasheet={has_datasheet}, "
            f"pricing={has_pricing}), retrying ({retry_count + 1}/{MAX_RETRIES})"
        )
        return "retry_search"
    else:
        # Even with incomplete data, try to format what we have
        if has_datasheet or has_pricing:
            logger.warning(
                "[ROUTER] Retries exhausted but have partial data, "
                "formatting partial report"
            )
            return "formatter"
        logger.error("[ROUTER] Retries exhausted with no data")
        return "error_handler"


def increment_retry(state: AgentState) -> dict[str, Any]:
    """Helper node to increment the retry counter before re-entering search."""
    retry_count = state.get("retry_count", 0) + 1
    trace = state.get("reasoning_trace", [])
    trace.append(
        f"[RETRY] Incrementing retry counter to {retry_count}/{MAX_RETRIES}. "
        f"Re-entering search phase..."
    )
    return {
        "retry_count": retry_count,
        "current_step": "retry",
        "reasoning_trace": trace,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Graph Construction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def build_graph() -> StateGraph:
    """
    Construct the LangGraph StateGraph for the hardware sourcing agent.

    Graph topology:
        START -> planner -> searcher --(conditional)--> extractor -> pricing -> validator
                                |                                                   |
                                |<------ retry (increment_retry) <--(conditional)---|
                                                                                    |
                                             error_handler <--(conditional)---------|
                                                  |                                 |
                                                  v                                 v
                                                 END <-------- formatter -------> END
    """
    logger.info("Building LangGraph StateGraph...")

    graph = StateGraph(AgentState)

    # ── Add nodes ──
    graph.add_node("planner", plan_node)
    graph.add_node("searcher", search_node)
    graph.add_node("extractor", extract_node)
    graph.add_node("pricing", pricing_node)
    graph.add_node("validator", validate_node)
    graph.add_node("formatter", format_node)
    graph.add_node("error_handler", error_node)
    graph.add_node("increment_retry", increment_retry)

    # ── Add edges ──
    # Linear flow: START -> planner -> searcher
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")

    # Conditional: after searcher, check if results are good
    graph.add_conditional_edges(
        "searcher",
        should_retry_search,
        {
            "extractor": "extractor",
            "retry_search": "increment_retry",
            "error_handler": "error_handler",
        },
    )

    # Linear flow: extractor -> pricing -> validator
    graph.add_edge("extractor", "pricing")
    graph.add_edge("pricing", "validator")

    # Conditional: after validator, check data completeness
    graph.add_conditional_edges(
        "validator",
        should_retry_or_finish,
        {
            "formatter": "formatter",
            "retry_search": "increment_retry",
            "error_handler": "error_handler",
        },
    )

    # Retry loop: increment_retry -> searcher
    graph.add_edge("increment_retry", "searcher")

    # Terminal edges
    graph.add_edge("formatter", END)
    graph.add_edge("error_handler", END)

    logger.info("StateGraph built successfully")
    return graph


def compile_graph():
    """Build and compile the graph into a runnable."""
    graph = build_graph()
    return graph.compile()


def run_agent(component_name: str) -> dict[str, Any]:
    """
    Run the hardware sourcing agent for a given component.

    Args:
        component_name: Electronic component name or part number.

    Returns:
        The final AgentState dict containing the ComponentReport.
    """
    logger.info(f"Starting agent for component: {component_name}")

    app = compile_graph()

    # Initialize state
    initial_state: AgentState = {
        "component_query": component_name,
        "search_plan": "",
        "search_results": [],
        "search_images": [],
        "youtube_links": [],
        "datasheet_info": None,
        "secondary_datasheet_info": None,
        "cross_validation": None,
        "pricing_data": [],
        "stock_status": None,
        "final_output": None,
        "error_log": [],
        "retry_count": 0,
        "current_step": "initializing",
        "reasoning_trace": [
            f"[INIT] Agent initialized for component: '{component_name}'"
        ],
    }

    # Run the graph
    final_state = app.invoke(initial_state)

    logger.info("Agent execution complete")
    return final_state


def get_graph_mermaid() -> str:
    """Get the Mermaid diagram representation of the graph."""
    graph = build_graph()
    app = graph.compile()
    return app.get_graph().draw_mermaid()
