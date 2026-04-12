from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

from config.blocklists import (
    ACCEPTED_SOURCE_DOMAINS,
    canonical_domain,
    domain_matches,
    is_blocked_domain,
    is_link_hub_domain,
)
from config.keywords import (
    DISCOVERY_KEYWORDS,
    DISCOVERY_MODIFIERS,
    COACH_PLATFORM_DOMAINS,
)
from config.settings import settings
from discovery.duckduckgo_search import build_queries, discover_candidates
from discovery.individual_search import search_individual_query
from discovery.instagram_parser import is_likely_name, parse_ig_snippet
from discovery.web_search import (
    quick_reject_website,
    rank_website_candidates,
    split_candidate_urls,
)
from enrichment.ai_classifier import classify_lead
from enrichment.icebreaker_generator import generate_icebreaker
from export.sheets_writer import SheetsWriter
from extraction.email_extractor import pick_best_email

from extraction.linktree_parser import parse_link_hub
from extraction.website_crawler import crawl_website
from logging_utils import get_logger
from models.lead import Lead
from scoring.lead_scorer import score_lead
from verification.deduplicator import deduplicate_leads
from verification.seen_tracker import (
    filter_seen_candidates,
    is_seen_lead,
    load_seen_identities,
    remember_lead_identities,
)
from verification.email_verifier import verify_email_address, verify_emails_batch
from utils import cast_dict, cast_int, cast_list


logger = get_logger("pipeline")


def log(message: str) -> None:
    logger.info(message)


CHECKPOINT_DIR = settings.output_cache_dir / "runs"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_EVERY = 10
DISCOVERY_STATE_PATH = settings.output_cache_dir / "discovery_state.json"


def checkpoint_path(run_id: str) -> Path:
    return CHECKPOINT_DIR / f"{run_id}.json"


