from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.blocklists import canonical_domain, is_blocked_domain, is_link_hub_domain
from config.settings import settings
from export.sheets_writer import SheetsWriter
from models.lead import Lead


SEEN_CACHE_PATH = settings.output_cache_dir / "seen_identities.json"
SEEN_CACHE_TTL = timedelta(hours=12)
SeenIdentityMap = dict[str, set[str]]

# Free/generic email providers whose domains should NOT be added to the seen
# domains set (otherwise we'd block every lead on gmail.com, etc.)
_FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "mail.com", "protonmail.com", "zoho.com", "yandex.com",
    "live.com", "msn.com", "me.com", "mac.com", "googlemail.com",
    "proton.me", "pm.me", "hey.com", "fastmail.com", "yahoo.co.uk",
    "hotmail.co.uk", "outlook.co.uk", "comcast.net", "att.net",
    "verizon.net", "sbcglobal.net", "cox.net", "charter.net",
}

# Domains that should NEVER be tracked as "seen" — they are platforms, not
# individual coach websites.  Tracking them poisons the seen set and causes
# every lead sourced from that platform to be rejected.
_META_DOMAINS = {
    "instagram.com", "facebook.com", "twitter.com", "x.com",
    "tiktok.com", "youtube.com", "linkedin.com", "pinterest.com",
    "threads.net",
}


def _is_meta_domain(domain: str) -> bool:
    """Return True if *domain* is a social/link-hub/blocked platform domain.

    These domains must never enter the seen-domains set because they are
    shared infrastructure, not individual coach websites.
    """
    if not domain:
        return False
    if domain in _META_DOMAINS:
        return True
    if is_blocked_domain(domain):
        return True
    if is_link_hub_domain(domain):
        return True
    return False


def _empty_seen() -> SeenIdentityMap:
    return {"emails": set(), "instagrams": set(), "domains": set()}


def _enrich_domains_from_emails(seen: SeenIdentityMap) -> int:
    """Extract domains from known emails and add them to seen domains.

    If we've already seen info@coachjane.com, then coachjane.com should be
    treated as a seen domain too.  Skips free/generic email providers.
    Returns the number of new domains added.
    """
    added = 0
    for email in seen["emails"]:
        if "@" not in email:
            continue
        domain = email.rsplit("@", 1)[1].strip().lower()
        if not domain or domain in _FREE_EMAIL_PROVIDERS:
            continue
        if domain not in seen["domains"]:
            seen["domains"].add(domain)
            added += 1
    return added


def _canonical_instagram_username(url_or_username: str) -> str:
    value = (url_or_username or "").strip().lower()
    if not value:
        return ""
    if "instagram.com" not in value:
        return value.lstrip("@")
    path = (
        Path(value.split("instagram.com", 1)[1].split("?", 1)[0]).as_posix().strip("/")
    )
    if not path:
        return ""
    return path.split("/", 1)[0].lstrip("@")


def _serialize_seen(seen: SeenIdentityMap) -> dict[str, object]:
    return {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "emails": sorted(seen["emails"]),
        "instagrams": sorted(seen["instagrams"]),
        "domains": sorted(seen["domains"]),
    }


