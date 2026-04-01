from __future__ import annotations

from config.settings import settings
from models.lead import Lead


def score_lead(lead: Lead) -> Lead:
    """Assign a heuristic score and tier based on contactability and ICP fit."""
    score = 0

    # --- Email quality ---
    if lead.email_status == "valid":
        score += 20
    elif lead.email_status == "catch-all":
        score += 12
    elif lead.email_status == "unknown" and lead.email:
        score += 8  # we have an email but couldn't verify - still useful
    elif not lead.email:
        score -= 15

    # --- Email source trust ---
    if lead.email and lead.email_source == "website":
        score += 5  # found on their actual site, high trust
    elif lead.email and lead.email_source == "link_hub":
        score += 4

    # --- Location ---
    if lead.country.lower() in {"us", "usa", "united states"}:
        score += 10
    elif lead.country.lower() in {
        "uk",
        "gb",
        "united kingdom",
        "canada",
        "ca",
        "australia",
        "au",
    }:
        score += 8

    # --- ICP match ---
    if lead.ai_icp_match == "yes":
        score += 15
    elif lead.ai_icp_match == "uncertain":
        score -= 5

    # --- Business presence ---
    if lead.website:
        score += 5
    if lead.booking_link:
        score += 5
    if lead.phone:
        score += 3
    if lead.instagram_url:
        score += 3

    # --- Offer signals ---
    if lead.offers_online_coaching == "yes":
        score += 10
    if lead.has_pricing_page:
        score += 5
    if lead.has_testimonials:
        score += 5
    if lead.has_lead_magnet:
        score += 3  # means they already think about funnels

    # --- Followers (sweet spot for solo coaches) ---
    if 1000 <= lead.followers <= 50000:
        score += 8
    elif lead.followers > 100000:
        score -= 5  # probably too big, won't respond
    elif 500 <= lead.followers < 1000:
        score += 3
    # 0 followers = we just don't have the data, no penalty

    # --- Opportunity signals (things you can pitch) ---
    if not lead.has_lead_magnet and lead.website:
        score += 3  # opportunity: they need one
    if not lead.booking_link and lead.website:
        score += 2  # opportunity: no clear CTA
    if lead.weakness:
        score += 3

    # --- Services depth ---
    if len(lead.services_found) >= 2:
        score += 3

    lead.lead_score = max(0, min(100, score))
    if lead.lead_score >= settings.hot_lead_threshold:
        lead.lead_tier = "hot"
    elif lead.lead_score >= settings.good_lead_threshold:
        lead.lead_tier = "good"
    else:
        lead.lead_tier = "review"
    return lead
