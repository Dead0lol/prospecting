from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse


INVALID_INSTAGRAM_PATHS = {"", "/", "/accounts", "/explore", "/reels", "/stories", "/p", "/reel", "/tv"}

# Domains that are never a real coach's site
DOMAIN_BLOCKLIST = {
    "reddit.com", "quora.com", "zhihu.com", "wikipedia.org",
    "youtube.com", "tiktok.com", "facebook.com", "twitter.com", "x.com",
    "pinterest.com", "linkedin.com", "medium.com", "substack.com",
    "amazon.com", "ebay.com", "etsy.com",
    "yelp.com", "bbb.org", "glassdoor.com",
    "nytimes.com", "forbes.com", "businessinsider.com", "huffpost.com",
    "healthline.com", "webmd.com", "mayoclinic.org",
    "indeed.com", "ziprecruiter.com",
    "buzzfeed.com", "buzzfeednews.com",
    # SaaS / platforms / aggregators
    "trainerize.com", "trainerize.me", "everfit.io", "playbookapp.io",
    "my.playbookapp.io", "trainiac.com", "future.co", "caliber.com",
    "thumbtack.com", "bark.com", "optimocoach.com", "msha.ke",
    # Fitness media (not individual coaches)
    "garagegymreviews.com", "menshealth.com", "womenshealthmag.com",
    "self.com", "shape.com", "bodybuilding.com", "muscleandstrength.com",
    "t-nation.com", "nasm.org", "acefitness.org", "precisionnutrition.com",
    # Franchise / chain gyms
    "anytimefitness.com", "snapfitness.com", "planetfitness.com",
    "orangetheory.com", "24hourfitness.com", "equinox.com",
    "goldsgym.com", "lafitness.com", "crunchfitness.com",
    # Payment platforms
    "cash.app", "venmo.com", "paypal.com", "paypal.me",
}

# URL path patterns that indicate articles, not coach sites
ARTICLE_PATH_HINTS = {
    "/blog/", "/article/", "/news/", "/post/", "/category/",
    "/tag/", "/what-is", "/how-to", "/best-", "/top-",
    "/wiki/", "/review/",
}

FITNESS_HINTS = {
    "fitness", "coach", "coaching", "trainer", "personal trainer",
    "fat loss", "strength", "nutrition", "transformation",
    "online coaching", "1:1", "macro", "weight loss",
}

LINK_HUB_DOMAINS = {"linktr.ee", "beacons.ai", "stan.store"}


def _is_blocked_domain(domain: str) -> bool:
    for blocked in DOMAIN_BLOCKLIST:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True
    return False


def _looks_like_article(url: str, title: str) -> bool:
    path = urlparse(url).path.lower()
    title_lower = title.lower()
    if any(hint in path for hint in ARTICLE_PATH_HINTS):
        return True
    if any(title_lower.startswith(prefix) for prefix in ["what is", "how to", "top 10", "best ", "the best"]):
        return True
    return False


def split_candidate_urls(candidates: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
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
        elif domain and not _is_blocked_domain(domain):
            if any(domain == hub or domain.endswith(f".{hub}") for hub in LINK_HUB_DOMAINS):
                websites.append(candidate)
                continue
            if _looks_like_article(url, title):
                continue
            blob = f"{title} {candidate.get('body', '')} {url}".lower()
            if any(hint in blob for hint in FITNESS_HINTS):
                websites.append(candidate)

    return {"instagram": instagram, "websites": websites}
