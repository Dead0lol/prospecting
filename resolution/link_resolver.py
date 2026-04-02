from __future__ import annotations

from typing import Dict
from urllib.parse import urlparse

from scrapling.fetchers import Fetcher

from config.settings import settings


def detect_link_type(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "linktr.ee" in domain:
        return "linktree"
    if "beacons.ai" in domain:
        return "beacons"
    if "stan.store" in domain:
        return "stan"
    if "calendly.com" in domain:
        return "calendly"
    if domain:
        return "website"
    return "unknown"


def resolve_external_url(url: str) -> Dict[str, str]:
    if not url:
        return {"resolved_url": "", "resolved_type": "unknown"}

    try:
        response = Fetcher.get(
            url,
            headers={"User-Agent": settings.user_agent},
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )
        resolved = response.url
    except Exception:
        resolved = url

    return {"resolved_url": resolved, "resolved_type": detect_link_type(resolved)}
