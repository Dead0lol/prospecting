from __future__ import annotations

import time
from typing import List


def _log(message: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] [email_guesser] {message}", flush=True)


# Words that are NOT real person names — they're titles, roles, or generic words
_GENERIC_WORDS = {
    "online", "fitness", "coach", "trainer", "personal", "coaching",
    "transformation", "nutrition", "strength", "fat", "loss", "macro",
    "weight", "health", "wellness", "body", "gym", "training",
    "certified", "nasm", "issa", "ace", "cscs", "content", "creator",
    "remote", "virtual", "home", "best", "top", "the", "and",
    "new", "york", "city", "nyc", "los", "angeles", "chicago",
    "houston", "phoenix", "dallas", "austin", "san", "diego",
    "antonio", "philadelphia", "eat", "liberty",
}


def _extract_real_name(contact_name: str) -> tuple[str, str]:
    """Extract first/last name from contact_name, filtering out generic words.
    Returns (first, last) or ("", "") if no real name found.
    """
    parts = [p.lower() for p in contact_name.replace("-", " ").split() if p.isalpha()]
    real_parts = [p for p in parts if p not in _GENERIC_WORDS and len(p) > 1]
    if not real_parts:
        return ("", "")
    first = real_parts[0]
    last = real_parts[-1] if len(real_parts) > 1 else ""
    return (first, last)


def guess_emails(contact_name: str, domain: str) -> List[str]:
    """Generate likely email patterns without doing SMTP checks inline."""
    if not domain:
        return []

    first, last = _extract_real_name(contact_name) if contact_name else ("", "")

    # Build guess list: name-based first, then generic
    guesses: List[str] = []
    if first:
        guesses.append(f"{first}@{domain}")
        if last and last != first:
            guesses.append(f"{first}.{last}@{domain}")
            guesses.append(f"{first}{last}@{domain}")

    # Always include generic patterns — these are the most common for solo coaches
    guesses.append(f"hello@{domain}")
    guesses.append(f"info@{domain}")
    guesses.append(f"contact@{domain}")

    # Dedupe while preserving order
    seen: set[str] = set()
    unique_guesses: List[str] = []
    for g in guesses:
        if g not in seen:
            seen.add(g)
            unique_guesses.append(g)

    for guess in unique_guesses[:3]:
        _log(f"candidate {guess}")

    return unique_guesses[:3]