def save_checkpoint(leads: List[Lead], run_id: str, country: str) -> None:
    payload = {
        "run_id": run_id,
        "country": country,
        "lead_count": len(leads),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "leads": [lead.to_dict() for lead in leads],
    }
    checkpoint_path(run_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_discovery_offset(total_queries: int) -> int:
    if total_queries <= 0:
        return 0
    try:
        data = json.loads(DISCOVERY_STATE_PATH.read_text(encoding="utf-8"))
        return int(data.get("next_offset", 0)) % total_queries
    except Exception:
        return 0


def _save_discovery_offset(offset: int, total_queries: int) -> None:
    if total_queries <= 0:
        return
    payload = {
        "next_offset": offset % total_queries,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    DISCOVERY_STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _rotate_queries(queries: List[str], window: int) -> List[str]:
    if not queries:
        return []
    offset = _load_discovery_offset(len(queries))
    rotated = queries[offset:] + queries[:offset]
    next_offset = offset + max(1, min(window, len(queries)))
    _save_discovery_offset(next_offset, len(queries))
    log(f"Discovery query offset: {offset}/{len(queries)}")
    return rotated


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def run_discovery(country: str, limit: int) -> Dict[str, List[Dict[str, str]]]:
    """Run keyword-based search queries and return categorised candidate URLs.

    Geography is irrelevant — the ICP is any English-speaking fitness coach globally.
    """
    queries = build_queries(
        DISCOVERY_KEYWORDS,
        DISCOVERY_MODIFIERS,
        platforms=ACCEPTED_SOURCE_DOMAINS,
    )
    queries = _rotate_queries(queries, settings.max_discovery_queries)
    log(
        f"Built {len(queries)} total queries, will run up to {settings.max_discovery_queries}"
    )
    candidates = discover_candidates(queries, target=limit * 10)
    log(f"Discovery returned {len(candidates)} raw candidates")
    split = split_candidate_urls(candidates)
    log(
        f"Filtered: {len(split['instagram'])} Instagram, {len(split['websites'])} websites"
    )
    return split


def _is_link_hub(url: str) -> bool:
    return is_link_hub_domain(canonical_domain(url))


def _extract_targets_from_link_hub(url: str) -> Dict[str, str]:
    targets = {"website": "", "instagram_url": ""}
    try:
        hub = parse_link_hub(url)
    except Exception as exc:
        log(f"  Link hub parse failed: {exc}")
        return targets

    for link in cast_list(hub.get("links", [])):
        if not link.startswith("http"):
            continue
        domain = canonical_domain(link)
        if not domain:
            continue
        if "instagram.com" in domain and not targets["instagram_url"]:
            targets["instagram_url"] = link
            continue
        if is_blocked_domain(domain):
            continue
        if domain_matches(domain, COACH_PLATFORM_DOMAINS):
            continue
        if _is_link_hub(link):
            continue
        if not targets["website"]:
            targets["website"] = link

    return targets


# ---------------------------------------------------------------------------
# Lead processing: shared logic for both IG and website candidates
# ---------------------------------------------------------------------------


def enrich_lead_from_website(lead: Lead) -> None:
    """Crawl the lead's website and fill in data fields."""
    if not lead.website:
        return
    try:
        log(f"  Crawling {lead.website}")
        crawl_data = crawl_website(lead.website)
        lead.raw_payload.update(crawl_data)
        lead.website_title = str(crawl_data.get("website_title", ""))
        lead.website_description = str(crawl_data.get("website_description", ""))
        lead.phone = str(crawl_data.get("phone", "")) or lead.phone
        lead.booking_link = lead.booking_link or str(crawl_data.get("booking_link", ""))
        lead.pricing_page = str(crawl_data.get("pricing_page", ""))
        lead.has_pricing_page = bool(crawl_data.get("has_pricing_page", False))
        lead.has_lead_magnet = bool(crawl_data.get("has_lead_magnet", False))
        lead.has_testimonials = bool(crawl_data.get("has_testimonials", False))
        lead.services_found = cast_list(crawl_data.get("services_found", []))
        lead.platform = str(crawl_data.get("platform", "unknown"))
        lead.offers_online_coaching = str(
            crawl_data.get("offers_online_coaching", "unknown")
        )
        # Use the crawler's extracted contact name if we don't have one yet
        crawled_name = str(crawl_data.get("contact_name", ""))
        if crawled_name and not lead.contact_name:
            lead.contact_name = crawled_name
            log(f"  Extracted contact name: {crawled_name}")
        socials = cast_dict(crawl_data.get("socials", {}))
        lead.linkedin_url = lead.linkedin_url or str(socials.get("linkedin_url", ""))
        lead.youtube_url = lead.youtube_url or str(socials.get("youtube_url", ""))
        lead.tiktok_url = lead.tiktok_url or str(socials.get("tiktok_url", ""))
        if not lead.instagram_url:
            lead.instagram_url = str(socials.get("instagram_url", ""))
        lead.social_links = [v for v in socials.values() if v]
        emails = cast_list(crawl_data.get("emails", []))
        if emails and not lead.email:
            domain = urlparse(lead.website).netloc.replace("www.", "")
            lead.email = pick_best_email(emails, domain)
            lead.email_source = "website"
            log(f"  Found email on site: {lead.email}")
    except Exception as exc:
        lead.notes.append(f"crawl_error:{exc}")
        log(f"  Crawl failed: {exc}")


def verify_lead_email(lead: Lead) -> None:
    """Verify the lead's email if present."""
    if not lead.email:
        lead.email_status = "missing"
        return
    log(f"  Verifying {lead.email}")
    lead.email_status = verify_email_address(lead.email)
    lead.verified_at = datetime.now(timezone.utc).isoformat()
    log(f"  Status: {lead.email_status}")


def verify_leads_in_batch(leads: List[Lead]) -> None:
    """Verify all lead emails in parallel after candidate collection."""
    email_map = {lead.email: lead for lead in leads if lead.email}
    missing = [lead for lead in leads if not lead.email]

    for lead in missing:
        lead.email_status = "missing"

    if not email_map:
        return

    statuses = verify_emails_batch(list(email_map.keys()))
    verified_at = datetime.now(timezone.utc).isoformat()
    for email, lead in email_map.items():
        lead.email_status = statuses.get(email, "unknown")
        lead.verified_at = verified_at


def classify_and_score(lead: Lead) -> None:
    """Run heuristic/AI classification and scoring."""
    try:
        ai = classify_lead(lead)
        lead.ai_icp_match = ai.get("is_solo_online_coach", "uncertain")
        lead.specialty = ai.get("specialty", "unknown")
        lead.country = ai.get("country", lead.country) or lead.country
        lead.city = ai.get("city", lead.city) or lead.city
        lead.offer_type = ai.get("offer_type", "unknown")
        lead.ai_maturity = ai.get("maturity", "unknown")
        lead.weakness = ai.get("weakness", "")
        lead.outreach_angle = ai.get("outreach_angle", "")
        lead.personalization_note = ai.get("personalization_note", "")
    except Exception as exc:
        lead.notes.append(f"classify_error:{exc}")

    # Generate personalized icebreaker
    try:
        lead.ice_breaker = generate_icebreaker(lead)
    except Exception as exc:
        log(f"  Icebreaker generation failed: {exc}")
        lead.ice_breaker = ""

    score_lead(lead)
    log(f"  Score: {lead.lead_score} ({lead.lead_tier}) icp={lead.ai_icp_match}")


def _result_mentions_coach(
    result: Dict[str, str], username: str, contact_name: str
) -> bool:
    """Check if a search result title/body/URL mentions the coach's username or name.
    This prevents matching random fitness sites that have nothing to do with the coach.
    """
    blob = f"{result.get('title', '')} {result.get('body', '')} {result.get('url', '')}".lower()
    # Check username (most reliable)
    if username and username.lower() in blob:
        return True
    # Check name parts (at least first AND last name must appear)
    if contact_name and is_likely_name(contact_name):
        name_parts = [p.lower() for p in contact_name.split() if len(p) > 2]
        if len(name_parts) >= 2 and all(part in blob for part in name_parts):
            return True
        # Single name: check if it appears in the domain
        if len(name_parts) == 1:
            domain = urlparse(result.get("url", "")).netloc.lower()
            if name_parts[0] in domain:
                return True
    return False


def _find_website_for_ig_lead(lead: Lead) -> None:
    """Run a quick DuckDuckGo search to find the coach's website.

    Strategy: search by IG username first (most unique identifier),
    then fall back to contact name if username search fails.
    Rejects SaaS platforms, aggregators, and blocklisted domains.
    Validates that the result actually mentions the coach before accepting.
    """
    if lead.website:
        return  # already have one

    username = lead.instagram_username or ""
    name = lead.contact_name or ""

    # Build search queries — username first (unique), then name
    queries_to_try: List[str] = []
    if username:
        queries_to_try.append(f"{username} fitness coach website")
    if name and name != username and is_likely_name(name):
        queries_to_try.append(f'"{name}" fitness coach website')

    if not queries_to_try:
        return

    def _can_use_website_result(rurl: str) -> bool:
        domain = urlparse(rurl).netloc.lower().lstrip("www.")
        if not domain:
            return False
        if "instagram.com" in domain:
            return False
        if is_blocked_domain(domain):
            return False
        if domain_matches(domain, COACH_PLATFORM_DOMAINS):
            return False
        if urlparse(rurl).path.count("/") > 2:
            return False
        return True

    for query in queries_to_try:
        log(f"  Searching for website: {query[:60]}")
        try:
            results = search_individual_query(query, max_results=5)
        except Exception as exc:
            log(f"  Website search failed: {exc}")
            continue

        for r in results:
            rurl = r.get("url", "")
            domain = urlparse(rurl).netloc.lower().lstrip("www.")
            if not domain:
                continue
            # Skip Instagram, social media, blocklisted domains
            if "instagram.com" in domain:
                continue
            if is_blocked_domain(domain):
                continue
            # Skip SaaS/platform/aggregator domains
            if domain_matches(domain, COACH_PLATFORM_DOMAINS):
                continue
            # Skip deep article paths (likely not the coach's homepage)
            if urlparse(rurl).path.count("/") > 2:
                continue

            # RELEVANCE CHECK: does this result actually mention the coach?
            if not _result_mentions_coach(r, username, name):
                continue

            # Handle link hubs — resolve to find the real site
            if any(h in domain for h in ["linktr.ee", "beacons.ai", "stan.store"]):
                try:
                    hub = parse_link_hub(rurl)
                    for link in cast_list(hub.get("links", [])):
                        if (
                            link.startswith("http")
                            and urlparse(link).netloc
                            and _can_use_website_result(link)
                        ):
                            lead.website = link
                            log(f"  Found website via link hub: {link[:60]}")
                            return
                except Exception:
                    pass
                continue

            if _can_use_website_result(rurl):
                lead.website = rurl
                log(f"  Found website: {rurl[:60]}")
                return

    # Last chance: search directly for common link hubs by username, then resolve them.
    hub_queries: List[str] = []
    if username:
        hub_queries.extend(
            [
                f"site:linktr.ee {username}",
                f"site:beacons.ai {username}",
                f"site:stan.store {username}",
            ]
        )

    for query in hub_queries:
        log(f"  Searching link hubs: {query}")
        try:
            results = search_individual_query(query, max_results=3)
        except Exception:
            continue

        for r in results:
            rurl = r.get("url", "")
            domain = urlparse(rurl).netloc.lower().lstrip("www.")
            if not any(h in domain for h in ["linktr.ee", "beacons.ai", "stan.store"]):
                continue
            if (
                username
                and username.lower() not in rurl.lower()
                and not _result_mentions_coach(r, username, name)
            ):
                continue
            try:
                hub = parse_link_hub(rurl)
                for link in cast_list(hub.get("links", [])):
                    if (
                        link.startswith("http")
                        and urlparse(link).netloc
                        and _can_use_website_result(link)
                    ):
                        lead.website = link
                        lead.notes.append(f"website_via_hub:{domain}")
                        log(f"  Found website via direct hub search: {link[:60]}")
                        return
            except Exception:
                continue

    log(f"  No relevant website found for {username}")


# ---------------------------------------------------------------------------
# Instagram candidate processing
# ---------------------------------------------------------------------------


def process_instagram_candidate(
    candidate: Dict[str, str], country: str, seen: dict | None = None
) -> Lead | None:
    """Process a single Instagram candidate into a Lead.

    Uses DuckDuckGo snippet data (name, followers, bio) instead of
    direct Instagram scraping.
    """
    url = candidate["url"]
    log(f"IG: {url}")

    parsed = parse_ig_snippet(candidate)
    username = parsed["instagram_username"]
    if not username:
        log(f"  Could not parse username from URL, skipping")
        return None

    followers = cast_int(parsed.get("followers", 0))
    contact_name = str(parsed.get("contact_name", ""))
    bio_text = str(parsed.get("bio_text", ""))

    log(f"  Parsed: {contact_name} | {followers} followers")

    lead = Lead(
        business_name=str(parsed.get("business_name", "")),
        contact_name=contact_name,
        instagram_url=str(parsed.get("instagram_url", "")),
        instagram_username=str(username),
        followers=followers,
        bio_text=bio_text,
        source_query=candidate.get("query", ""),
        source_type="instagram",
        source_url=url,
        country=country,
    )

    # Try to find their website via a follow-up search
    _find_website_for_ig_lead(lead)

    # DROP IG-only leads that have no website — they score 16-24 (useless)
    # and waste expensive SMTP time. Only process if we found a real site.
    if not lead.website:
        log(f"  Dropping IG-only lead (no website found): {username}")
        return None

    # Early seen-domain check: skip crawling if the resolved website domain
    # is already in our seen set.  This avoids wasting 10-15s per candidate
    # on website crawls that will just be rejected later anyway.
    if seen:
        resolved_domain = canonical_domain(lead.website)
        if resolved_domain and resolved_domain in seen["domains"]:
            log(f"  Skipping: resolved domain {resolved_domain} already seen (pre-crawl)")
            return None

    enrich_lead_from_website(lead)
    return lead


# ---------------------------------------------------------------------------
# Website candidate processing
# ---------------------------------------------------------------------------


def process_website_candidate(
    candidate: Dict[str, str], country: str, seen: dict | None = None
) -> Lead | None:
    """Process a website search result into a Lead (or None if junk)."""
    url = candidate.get("url", "")
    title = candidate.get("title", "")

    if quick_reject_website(url):
        return None

    log(f"WEB: {url[:70]}")
    resolved_website = url
    resolved_instagram = ""
    if _is_link_hub(url):
        targets = _extract_targets_from_link_hub(url)
        resolved_website = targets.get("website", "") or url
        resolved_instagram = targets.get("instagram_url", "")
        log(
            f"  Resolved link hub -> website={bool(targets.get('website'))} instagram={bool(resolved_instagram)}"
        )

    # Early seen-domain check: skip crawling if the resolved domain is
    # already known.  Saves 10-15s of website crawling per candidate.
    if seen:
        resolved_domain = canonical_domain(resolved_website)
        if resolved_domain and resolved_domain in seen["domains"]:
            log(f"  Skipping: resolved domain {resolved_domain} already seen (pre-crawl)")
            return None

    lead = Lead(
        business_name=title or urlparse(url).netloc,
        source_query=candidate.get("query", ""),
        source_type="website",
        source_url=url,
        website=resolved_website,
        instagram_url=resolved_instagram,
        country=country,
    )

    enrich_lead_from_website(lead)

    # Quick viability check BEFORE expensive email/SMTP work
    if not _has_coach_signals(lead):
        log(f"  Rejected: no coach signals")
        return None

    return lead


def _has_coach_signals(lead: Lead) -> bool:
    """Cheap check: does this look like a real coach's site?"""
    blob = (
        f"{lead.website_title} {lead.website_description} {' '.join(lead.services_found)} "
        f"{lead.bio_text}"
    ).lower()
    fitness_keywords = [
        "fitness",
        "personal trainer",
        "online coach",
        "fitness coach",
        "nutrition coach",
        "strength coach",
        "weight loss",
        "fat loss",
        "body recomposition",
        "macro coaching",
        "workout",
        "gym",
        "transformation",
    ]
    if not any(keyword in blob for keyword in fitness_keywords):
        return False

    signals = 0
    if lead.booking_link:
        signals += 1
    if lead.offers_online_coaching == "yes":
        signals += 1
    if lead.has_pricing_page:
        signals += 1
    if lead.instagram_url:
        signals += 1
    if lead.email and urlparse(lead.email).scheme == "":
        signals += 1
    if len(lead.services_found) >= 1:
        signals += 1
    return signals >= 2


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(country: str = "US", limit: int = 100) -> List[Lead]:
    log(f"=== Pipeline start: country={country} limit={limit} ===")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seen = load_seen_identities(log)
    split = filter_seen_candidates(run_discovery(country, limit), seen, log)

    leads: List[Lead] = []
    ig_candidates = split["instagram"]
    web_candidates = rank_website_candidates(split["websites"])

    # Process WEBSITE candidates first — they produce higher-quality leads
    # because we already have their domain (no guessing needed)
    interrupted = False
    try:
        if web_candidates:
            log(f"--- Processing {len(web_candidates)} website candidates ---")
            tried = 0
            for candidate in web_candidates:
                if tried >= limit * 3:  # Don't try forever
                    break
                tried += 1
                lead = process_website_candidate(candidate, country, seen=seen)
                if lead:
                    if is_seen_lead(lead, seen):
                        log("  Skipping seen website lead")
                        continue
                    lead.run_id = run_id
                    remember_lead_identities(lead, seen)
                    leads.append(lead)
                    if len(leads) % CHECKPOINT_EVERY == 0:
                        save_checkpoint(leads, run_id, country)
                        log(f"Checkpoint saved: {len(leads)} leads")
                    if len(leads) >= limit:
                        break

        # Fill remaining slots from Instagram candidates
        remaining = limit - len(leads)
        if remaining > 0 and ig_candidates:
            log(f"--- Processing IG candidates (need {remaining} more) ---")
            for i, candidate in enumerate(ig_candidates, 1):
                if i > remaining * 2:  # Don't try too many
                    break
                log(f"[{i}/{len(ig_candidates)}]")
                lead = process_instagram_candidate(candidate, country, seen=seen)
                if lead:
                    if is_seen_lead(lead, seen):
                        log("  Skipping seen Instagram lead")
                        continue
                    lead.run_id = run_id
                    remember_lead_identities(lead, seen)
                    leads.append(lead)
                    if len(leads) % CHECKPOINT_EVERY == 0:
                        save_checkpoint(leads, run_id, country)
                        log(f"Checkpoint saved: {len(leads)} leads")
                if len(leads) >= limit:
                    break
    except KeyboardInterrupt:
        interrupted = True
        log("Interrupted - returning partial results")

    leads = deduplicate_leads(leads)
    verify_leads_in_batch(leads)
    for lead in leads:
        classify_and_score(lead)
    save_checkpoint(leads, run_id, country)
    if interrupted:
        log(f"=== Pipeline interrupted: {len(leads)} leads after dedup ===")
    else:
        log(f"=== Pipeline done: {len(leads)} leads after dedup ===")
    return leads


def export_run(leads: List[Lead], country: str) -> Dict[str, int]:
    log("Exporting to Google Sheets")
    writer = SheetsWriter()
    writer.ensure_tabs()
    writer.clear_priority_tabs()
    writer.ensure_all_leads_header()

    grouped: Dict[str, List[Lead]] = defaultdict(list)
    for lead in leads:
        grouped[lead.lead_tier].append(lead)

    writer.write_leads("Hot_Leads", grouped.get("hot", []))
    writer.write_leads("Good_Leads", grouped.get("good", []))
    writer.write_leads("Review_Queue", grouped.get("review", []))
    writer.write_leads("All_Leads", leads)

    counts = {
        "processed": len(leads),
        "hot": len(grouped.get("hot", [])),
        "good": len(grouped.get("good", [])),
        "review": len(grouped.get("review", [])),
    }
    writer.log_run(
        "success",
        country,
        counts["processed"],
        counts["hot"],
        counts["good"],
        counts["review"],
    )
    log(f"Export done: {counts}")
    return counts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fitness coach lead pipeline")
    parser.add_argument("--country", default="US")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    start = time.time()
    leads = run(country=args.country, limit=args.limit)
    counts = export_run(leads, args.country)
    elapsed = time.time() - start

    if args.json:
        print(
            json.dumps(
                {
                    "counts": counts,
                    "elapsed_seconds": round(elapsed, 1),
                    "sample": [lead.to_dict() for lead in leads[:5]],
                },
                indent=2,
            )
        )
    else:
        log(f"Done in {elapsed:.0f}s -> {counts}")


if __name__ == "__main__":
    main()
