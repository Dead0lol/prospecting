"""Disify API client for domain-level email validation.

Free API (1000 requests/day, no signup required) that checks:
- Email format validity
- Domain has MX records
- Disposable email domain detection
- Role account detection (info@, admin@, etc.)
- Free email provider detection

Does NOT verify mailbox existence - use SMTP for that.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import requests

from config.settings import settings
from logging_utils import get_logger


logger = get_logger("disify")

_CACHE_DIR = settings.output_cache_dir / "disify"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DISIFY_API_URL = "https://disify.com/api/email"
DISIFY_TIMEOUT = 10


@dataclass
class DisifyResult:
    """Result from Disify API validation."""

    email: str
    format_valid: bool
    dns_valid: bool
    is_disposable: bool
    is_role_account: bool
    is_free_provider: bool
    mx_records: list[str]
    domain: str

    @property
    def is_deliverable_domain(self) -> bool:
        """Domain-level check: format OK, DNS OK, not disposable."""
        return self.format_valid and self.dns_valid and not self.is_disposable

    def to_dict(self) -> Dict:
        return {
            "email": self.email,
            "format_valid": self.format_valid,
            "dns_valid": self.dns_valid,
            "is_disposable": self.is_disposable,
            "is_role_account": self.is_role_account,
            "is_free_provider": self.is_free_provider,
            "mx_records": self.mx_records,
            "domain": self.domain,
        }


def _cache_path(email: str) -> Path:
    h = hashlib.sha256(email.lower().encode()).hexdigest()
    return _CACHE_DIR / f"{h}.json"


def _get_cached(email: str) -> Optional[DisifyResult]:
    path = _cache_path(email)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return DisifyResult(
            email=data["email"],
            format_valid=data["format_valid"],
            dns_valid=data["dns_valid"],
            is_disposable=data["is_disposable"],
            is_role_account=data["is_role_account"],
            is_free_provider=data["is_free_provider"],
            mx_records=data.get("mx_records", []),
            domain=data.get("domain", ""),
        )
    except Exception:
        return None


def _set_cached(result: DisifyResult) -> None:
    try:
        _cache_path(result.email).write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def validate_email_domain(email: str) -> DisifyResult:
    """Validate email domain via Disify API.

    Returns cached result if available, otherwise calls API.
    Handles API errors gracefully with sensible defaults.
    """
    email = email.lower().strip()

    # Check cache first
    cached = _get_cached(email)
    if cached is not None:
        logger.info(
            f"cached: {email} -> deliverable_domain={cached.is_deliverable_domain}"
        )
        return cached

    # Call Disify API
    try:
        resp = requests.get(
            f"{DISIFY_API_URL}/{email}",
            timeout=DISIFY_TIMEOUT,
            headers={"User-Agent": settings.user_agent},
        )
        resp.raise_for_status()
        data = resp.json()

        result = DisifyResult(
            email=email,
            format_valid=data.get("format", False),
            dns_valid=data.get("dns", False),
            is_disposable=data.get("disposable", False),
            is_role_account=data.get("role", False),
            is_free_provider=data.get("free", False),
            mx_records=data.get("mx_info", []),
            domain=data.get("domain", email.split("@")[-1] if "@" in email else ""),
        )
        logger.info(
            f"disify: {email} -> format={result.format_valid} dns={result.dns_valid} "
            f"disposable={result.is_disposable}"
        )
    except Exception as exc:
        # On error, assume valid format and unknown domain status
        logger.warning(f"disify error for {email}: {exc}")
        domain = email.split("@")[-1] if "@" in email else ""
        result = DisifyResult(
            email=email,
            format_valid="@" in email and "." in email.split("@")[-1],
            dns_valid=True,  # Assume true, let SMTP verify
            is_disposable=False,
            is_role_account=False,
            is_free_provider=False,
            mx_records=[],
            domain=domain,
        )

    _set_cached(result)
    return result


def validate_emails_batch(emails: list[str]) -> Dict[str, DisifyResult]:
    """Validate multiple emails (sequential, respects rate limits).

    Disify doesn't have a batch endpoint, so we call one by one.
    Results are cached, so repeated calls are fast.
    """
    results = {}
    for email in emails:
        results[email] = validate_email_domain(email)
    return results
