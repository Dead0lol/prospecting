from __future__ import annotations

import re
from typing import Iterable, List


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_emails(text: str) -> List[str]:
    emails = {match.group(0).lower() for match in EMAIL_RE.finditer(text or "")}
    return sorted(emails)


def pick_best_email(emails: Iterable[str], domain: str = "") -> str:
    priority_prefixes = ["hello", "contact", "info", "coach", "admin"]
    filtered = [email for email in emails if email]
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
