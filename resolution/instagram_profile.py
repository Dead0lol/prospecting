from __future__ import annotations

import re
import time
from functools import lru_cache
from typing import Dict

import instaloader

from config.settings import settings


INSTAGRAM_RE = re.compile(r"instagram\.com/([A-Za-z0-9_.]+)")


@lru_cache(maxsize=1)
def get_loader() -> instaloader.Instaloader:
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        save_metadata=False,
        quiet=True,
    )
    if settings.ig_username and settings.ig_password:
        try:
            loader.login(settings.ig_username, settings.ig_password)
        except Exception:
            pass  # continue without login, lower rate limits
    return loader


def normalize_username(instagram_url_or_username: str) -> str:
    if instagram_url_or_username.startswith("http"):
        match = INSTAGRAM_RE.search(instagram_url_or_username)
        if not match:
            raise ValueError(f"Could not parse username from {instagram_url_or_username}")
        username = match.group(1).strip("/")
        # Filter out non-profile paths that slipped through
        if username.lower() in {"p", "reel", "reels", "explore", "stories", "accounts", "tv", "s"}:
            raise ValueError(f"Not a profile URL: {instagram_url_or_username}")
        return username
    return instagram_url_or_username.strip().lstrip("@").strip("/")


def fetch_profile(instagram_url_or_username: str) -> Dict[str, object]:
    username = normalize_username(instagram_url_or_username)
    loader = get_loader()
    profile = instaloader.Profile.from_username(loader.context, username)
    time.sleep(settings.instagram_delay_seconds)
    return {
        "instagram_url": f"https://www.instagram.com/{profile.username}/",
        "instagram_username": profile.username,
        "contact_name": profile.full_name or "",
        "bio_text": profile.biography or "",
        "followers": profile.followers or 0,
        "business_category": profile.business_category_name or "",
        "business_name": profile.full_name or profile.username,
        "source_confidence": "high",
        "external_url": profile.external_url or "",
        "is_business": profile.is_business_account,
    }
