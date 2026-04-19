"""
main.py - CLI entry point for the Hardware Sourcing & Specs Agent.

Usage:
    python -m src.main "ESP32-WROOM-32"
    python -m src.main "NE555" --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from src.agent import run_agent, get_graph_mermaid
from src.utils.logger import logger


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def main():
    parser = argparse.ArgumentParser(
        description="Hardware Sourcing & Specs Agent - "
        "Autonomous electronic component research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python -m src.main "ESP32-WROOM-32"\n'
            '  python -m src.main "NE555" --verbose\n'
            '  python -m src.main "STM32F103C8T6" --output report.json\n'
            "  python -m src.main --show-graph"
        ),
    )

    parser.add_argument(
        "component",
        nargs="?",
        help="Electronic component name or part number (e.g., ESP32-WROOM-32)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save JSON output to a file",
    )
    parser.add_argument(
        "--show-graph",
        action="store_true",
        help="Print the LangGraph Mermaid diagram and exit",
    )

    args = parser.parse_args()

    # Show graph mode
    if args.show_graph:
        print("\n=== LangGraph Workflow (Mermaid) ===\n")
        try:
            mermaid = get_graph_mermaid()
            print(mermaid)
        except Exception as e:
            print(f"Could not generate graph: {e}")
        return

    # Validate component argument
    if not args.component:
        parser.print_help()
        print("\nError: component name is required (unless using --show-graph)")
        sys.exit(1)

    # Configure verbose logging
    if args.verbose:
        import loguru
        logger.remove()
        logger.add(sys.stderr, level="DEBUG", colorize=True)

    component = args.component
    print(f"\n{'='*60}")
    print(f"  Hardware Sourcing & Specs Agent")
    print(f"  Component: {component}")
    print(f"{'='*60}\n")

    # Run the agent
    try:
        final_state = run_agent(component)

        report = final_state.get("final_output")

        if report:
            # Pretty print the report
            print("\n" + "="*60)
            print("  COMPONENT REPORT")
            print("="*60)
            print(f"\n  Component:  {report.get('component_name', 'N/A')}")
            print(f"  Manufacturer: {report.get('manufacturer', 'N/A')}")
            print(f"  Description:  {report.get('description', 'N/A')}")
            print(f"  Datasheet:    {report.get('datasheet_url', 'N/A')}")
            print(f"  Package:      {report.get('package_type', 'N/A')}")
            print(f"  Voltage:      {report.get('operating_voltage', 'N/A')}")

            # Key Pins
            pins = report.get("key_pins_summary", [])
            if pins:
                print(f"\n  --- Key Pins ({len(pins)}) ---")
                for p in pins:
                    pin_name = p.get("pin_name", "?") if isinstance(p, dict) else p.pin_name
                    pin_num = p.get("pin_number", "?") if isinstance(p, dict) else p.pin_number
                    func = p.get("function", "?") if isinstance(p, dict) else p.function
                    print(f"    Pin {pin_num:>4s} | {pin_name:<12s} | {func}")

            # Pricing
            print(f"\n  --- Pricing ---")
            print(f"  Average:    ${report.get('average_price', 0):.2f}")
            print(f"  Range:      {report.get('price_range', 'N/A')}")
            print(f"  Best Deal:  {report.get('best_deal', 'N/A')}")

            breakdown = report.get("pricing_breakdown", [])
            if breakdown:
                print(f"\n  {'Distributor':<25s} {'Price':>8s} {'MOQ':>6s} {'Stock':>10s}")
                print(f"  {'-'*53}")
                for entry in breakdown:
                    dist = entry.get("distributor", "?") if isinstance(entry, dict) else entry.distributor
                    price = entry.get("unit_price", 0) if isinstance(entry, dict) else entry.unit_price
                    moq = entry.get("moq", 0) if isinstance(entry, dict) else entry.moq
                    stock = entry.get("stock_quantity", 0) if isinstance(entry, dict) else entry.stock_quantity
                    print(f"  {dist:<25s} ${price:>7.2f} {moq:>6d} {stock:>10,d}")

            # Stock Status
            in_stock = report.get("in_stock", False)
            stock_label = "IN STOCK" if in_stock else "OUT OF STOCK"
            total_stock = report.get("total_available_stock", 0)
            print(f"\n  Stock:      {stock_label} (Total: {total_stock:,d} units)")

            print(f"\n{'='*60}")

            # Reasoning trace
            trace = report.get("agent_reasoning_trace", [])
            if trace:
                print(f"\n  --- Agent Reasoning Trace ({len(trace)} steps) ---")
                for i, step in enumerate(trace, 1):
                    print(f"  {i:2d}. {step}")
                print()

            # Save to file if requested
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, cls=DateTimeEncoder)
                print(f"  Report saved to: {args.output}")

            # Also print raw JSON
            print("\n  --- Raw JSON Output ---")
            print(json.dumps(report, indent=2, cls=DateTimeEncoder))

        else:
            print("\n  ERROR: Agent did not produce a report.")
            errors = final_state.get("error_log", [])
            if errors:
                print("  Errors:")
                for e in errors:
                    print(f"    - {e}")

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        print(f"\n  FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
