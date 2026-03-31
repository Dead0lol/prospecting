from __future__ import annotations

import hashlib
import json
import random
import smtplib
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import dns.resolver

from config.settings import settings

# Simple disk cache so we never re-verify the same email or domain twice
_CACHE_DIR = settings.output_cache_dir / "smtp"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Track which domains are catch-all so we skip guessing on them
_catch_all_domains: Dict[str, bool] = {}

SMTP_CONNECT_TIMEOUT = 5  # seconds per SMTP connection


def _log(message: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] [smtp] {message}", flush=True)


def _cache_path(email: str) -> Path:
    h = hashlib.md5(email.lower().encode()).hexdigest()
    return _CACHE_DIR / f"{h}.json"


def _get_cached(email: str) -> str | None:
    path = _cache_path(email)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data.get("status")
        except Exception:
            pass
    return None


def _set_cached(email: str, status: str) -> None:
    try:
        _cache_path(email).write_text(json.dumps({"email": email, "status": status}))
    except Exception:
        pass


def _mx_host(domain: str) -> str:
    records = dns.resolver.resolve(domain, "MX", lifetime=5)
    sorted_records = sorted(records, key=lambda item: item.preference)
    return str(sorted_records[0].exchange).rstrip(".")


def _smtp_check(email: str, mx: str) -> int | None:
    server = smtplib.SMTP(timeout=SMTP_CONNECT_TIMEOUT)
    try:
        server.connect(mx)
        server.helo("verify.local")
        server.mail("check@verify.local")
        code, _ = server.rcpt(email)
        return int(code)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def is_catch_all_domain(domain: str) -> bool:
    """Check if a domain accepts all addresses. Cached per-run."""
    if domain in _catch_all_domains:
        return _catch_all_domains[domain]

    try:
        mx = _mx_host(domain)
        random_local = "zz" + "".join(random.choice(string.ascii_lowercase) for _ in range(12))
        code = _smtp_check(f"{random_local}@{domain}", mx)
        result = code == 250
    except Exception:
        result = False

    _catch_all_domains[domain] = result
    return result


def verify_email_address(email: str) -> str:
    """Verify an email. Returns: valid, invalid, catch-all, unknown."""
    cached = _get_cached(email)
    if cached is not None:
        _log(f"cached: {email} -> {cached}")
        return cached

    domain = email.split("@", 1)[1]

    # Step 1: MX exists?
    try:
        mx = _mx_host(domain)
    except Exception:
        _set_cached(email, "invalid")
        return "invalid"

    # Step 2: SMTP check
    try:
        actual_status = _smtp_check(email, mx)
    except Exception:
        _set_cached(email, "unknown")
        return "unknown"

    if actual_status == 250:
        if is_catch_all_domain(domain):
            _set_cached(email, "catch-all")
            return "catch-all"
        _set_cached(email, "valid")
        return "valid"

    if actual_status in {550, 551, 553}:
        _set_cached(email, "invalid")
        return "invalid"

    _set_cached(email, "unknown")
    return "unknown"


# ---------------------------------------------------------------------------
# Batch (parallel) verification
# ---------------------------------------------------------------------------

SMTP_MAX_WORKERS = 5


def verify_emails_batch(emails: List[str], max_workers: int = SMTP_MAX_WORKERS) -> Dict[str, str]:
    """Verify multiple emails in parallel using a thread pool.

    Returns a dict mapping email -> status.
    Thread-safe because each verification is independent (own SMTP connection,
    own cache file, and _catch_all_domains dict is append-only).
    """
    results: Dict[str, str] = {}

    if not emails:
        return results

    # Deduplicate while preserving order
    unique_emails = list(dict.fromkeys(emails))

    # Separate cached from uncached to avoid unnecessary thread overhead
    uncached: List[str] = []
    for email in unique_emails:
        cached = _get_cached(email)
        if cached is not None:
            results[email] = cached
            _log(f"cached: {email} -> {cached}")
        else:
            uncached.append(email)

    if not uncached:
        return results

    _log(f"Verifying {len(uncached)} emails in parallel (workers={max_workers})")

    def _verify_one(email: str) -> Tuple[str, str]:
        return email, verify_email_address(email)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_verify_one, email): email for email in uncached}
        for future in as_completed(futures):
            try:
                email, status = future.result()
                results[email] = status
            except Exception as exc:
                email = futures[future]
                results[email] = "unknown"
                _log(f"verify error for {email}: {exc}")

    return results
