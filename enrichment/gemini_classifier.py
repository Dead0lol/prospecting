from __future__ import annotations

import json
import time
from importlib import import_module
from typing import Dict

from config.settings import settings
from models.lead import Lead


PROMPT = """
You are classifying a fitness professional for a B2B lead database.

Return JSON only with these keys:
- is_solo_online_coach
- specialty
- country
- city
- offer_type
- maturity
- weakness
- outreach_angle
- personalization_note

Context:
Instagram bio: {bio}
Business category: {business_category}
Website title: {website_title}
Website description: {website_description}
Services found: {services_found}
Website text excerpt: {website_excerpt}
Followers: {followers}
Offers online coaching: {offers_online_coaching}
Has booking link: {has_booking_link}
Has lead magnet: {has_lead_magnet}
Has pricing page: {has_pricing_page}
Platform: {platform}
""".strip()


def classify_lead(lead: Lead) -> Dict[str, str]:
    if not settings.enable_ai or not settings.gemini_api_key:
        return heuristic_classify(lead)

    try:
        genai = import_module("google.generativeai")

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = PROMPT.format(
            bio=lead.bio_text,
            business_category=lead.business_category,
            website_title=lead.website_title,
            website_description=lead.website_description,
            services_found=", ".join(lead.services_found),
            website_excerpt=(lead.raw_payload.get("page_text", "")[:1800] if lead.raw_payload else ""),
            followers=lead.followers,
            offers_online_coaching=lead.offers_online_coaching,
            has_booking_link=bool(lead.booking_link),
            has_lead_magnet=lead.has_lead_magnet,
            has_pricing_page=lead.has_pricing_page,
            platform=lead.platform,
        )
        response = model.generate_content(prompt)
        time.sleep(settings.gemini_delay_seconds)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.replace("json", "", 1).strip()
        return json.loads(text)
    except Exception:
        return heuristic_classify(lead)


def heuristic_classify(lead: Lead) -> Dict[str, str]:
    blob = " ".join(
        [
            lead.bio_text,
            lead.website_title,
            lead.website_description,
            " ".join(lead.services_found),
            str(lead.raw_payload.get("page_text", ""))[:1800],
        ]
    ).lower()
    specialty = "general fitness"
    specialty_map = {
        "fat loss": "fat loss",
        "weight loss": "weight loss",
        "strength": "strength training",
        "postpartum": "postpartum fitness",
        "women": "women's fitness",
        "men": "men's fitness",
        "nutrition": "nutrition coaching",
        "macro": "macro coaching",
    }
    for hint, value in specialty_map.items():
        if hint in blob:
            specialty = value
            break

    is_fit = any(hint in blob for hint in ["fitness", "trainer", "coach", "coaching", "fat loss", "strength"])
    is_online = any(hint in blob for hint in ["online coaching", "remote coaching", "virtual coaching", "1:1 coaching"])
    maturity = "early"
    if lead.has_testimonials and lead.has_pricing_page:
        maturity = "established"
    if lead.followers > 15000:
        maturity = "scaled"

    weakness = ""
    if not lead.has_lead_magnet:
        weakness = "Active offer presence but no visible lead magnet."
    elif not lead.booking_link:
        weakness = "No obvious booking flow on the site."
    elif not lead.email:
        weakness = "Weak direct contact path because no email was found."

    outreach_angle = ""
    if is_fit and is_online:
        outreach_angle = "Pitch a stronger client acquisition funnel for their online coaching offer."
    elif is_fit:
        outreach_angle = "Pitch clearer positioning and conversion paths for fitness offers."

    note = ""
    if lead.followers and not lead.booking_link:
        note = "Has audience attention but no clear booking CTA."
    elif lead.booking_link and not lead.has_lead_magnet:
        note = "Has sales intent but no top-of-funnel lead capture."

    return {
        "is_solo_online_coach": "yes" if is_fit else "uncertain",
        "specialty": specialty,
        "country": lead.country or "US",
        "city": lead.city or "",
        "offer_type": "1:1" if is_online else "unknown",
        "maturity": maturity,
        "weakness": weakness,
        "outreach_angle": outreach_angle,
        "personalization_note": note,
    }
