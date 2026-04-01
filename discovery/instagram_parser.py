from __future__ import annotations

import re
from typing import Dict

from resolution.instagram_profile import normalize_username


_FOLLOWER_RE = re.compile(
    r"([\d,.]+)\s*([MmKk])\s*[Ff]ollower|(\d[\d,.]*)\s*[Ff]ollower"
)

_NOT_A_NAME = {
    "online",
    "fitness",
    "coach",
    "trainer",
    "personal",
    "coaching",
    "transformation",
    "nutrition",
    "strength",
    "fat loss",
    "macro",
    "weight loss",
    "health",
    "wellness",
    "body",
    "gym",
    "training",
    "certified",
    "nasm",
    "issa",
    "ace",
    "cscs",
    "content creator",
}


def parse_followers(text: str) -> int:
    match = _FOLLOWER_RE.search(text)
    if not match:
        return 0
    if match.group(1) and match.group(2):
        try:
            base = float(match.group(1).replace(",", ""))
        except ValueError:
            return 0
        multiplier = 1_000_000 if match.group(2).upper() == "M" else 1_000
        return int(base * multiplier)
    if match.group(3):
        try:
            return int(match.group(3).replace(",", ""))
        except ValueError:
            return 0
    return 0


def is_likely_name(text: str) -> bool:
    words = text.lower().split()
    if not words or len(words) > 6:
        return False
    generic_count = sum(1 for word in words if word.strip(",-.'") in _NOT_A_NAME)
    return generic_count < len(words)


def parse_ig_snippet(candidate: Dict[str, str]) -> Dict[str, str | int]:
    url = candidate.get("url", "")
    title = candidate.get("title", "")
    body = candidate.get("body", "")
    blob = f"{title} {body}"

    try:
        username = normalize_username(url)
    except ValueError:
        username = ""

    contact_name = ""
    if title:
        parts = []
        for sep in ["|", "(", " - ", "•", "·"]:
            if sep in title:
                parts = [part.strip() for part in title.split(sep)]
                break
        if not parts:
            parts = [title.strip()]

        for part in parts:
            cleaned = re.sub(r"@\S+", "", part).strip()
            if cleaned and cleaned.lower() != "instagram" and is_likely_name(cleaned):
                contact_name = cleaned
                break

    followers = parse_followers(blob)
    bio_text = body.strip()

    return {
        "instagram_url": f"https://www.instagram.com/{username}/",
        "instagram_username": username,
        "contact_name": contact_name,
        "bio_text": bio_text,
        "followers": followers,
        "business_name": contact_name or username,
    }
