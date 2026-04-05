"""
Individual query search module for single coach/website lookups.

Uses DuckDuckGo with enhanced retry logic for reliable individual queries.
Bulk discovery uses duckduckgo_search.py; this module is for one-off lookups
where reliability matters more than throughput.
"""

from __future__ import annotations

import time
from typing import Dict, List

from config.settings import settings
from discovery.duckduckgo_search import search_query
from logging_utils import get_logger


logger = get_logger("individual_search")


def search_individual_query(
    query: str, max_results: int | None = None
) -> List[Dict[str, str]]:
    """Search for a specific coach/site lookup with enhanced reliability.

    Uses DuckDuckGo with retry logic optimized for single queries.
    This path is for one-off lookups (e.g., finding a coach's website
    from their Instagram handle).
    """
    max_results = max_results or min(10, settings.max_search_results_per_query)

    # First attempt with standard search
    hits = search_query(query, max_results=max_results)
    if hits:
        logger.info(f"individual search returned {len(hits)} hits")
        return hits

    # If no results, try with slightly modified query (add quotes if missing)
    if '"' not in query:
        quoted_query = f'"{query}"'
        logger.info(f"retrying with quoted query: {quoted_query[:60]}")
        time.sleep(1)  # Brief pause before retry
        hits = search_query(quoted_query, max_results=max_results)
        if hits:
            # Restore original query in results for consistency
            for hit in hits:
                hit["query"] = query
            logger.info(f"quoted retry returned {len(hits)} hits")
            return hits

    logger.info(f"individual search found no results for: {query[:60]}")
    return []
