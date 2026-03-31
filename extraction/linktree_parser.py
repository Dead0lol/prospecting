from __future__ import annotations

from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config.settings import settings


def parse_link_hub(url: str) -> Dict[str, object]:
    response = requests.get(url, headers={"User-Agent": settings.user_agent}, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links: List[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith("/"):
            href = urljoin(url, href)
        if href.startswith("http") or href.startswith("mailto:"):
            links.append(href)

    text = " ".join(soup.stripped_strings)
    return {"text": text, "links": sorted(set(links))}
