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


INVALID_INSTAGRAM_PATHS = {
    "", "/", "/accounts", "/explore", "/reels",
    "/stories", "/p", "/reel", "/tv", "/login", "/accounts",
}

DOMAIN_BLOCKLIST = {
    # Social media (not useful for lead data)
    "reddit.com", "quora.com", "zhihu.com", "wikipedia.org",
    "youtube.com", "tiktok.com", "facebook.com", "twitter.com", "x.com",
    "pinterest.com", "linkedin.com", "medium.com", "substack.com",
    "amazon.com", "ebay.com", "etsy.com",
    # Review / directory sites
    "yelp.com", "bbb.org", "glassdoor.com",
    # News and media
    "nytimes.com", "forbes.com", "businessinsider.com", "huffpost.com",
    "healthline.com", "webmd.com", "mayoclinic.org",
    # Job boards
    "indeed.com", "ziprecruiter.com",
    # Viral/content media
    "buzzfeed.com", "buzzfeednews.com",
    # Franchise / chain gyms
    "anytimefitness.com", "snapfitness.com", "planetfitness.com",
    "orangetheory.com", "24hourfitness.com", "equinox.com",
    "goldsgym.com", "lafitness.com", "crunchfitness.com",
    # Payment / money apps
    "cash.app", "venmo.com", "paypal.com", "paypal.me",
    # Aggregators / platforms (coach pages on these are subdirectories with no email)
    "playbookapp.io", "my.playbookapp.io", "trainiac.com",
    "future.co", "thumbtack.com", "bark.com", "optimocoach.com",
    "msha.ke", "everfit.io", "myfit.app", "coachhub.io",
    # Fitness media sites
    "garagegymreviews.com", "menshealth.com", "womenshealthmag.com",
    "self.com", "shape.com", "bodybuilding.com", "muscleandstrength.com",
    "t-nation.com", "nasm.org", "acefitness.org", "precisionnutrition.com",
}

# Coach link hub domains — ACCEPTED (will be resolved to real site)
LINK_HUB_DOMAINS = {
    "linktr.ee", "beacons.ai", "stan.store",
    "linkpop.com", "koji.io",
}

# Coach platform domains — ACCEPTED (proven digital sellers)
COACH_PLATFORM_DOMAINS = {
    "kajabi.com",
    "gumroad.com",
    "thinkific.com",
    "teachable.com",
    "trainerize.com",
    "caliber.com",
}

# Coach directory domains — ACCEPTED (structured profiles)
COACH_DIRECTORY_DOMAINS = {
    "getmisfit.com",
    "coachcaller.com",
    "yogaia.com",
    "fitnessnetwork.com",
}

ACCEPTED_SOURCE_DOMAINS = (
    LINK_HUB_DOMAINS | COACH_PLATFORM_DOMAINS | COACH_DIRECTORY_DOMAINS
)

ARTICLE_PATH_HINTS = {
    "/blog/", "/article/", "/news/", "/post/", "/category/",
    "/tag/", "/what-is", "/how-to", "/best-", "/top-",
    "/wiki/", "/review/",
}

FITNESS_HINTS = {
    "fitness", "coach", "coaching", "trainer", "personal trainer",
    "fat loss", "strength", "nutrition", "transformation",
    "online coaching", "1:1", "macro", "weight loss", "workout",
    "training", "wellness", "body", "muscle", "diet", "health",
}


def _is_blocked_domain(domain: str) -> bool:
    if not domain:
        return True
    for blocked in DOMAIN_BLOCKLIST:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True
    return False


def _is_accepted_source(domain: str) -> bool:
    if not domain:
        return False
    for accepted in ACCEPTED_SOURCE_DOMAINS:
        if domain == accepted or domain.endswith(f".{accepted}"):
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
            continue

        if not domain or _is_blocked_domain(domain):
            continue

        # Accept link hubs, coach platforms, and directories — they'll be resolved
        # in the pipeline to find the coach's real contact/email
        if _is_accepted_source(domain):
            websites.append(candidate)
            continue

        if _looks_like_article(url, title):
            continue

        blob = f"{title} {candidate.get('body', '')} {url}".lower()
        if any(hint in blob for hint in FITNESS_HINTS):
            websites.append(candidate)

    return {"instagram": instagram, "websites": websites}
