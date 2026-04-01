from __future__ import annotations

from typing import List

from logging_utils import get_logger


logger = get_logger("email_guesser")


# Words that are NOT real person names — they're titles, roles, or generic words
_GENERIC_WORDS = {
    "online",
    "fitness",
    "coach",
    "trainer",
    "personal",
    "coaching",
    "transformation",
    "nutrition",
    "strength",
    "fat",
    "loss",
    "macro",
    "weight",
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
    "content",
    "creator",
    "remote",
    "virtual",
    "home",
    "best",
    "top",
    "the",
    "and",
    "new",
    "york",
    "city",
    "nyc",
    "los",
    "angeles",
    "chicago",
    "houston",
    "phoenix",
    "dallas",
    "austin",
    "san",
    "diego",
    "antonio",
    "philadelphia",
    "eat",
    "liberty",
    # Common words that appear in business names but aren't names
    "losing",
    "gaining",
    "getting",
    "getting",
    "training",
    "results",
    "lifestyle",
    "performance",
    "focused",
    "driven",
    "elite",
    "pro",
    "life",
    "mindset",
    "journey",
    "results",
    "achieving",
    "building",
    "becoming",
    "living",
    "moving",
    "feeling",
    "looking",
    "strong",
    "better",
    "fitter",
    "leaner",
    "healthier",
    "happier",
    "with",
    "your",
    "my",
    "our",
    "free",
    "start",
    "join",
    "apply",
    "book",
    "schedule",
    "today",
    "now",
    "get",
    "take",
    "the",
    "method",
    "system",
    "program",
    "plan",
    "academy",
    "studio",
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

    # Build guess list: generic first (most reliable), then name-based
    guesses: List[str] = []

    # Always include generic patterns — these are the most common for solo coaches
    guesses.append(f"hello@{domain}")
    guesses.append(f"info@{domain}")
    guesses.append(f"contact@{domain}")

    if first and len(first) >= 2 and first.isalpha():
        guesses.append(f"{first}@{domain}")
        if last and last != first and len(last) >= 2 and last.isalpha():
            guesses.append(f"{first}.{last}@{domain}")
            guesses.append(f"{first}{last}@{domain}")

    # Dedupe while preserving order
    seen: set[str] = set()
    unique_guesses: List[str] = []
    for g in guesses:
        if g not in seen:
            seen.add(g)
            unique_guesses.append(g)

    for guess in unique_guesses[:3]:
        logger.info(f"candidate {guess}")

    return unique_guesses[:3]
