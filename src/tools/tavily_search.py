"""
tavily_search.py - Web search tool powered by Tavily API.

Performs optimized searches for electronic component datasheets
and specifications using Tavily's AI-optimized search engine.
"""

from __future__ import annotations

import os
from typing import Any, Literal

from dotenv import load_dotenv

from src.utils.logger import logger

load_dotenv()


def search_component(
    query: str,
    search_type: Literal["datasheet", "general", "youtube"] = "general",
    max_results: int = 5,
) -> dict[str, Any]:
    """
    Search for electronic component information using Tavily.

    Args:
        query: Component name or part number (e.g., "ESP32-WROOM-32").
        search_type: Type of search - "datasheet" for PDF datasheets,
                     "general" for specs and manufacturer info.
        max_results: Maximum number of results to return.

    Returns:
        List of search result dicts with keys: title, url, content, score.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.error("TAVILY_API_KEY not found in environment variables")
        raise ValueError(
            "TAVILY_API_KEY is required. Get one free at https://tavily.com"
        )

    # Build optimized search queries based on technical requirements
    # We include major technical sites to ensure official datasheets are prioritized
    if search_type == "datasheet":
        search_query = (
            f"'{query}' datasheet PDF "
            f"site:mouser.com OR site:datasheetlib.com OR site:alldatasheet.com "
            f"OR site:digikey.com OR site:st.com OR site:ti.com OR site:analog.com"
        )
    elif search_type == "youtube":
        search_query = f"{query} tutorial video"
    else:
        search_query = (
            f"'{query}' electronic component clear hardware pinout diagram "
            f"features operating voltage datasheet"
        )

    logger.info(f"Tavily search [{search_type}]: {search_query}")

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)

        response = client.search(
            query=search_query,
            max_results=max_results,
            include_answer=True,
            include_images=True,
            search_depth="advanced",
        )

        results = []

        # Include the AI-synthesized answer as the first result
        if response.get("answer"):
            results.append(
                {
                    "title": f"AI Summary: {query}",
                    "url": "tavily-ai-answer",
                    "content": response["answer"],
                    "score": 1.0,
                }
            )

        # Add individual search results
        for r in response.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0.0),
                }
            )

        logger.info(f"Tavily returned {len(results)} results and {len(response.get('images', []))} images")
        return {
            "results": results,
            "images": response.get("images", [])
        }

    except ImportError:
        logger.error("tavily-python package not installed")
        raise ImportError(
            "Please install tavily-python: pip install tavily-python"
        )
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        raise
