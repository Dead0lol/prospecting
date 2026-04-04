from __future__ import annotations

import re
from typing import Iterable, List


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HEX_TOKEN_RE = re.compile(r"^[a-f0-9]{16,}$")
BAD_EMAIL_DOMAIN_HINTS = {
    "sentry.io",
    "wixpress.com",
}
BAD_EMAIL_PREFIXES = {
    "example",
    "test",
    "noreply",
    "no-reply",
    "mailer-daemon",
    "wordpress",
    "wp",
    "root",
}
BAD_EMAIL_SUBSTRINGS = {
    "admin@localhost",
    "email@example",
    ".png@",
    ".jpg@",
    ".gif@",
    ".svg@",
}


def _is_likely_contact_email(email: str) -> bool:
    candidate = (email or "").strip().lower()
    if "@" not in candidate:
        return False

    local_part, domain = candidate.rsplit("@", 1)
    if not local_part or not domain:
        return False

    if any(candidate.endswith(f"@{bad_domain}") or domain.endswith(f".{bad_domain}") for bad_domain in BAD_EMAIL_DOMAIN_HINTS):
        return False

    if local_part in BAD_EMAIL_PREFIXES:
        return False

    if any(bad in candidate for bad in BAD_EMAIL_SUBSTRINGS):
        return False

    # Drop vendor telemetry addresses like Wix/Sentry UUID-ish mailboxes.
    if HEX_TOKEN_RE.fullmatch(local_part):
        return False

    return True


def extract_emails(text: str) -> List[str]:
    emails = {
        match.group(0).lower()
        for match in EMAIL_RE.finditer(text or "")
        if _is_likely_contact_email(match.group(0))
    }
    return sorted(emails)


def pick_best_email(emails: Iterable[str], domain: str = "") -> str:
    priority_prefixes = [
        "info",
        "hello",
        "contact",
        "admin",
        "coach",
        "support",
        "team",
    ]
    filtered = [email for email in emails if _is_likely_contact_email(email)]

    if not filtered:
        return ""

    if domain:
        domain_matches = [email for email in filtered if email.endswith(f"@{domain}")]
        if domain_matches:
            filtered = domain_matches

    for prefix in priority_prefixes:
        for email in filtered:
            if email.startswith(f"{prefix}@"):
                return email

    return filtered[0]
