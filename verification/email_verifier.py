"""Unified email verification using Disify (domain) + SMTP (mailbox).

Verification flow:
1. Disify API checks: format, MX records, disposable domain, role account
2. If domain is invalid/disposable, skip SMTP (saves time and connections)
3. SMTP probe attempts mailbox verification (best effort)

Final statuses:
- valid: SMTP confirmed mailbox exists
- invalid: Domain invalid OR SMTP rejected
- catch-all: Domain accepts all addresses (can't verify individual mailbox)
- risky: Domain OK but SMTP inconclusive (timeout, blocked, etc.)
- disposable: Disposable email domain detected
- missing: No email provided
"""

from __future__ import annotations

import hashlib
import json
import random
import smtplib
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dns.resolver

from config.settings import settings
from logging_utils import get_logger
from verification.disify_client import DisifyResult, validate_email_domain


logger = get_logger("email_verifier")

_CACHE_DIR = settings.output_cache_dir / "email_verification"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_catch_all_domains: Dict[str, bool] = {}
_CATCH_ALL_CACHE_PATH = _CACHE_DIR / "catch_all_domains.json"

SMTP_CONNECT_TIMEOUT = 5
SMTP_MAX_WORKERS = 5


@dataclass
class VerificationResult:
    """Full verification result combining Disify + SMTP."""

    email: str
    status: str  # valid, invalid, catch-all, risky, disposable, missing
    disify: Optional[DisifyResult] = None
    smtp_code: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "email": self.email,
            "status": self.status,
            "smtp_code": self.smtp_code,
            "error": self.error,
            "disify": self.disify.to_dict() if self.disify else None,
        }


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def _cache_path(email: str) -> Path:
    h = hashlib.sha256(email.lower().encode()).hexdigest()
    return _CACHE_DIR / f"{h}.json"


def _get_cached(email: str) -> Optional[str]:
    """Get cached status string (for backward compatibility)."""
    path = _cache_path(email)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("status")
        except Exception:
            pass
    return None


def _set_cached(email: str, status: str, smtp_code: Optional[int] = None) -> None:
    try:
        payload = {"email": email, "status": status}
        if smtp_code is not None:
            payload["smtp_code"] = smtp_code
        _cache_path(email).write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass


def _load_catch_all_cache() -> Dict[str, bool]:
    if not _CATCH_ALL_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(_CATCH_ALL_CACHE_PATH.read_text(encoding="utf-8"))
        return {str(domain): bool(value) for domain, value in data.items()}
    except Exception:
        return {}


