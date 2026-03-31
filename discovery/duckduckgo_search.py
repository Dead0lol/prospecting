"""
DuckDuckGo search module for fitness coach prospecting.

Uses the `ddgs` library (ddgstealth). All queries are keyword-based — geography is
irrelevant since the ICP is any English-speaking fitness coach globally.

Query rotation: Each run picks up where the last run left off, so different
keyword subsets are searched each time. The full query pool is large enough that
it takes many runs to exhaust it.
"""

from __future__ import annotations

import re
import time
from typing import Dict, Iterable, List

from ddgs import DDGS

from config.settings import settings


def _log(message: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] [discovery] {message}", flush=True)


def _search_ddgs_once(query: str, max_results: int, region: str, safesearch: str) -> List[Dict[str, str]]:
    hits: List[Dict[str, str]] = []
    with DDGS(timeout=settings.ddgs_timeout_seconds) as ddgs:
        for result in ddgs.text(
            query,
            max_results=max_results,
            backend="html",
            region=region,
            safesearch=safesearch,
        ):
            href = result.get("href") or result.get("url") or ""
            title = result.get("title") or ""
            body = result.get("body") or ""
            if not href:
                continue
            hits.append({"query": query, "url": href, "title": title, "body": body})
    return hits


def _query_variants(query: str) -> List[str]:
    """Generate alternate query forms for the same intent. DDG is inconsistent
    across region/safesearch combos, so we try the query as-is and a collapsed version."""
    variants = [query]
    if "site:instagram.com" not in query:
        return variants

    base = query.replace("site:instagram.com", "").strip()
    unquoted = re.sub(r'"', "", base)
    collapsed = re.sub(r"\s+", " ", unquoted).strip()

    for variant in [
        f"site:instagram.com {collapsed}",
        f"{collapsed} site:instagram.com",
    ]:
        if variant and variant not in variants:
            variants.append(variant)
    return variants


def build_queries(
    keywords: Iterable[str],
    modifiers: Iterable[str],
    platforms: Iterable[str] | None = None,
) -> List[str]:
    """Build a flat, diversified query list from keywords and modifiers.

    No city/geo logic. Each keyword gets interleaved with modifiers so early
    query cuts still give broad coverage. Platforms are searched directly too.
    """
    kw_list = list(keywords)
    mod_list = list(modifiers)
    plat_list = list(platforms) if platforms else []
    queries: List[str] = []

    # Primary: keyword alone (widest net)
    for kw in kw_list:
        queries.append(f'"{kw}"')

    # Secondary: keyword + modifier (action/intent signals)
    for kw in kw_list:
        for mod in mod_list:
            queries.append(f'"{kw}" "{mod}"')

    # Instagram: keyword alone (profile discovery)
    for kw in kw_list:
        queries.append(f'"{kw}" site:instagram.com')

    # Instagram: keyword + modifier
    for kw in kw_list:
        for mod in mod_list[:5]:  # Top 5 modifiers only for IG
            queries.append(f'"{kw}" "{mod}" site:instagram.com')

    # Platform: keyword + platform domain (coach marketplace discovery)
    for kw in kw_list:
        for plat in plat_list:
            queries.append(f'"{kw}" site:{plat}')

    return queries


def search_query(query: str, max_results: int | None = None) -> List[Dict[str, str]]:
    """Execute a single query with automatic retry across region/safesearch combos."""
    max_results = max_results or settings.max_search_results_per_query
    _log(f"searching: {query[:80]}")
    attempts = []
    for variant in _query_variants(query):
        attempts.extend([
            (variant, "us-en", "off"),
            (variant, "wt-wt", "off"),
        ])

    hits: List[Dict[str, str]] = []
    seen_urls: set[str] = set()
    last_error = ""
    for index, (variant, region, safesearch) in enumerate(attempts, start=1):
        try:
            if index > 1:
                _log(f"retry {index - 1}: {variant[:80]} region={region} safesearch={safesearch}")
            batch = _search_ddgs_once(variant, max_results, region, safesearch)
            for hit in batch:
                if hit["url"] in seen_urls:
                    continue
                seen_urls.add(hit["url"])
                hit["query"] = query
                hits.append(hit)
            if hits:
                break
        except Exception as exc:
            last_error = str(exc)
            _log(f"search error: {exc}")

    if not hits and last_error:
        _log(f"all retries failed for query: {query[:80]}")
    _log(f"got {len(hits)} hits")
    time.sleep(settings.discovery_delay_seconds)
    return hits


def discover_candidates(queries: Iterable[str], target: int = 200) -> List[Dict[str, str]]:
    """Run queries until we reach target candidate count or exhaust queries."""
    seen: set[str] = set()
    candidates: List[Dict[str, str]] = []

    query_list = list(queries)[: settings.max_discovery_queries]
    _log(f"running up to {len(query_list)} queries (target {target} candidates)")

    queries_run = 0
    for index, query in enumerate(query_list, start=1):
        queries_run = index
        _log(f"query {index}/{len(query_list)} (pool={len(candidates)})")
        results = search_query(query)

        for result in results:
            url = result["url"]
            if url not in seen:
                seen.add(url)
                candidates.append(result)

        if len(candidates) >= target:
            _log(f"reached target of {target} candidates, stopping discovery early")
            break

    _log(f"discovery done: {len(candidates)} unique candidates from {queries_run} queries")
    return candidates
