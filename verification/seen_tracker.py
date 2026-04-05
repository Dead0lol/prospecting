from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.blocklists import canonical_domain
from config.settings import settings
from export.sheets_writer import SheetsWriter
from models.lead import Lead


SEEN_CACHE_PATH = settings.output_cache_dir / "seen_identities.json"
SEEN_CACHE_TTL = timedelta(hours=12)
SeenIdentityMap = dict[str, set[str]]


def _empty_seen() -> SeenIdentityMap:
    return {"emails": set(), "instagrams": set(), "domains": set()}


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
                canonical_domain(str(item).strip()) or str(item).strip().lower()
                for item in data.get("domains", [])
                if str(item).strip()
            },
        }
    except Exception:
        return None


def load_seen_identities(log) -> SeenIdentityMap:
    cached = _load_seen_cache()
    if cached is not None:
        log(
            f"Loaded seen identities from cache: {len(cached['emails'])} emails, "
            f"{len(cached['instagrams'])} IGs, {len(cached['domains'])} domains"
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
            if domain:
                seen["domains"].add(domain)

    persist_seen_identities(seen)
    log(
        f"Loaded seen identities from sheet: {len(seen['emails'])} emails, "
        f"{len(seen['instagrams'])} IGs, {len(seen['domains'])} domains"
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
        if domain and domain in seen["domains"]:
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
        if domain:
            seen["domains"].add(domain)

    persist_seen_identities(seen)