def _persist_catch_all_cache() -> None:
    try:
        _CATCH_ALL_CACHE_PATH.write_text(
            json.dumps(_catch_all_domains, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# SMTP helpers
# ---------------------------------------------------------------------------


def _smtp_probe_identity() -> Tuple[str, str]:
    helo = settings.smtp_probe_helo_name or "mail.example.com"
    mail_from = settings.smtp_probe_mail_from or "verify@example.com"
    return helo, mail_from


def _mx_host(domain: str) -> str:
    """Get primary MX host for domain."""
    records = dns.resolver.resolve(domain, "MX", lifetime=5)
    sorted_records = sorted(records, key=lambda item: item.preference)
    return str(sorted_records[0].exchange).rstrip(".")


def _smtp_check(email: str, mx: str) -> int:
    """Perform SMTP RCPT TO check. Returns SMTP response code."""
    server = smtplib.SMTP(timeout=SMTP_CONNECT_TIMEOUT)
    try:
        helo_name, mail_from = _smtp_probe_identity()
        server.connect(mx)
        server.helo(helo_name)
        server.mail(mail_from)
        code, _ = server.rcpt(email)
        return int(code)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def _is_catch_all_domain(domain: str, mx: str) -> bool:
    """Check if domain accepts all addresses (catch-all)."""
    if not _catch_all_domains:
        _catch_all_domains.update(_load_catch_all_cache())

    if domain in _catch_all_domains:
        return _catch_all_domains[domain]

    try:
        random_local = "zz" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        code = _smtp_check(f"{random_local}@{domain}", mx)
        result = code == 250
    except Exception:
        result = False

    _catch_all_domains[domain] = result
    _persist_catch_all_cache()
    return result


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------


def verify_email(email: str) -> VerificationResult:
    """Verify a single email using Disify + SMTP.

    Flow:
    1. Check cache
    2. Disify domain validation
    3. If domain invalid/disposable -> done
    4. SMTP mailbox probe
    5. Cache and return result
    """
    email = email.lower().strip()

    if not email or "@" not in email:
        return VerificationResult(email=email, status="missing")

    # Check cache first
    cached_status = _get_cached(email)
    if cached_status is not None:
        logger.info(f"cached: {email} -> {cached_status}")
        return VerificationResult(email=email, status=cached_status)

    # Step 1: Disify domain validation
    disify = validate_email_domain(email)

    # Invalid format
    if not disify.format_valid:
        _set_cached(email, "invalid")
        return VerificationResult(
            email=email, status="invalid", disify=disify, error="invalid_format"
        )

    # Disposable domain
    if disify.is_disposable:
        _set_cached(email, "disposable")
        return VerificationResult(email=email, status="disposable", disify=disify)

    # No MX records
    if not disify.dns_valid:
        _set_cached(email, "invalid")
        return VerificationResult(
            email=email, status="invalid", disify=disify, error="no_mx_records"
        )

    # Step 2: SMTP verification
    domain = disify.domain or email.split("@")[1]

    try:
        # Get MX from Disify result or do our own lookup
        if disify.mx_records:
            mx = disify.mx_records[0]
        else:
            mx = _mx_host(domain)
    except Exception as exc:
        logger.warning(f"MX lookup failed for {domain}: {exc}")
        _set_cached(email, "risky")
        return VerificationResult(
            email=email, status="risky", disify=disify, error=f"mx_lookup_failed:{exc}"
        )

    # SMTP probe
    try:
        smtp_code = _smtp_check(email, mx)
    except smtplib.SMTPConnectError as exc:
        logger.warning(f"SMTP connect failed for {email}: {exc}")
        _set_cached(email, "risky")
        return VerificationResult(
            email=email, status="risky", disify=disify, error="smtp_connect_failed"
        )
    except Exception as exc:
        logger.warning(f"SMTP error for {email}: {exc}")
        _set_cached(email, "risky")
        return VerificationResult(
            email=email,
            status="risky",
            disify=disify,
            error=f"smtp_error:{type(exc).__name__}",
        )

    # Interpret SMTP response
    if smtp_code == 250:
        # Check for catch-all before declaring valid
        if _is_catch_all_domain(domain, mx):
            _set_cached(email, "catch-all", smtp_code)
            return VerificationResult(
                email=email, status="catch-all", disify=disify, smtp_code=smtp_code
            )
        _set_cached(email, "valid", smtp_code)
        return VerificationResult(
            email=email, status="valid", disify=disify, smtp_code=smtp_code
        )

    if smtp_code in {550, 551, 552, 553, 554}:
        _set_cached(email, "invalid", smtp_code)
        return VerificationResult(
            email=email, status="invalid", disify=disify, smtp_code=smtp_code
        )

    # Other codes (421 temp failure, 450 mailbox unavailable, etc.)
    _set_cached(email, "risky", smtp_code)
    return VerificationResult(
        email=email, status="risky", disify=disify, smtp_code=smtp_code
    )


def verify_email_address(email: str) -> str:
    """Backward-compatible wrapper returning just the status string."""
    result = verify_email(email)
    return result.status


def verify_emails_batch(
    emails: List[str], max_workers: int = SMTP_MAX_WORKERS
) -> Dict[str, str]:
    """Verify multiple emails in parallel.

    Returns dict mapping email -> status string.
    """
    results: Dict[str, str] = {}

    if not emails:
        return results

    # Deduplicate while preserving order
    unique_emails = list(dict.fromkeys(emails))

    # Separate cached from uncached
    uncached: List[str] = []
    for email in unique_emails:
        cached = _get_cached(email)
        if cached is not None:
            results[email] = cached
            logger.info(f"cached: {email} -> {cached}")
        else:
            uncached.append(email)

    if not uncached:
        return results

    logger.info(f"Verifying {len(uncached)} emails (workers={max_workers})")

    def _verify_one(email: str) -> Tuple[str, str]:
        result = verify_email(email)
        return email, result.status

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_verify_one, email): email for email in uncached}
        for future in as_completed(futures):
            try:
                email, status = future.result()
                results[email] = status
            except Exception as exc:
                email = futures[future]
                results[email] = "risky"
                logger.warning(f"verify error for {email}: {exc}")

    return results
