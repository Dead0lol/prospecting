from __future__ import annotations

import re


INSTAGRAM_RE = re.compile(r"instagram\.com/([A-Za-z0-9_.]+)")


def normalize_username(instagram_url_or_username: str) -> str:
    if instagram_url_or_username.startswith("http"):
        match = INSTAGRAM_RE.search(instagram_url_or_username)
        if not match:
            raise ValueError(
                f"Could not parse username from {instagram_url_or_username}"
            )
        username = match.group(1).strip("/")
        # Filter out non-profile paths that slipped through
        if username.lower() in {
            "p",
            "reel",
            "reels",
            "explore",
            "stories",
            "accounts",
            "tv",
            "s",
        }:
            raise ValueError(f"Not a profile URL: {instagram_url_or_username}")
        return username
    return instagram_url_or_username.strip().lstrip("@").strip("/")
