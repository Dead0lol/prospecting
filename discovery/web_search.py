"""
URL classification and filtering for discovery candidates.

Separates Instagram profiles from websites, applies blocklists, and identifies
coach platform sources (Kajabi, Gumroad, Trainerize, etc. — these are ACCEPTED,
not blocked, because a coach on these platforms is a perfect ICP match for a
low-ticket digital product campaign).
"""

from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse

from config.blocklists import (
    ACCEPTED_SOURCE_DOMAINS,
    DOMAIN_BLOCKLIST,
    LINK_HUB_DOMAINS,
    is_accepted_source_domain,
    is_blocked_domain,
)


INVALID_INSTAGRAM_PATHS = {
    "",
    "/",
    "/accounts",
    "/explore",
    "/reels",
    "/stories",
    "/p",
    "/reel",
    "/tv",
    "/login",
    "/accounts",
}

ARTICLE_PATH_HINTS = {
    "/blog/",
    "/article/",
    "/news/",
    "/post/",
    "/category/",
    "/tag/",
    "/what-is",
    "/how-to",
    "/best-",
    "/top-",
    "/wiki/",
    "/review/",
}

FITNESS_HINTS = {
    "fitness",
    "coach",
    "coaching",
    "trainer",
    "personal trainer",
    "fat loss",
    "strength",
    "nutrition",
    "transformation",
    "online coaching",
    "1:1",
    "macro",
    "weight loss",
    "workout",
    "training",
    "wellness",
    "body",
    "muscle",
    "diet",
    "health",
}


def _looks_like_article(url: str, title: str) -> bool:
    path = urlparse(url).path.lower()
    title_lower = title.lower()
    if any(hint in path for hint in ARTICLE_PATH_HINTS):
        return True
    if any(
        title_lower.startswith(prefix)
        for prefix in ["what is", "how to", "top 10", "best ", "the best"]
    ):
        return True
    return False


def quick_reject_website(url: str) -> bool:
    """Return True if this URL is obviously not a real coach site."""
    domain = urlparse(url).netloc.lower().lstrip("www.")
    if domain in {
        "blogili.com",
        "wikihow.com",
        "allrecipes.com",
        "buzzfeed.com",
        "goodreads.com",
        "imdb.com",
        "tripadvisor.com",
    }:
        return True
    return urlparse(url).path.count("/") > 3


def rank_website_candidates(candidates: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Sort website candidates so the most promising ones come first."""

    def score(candidate: Dict[str, str]) -> int:
        score_value = 0
        blob = f"{candidate.get('title', '')} {candidate.get('body', '')}".lower()
        url = candidate.get("url", "").lower()
        domain = urlparse(url).netloc.lower().lstrip("www.")
        if urlparse(url).path.strip("/") == "":
            score_value += 10
        if domain and any(
            domain == hub or domain.endswith(f".{hub}") for hub in LINK_HUB_DOMAINS
        ):
            score_value += 8
        for hint in [
            "coaching",
            "1:1",
            "apply",
            "book a call",
            "free consult",
            "work with me",
        ]:
            if hint in blob:
                score_value += 5
        for hint in ["online coach", "personal trainer", "fitness coach"]:
            if hint in blob:
                score_value += 3
        for hint in ["top 10", "best ", "list of", "directory", "find a trainer"]:
            if hint in blob:
                score_value -= 10
        return score_value

    return sorted(candidates, key=score, reverse=True)


def split_candidate_urls(
    candidates: List[Dict[str, str]],
) -> Dict[str, List[Dict[str, str]]]:
    instagram: List[Dict[str, str]] = []
    websites: List[Dict[str, str]] = []

    for candidate in candidates:
        url = candidate.get("url", "")
        title = candidate.get("title", "")
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")

        if "instagram.com" in domain:
            path = parsed.path.rstrip("/")
            if path in INVALID_INSTAGRAM_PATHS or path.count("/") > 1:
                continue
            instagram.append(candidate)
            continue

        if not domain or is_blocked_domain(domain):
            continue

        # Accept link hubs, coach platforms, and directories — they'll be resolved
        # in the pipeline to find the coach's real contact/email
        if is_accepted_source_domain(domain):
            websites.append(candidate)
            continue

        if _looks_like_article(url, title):
            continue

        blob = f"{title} {candidate.get('body', '')} {url}".lower()
        if any(hint in blob for hint in FITNESS_HINTS):
            websites.append(candidate)

    return {"instagram": instagram, "websites": websites}