def persist_seen_identities(seen: SeenIdentityMap) -> None:
    try:
        SEEN_CACHE_PATH.write_text(
            json.dumps(_serialize_seen(seen), indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _load_seen_cache() -> SeenIdentityMap | None:
    if not SEEN_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(SEEN_CACHE_PATH.read_text(encoding="utf-8"))
        saved_at_raw = str(data.get("saved_at", ""))
        saved_at = datetime.fromisoformat(saved_at_raw) if saved_at_raw else None
        if not saved_at or datetime.now(timezone.utc) - saved_at > SEEN_CACHE_TTL:
            return None
        return {
            "emails": {
                str(item).strip().lower()
                for item in data.get("emails", [])
                if str(item).strip()
            },
            "instagrams": {
                _canonical_instagram_username(str(item).strip())
                for item in data.get("instagrams", [])
                if _canonical_instagram_username(str(item).strip())
            },
            "domains": {
                d
                for item in data.get("domains", [])
                if str(item).strip()
                for d in [canonical_domain(str(item).strip()) or str(item).strip().lower()]
                if d and not _is_meta_domain(d)
            },
        }
    except Exception:
        return None


def load_seen_identities(log) -> SeenIdentityMap:
    cached = _load_seen_cache()
    if cached is not None:
        email_domains = _enrich_domains_from_emails(cached)
        if email_domains:
            persist_seen_identities(cached)
        log(
            f"Loaded seen identities from cache: {len(cached['emails'])} emails, "
            f"{len(cached['instagrams'])} IGs, {len(cached['domains'])} domains "
            f"(+{email_domains} domains from emails)"
        )
        return cached

    seen = _empty_seen()
    try:
        writer = SheetsWriter()
        writer.ensure_tabs()
        writer.ensure_all_leads_header()
        rows = writer.sheet.worksheet("All_Leads").get_all_records()
    except Exception as exc:
        log(f"Could not load seen identities from sheet: {exc}")
        return seen

    for row in rows:
        email = str(row.get("email", "")).strip().lower()
        if email:
            seen["emails"].add(email)

        for candidate in [
            str(row.get("instagram_username", "")).strip(),
            str(row.get("instagram_url", "")).strip(),
        ]:
            username = _canonical_instagram_username(candidate)
            if username:
                seen["instagrams"].add(username)

        for url in [
            str(row.get("website", "")).strip(),
            str(row.get("source_url", "")).strip(),
        ]:
            domain = canonical_domain(url)
            if domain and not _is_meta_domain(domain):
                seen["domains"].add(domain)

    email_domains = _enrich_domains_from_emails(seen)
    persist_seen_identities(seen)
    log(
        f"Loaded seen identities from sheet: {len(seen['emails'])} emails, "
        f"{len(seen['instagrams'])} IGs, {len(seen['domains'])} domains "
        f"(+{email_domains} domains from emails)"
    )
    return seen


def filter_seen_candidates(
    split: dict[str, list[dict[str, str]]], seen: SeenIdentityMap, log
) -> dict[str, list[dict[str, str]]]:
    fresh_instagram: list[dict[str, str]] = []
    fresh_websites: list[dict[str, str]] = []

    for candidate in split.get("instagram", []):
        username = _canonical_instagram_username(candidate.get("url", ""))
        if username and username in seen["instagrams"]:
            continue
        fresh_instagram.append(candidate)

    for candidate in split.get("websites", []):
        domain = canonical_domain(candidate.get("url", ""))
        if domain and domain in seen["domains"]:
            continue
        fresh_websites.append(candidate)

    log(
        f"Suppressed seen candidates: {len(split.get('instagram', [])) - len(fresh_instagram)} IG, "
        f"{len(split.get('websites', [])) - len(fresh_websites)} websites"
    )
    return {"instagram": fresh_instagram, "websites": fresh_websites}


def is_seen_lead(lead: Lead, seen: SeenIdentityMap) -> bool:
    email = lead.email.strip().lower() if lead.email else ""
    if email and email in seen["emails"]:
        return True

    for candidate in [lead.instagram_username, lead.instagram_url]:
        username = _canonical_instagram_username(candidate)
        if username and username in seen["instagrams"]:
            return True

    for url in [lead.website, lead.source_url]:
        domain = canonical_domain(url)
        if domain and not _is_meta_domain(domain) and domain in seen["domains"]:
            return True

    return False


def remember_lead_identities(lead: Lead, seen: SeenIdentityMap) -> None:
    email = lead.email.strip().lower() if lead.email else ""
    if email:
        seen["emails"].add(email)

    for candidate in [lead.instagram_username, lead.instagram_url]:
        username = _canonical_instagram_username(candidate)
        if username:
            seen["instagrams"].add(username)

    for url in [lead.website, lead.source_url]:
        domain = canonical_domain(url)
        if domain and not _is_meta_domain(domain):
            seen["domains"].add(domain)

    persist_seen_identities(seen)
