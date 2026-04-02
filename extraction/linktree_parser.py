from __future__ import annotations

from typing import Dict, List
from urllib.parse import urljoin

from scrapling.fetchers import Fetcher

from config.settings import settings


def parse_link_hub(url: str) -> Dict[str, object]:
    response = Fetcher.get(
        url,
        headers={"User-Agent": settings.user_agent},
        timeout=settings.request_timeout_seconds,
    )
    if response.status >= 400:
        reason = getattr(response, "reason", "")
        if reason:
            raise RuntimeError(f"HTTP {response.status} {reason} for {url}")
        raise RuntimeError(f"HTTP {response.status} for {url}")

    links: List[str] = []
    for anchor in response.css("a[href]"):
        href = anchor.attrib.get("href", "").strip()
        if not href:
            continue
        if href.startswith("/"):
            href = urljoin(url, href)
        if href.startswith("http") or href.startswith("mailto:"):
            links.append(href)

    text = " ".join(chunk.strip() for chunk in response.css("::text").getall() if chunk.strip())
    return {"text": text, "links": sorted(set(links))}
