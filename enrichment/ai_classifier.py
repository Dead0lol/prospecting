from __future__ import annotations

import json
import time
from typing import Any, Dict
from urllib import request

from config.settings import settings
from models.lead import Lead


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
EXPECTED_KEYS = [
    "is_solo_online_coach",
    "specialty",
    "country",
    "city",
    "offer_type",
    "maturity",
    "weakness",
    "outreach_angle",
    "personalization_note",
]

SYSTEM_PROMPT = """
You classify fitness professionals for a B2B lead database.

Return only JSON with exactly these keys:
- is_solo_online_coach
- specialty
- country
- city
- offer_type
- maturity
- weakness
- outreach_angle
- personalization_note
""".strip()

USER_PROMPT = """
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
    if not settings.enable_ai or not settings.openrouter_api_key:
        return heuristic_classify(lead)

    fallback = heuristic_classify(lead)

    try:
        payload = _call_openrouter(lead)
        return _normalize_ai_result(payload, fallback)
    except Exception:
        return fallback


def _call_openrouter(lead: Lead) -> Dict[str, Any]:
    body = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT.format(
                    bio=lead.bio_text,
                    business_category=lead.business_category,
                    website_title=lead.website_title,
                    website_description=lead.website_description,
                    services_found=", ".join(lead.services_found),
                    website_excerpt=(
                        lead.raw_payload.get("page_text", "")[:1800]
                        if lead.raw_payload
                        else ""
                    ),
                    followers=lead.followers,
                    offers_online_coaching=lead.offers_online_coaching,
                    has_booking_link=bool(lead.booking_link),
                    has_lead_magnet=lead.has_lead_magnet,
                    has_pricing_page=lead.has_pricing_page,
                    platform=lead.platform,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "plugins": [{"id": "response-healing"}],
        "temperature": 0,
        "max_tokens": 300,
    }
    req = request.Request(
        OPENROUTER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Dead0lol/prospecting",
            "X-Title": "Fitness Coach Prospecting Pipeline",
        },
        method="POST",
    )

    with request.urlopen(req, timeout=settings.request_timeout_seconds) as response:
        raw = json.loads(response.read().decode("utf-8"))

    time.sleep(settings.openrouter_delay_seconds)
    choices = raw.get("choices", [])
    if not choices:
        raise ValueError("OpenRouter returned no choices")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter returned empty content")
    return json.loads(content)


def _normalize_ai_result(
    payload: Dict[str, Any], fallback: Dict[str, str]
) -> Dict[str, str]:
    result = dict(fallback)
    for key in EXPECTED_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                result[key] = cleaned
            continue
        result[key] = str(value)
    return result


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

    fitness_hints = [
        "fitness",
        "personal trainer",
        "online trainer",
        "fitness coach",
        "nutrition coach",
        "strength coach",
        "fat loss",
        "weight loss",
        "body recomposition",
        "macro coaching",
        "workout",
        "gym",
    ]
    is_fit = any(hint in blob for hint in fitness_hints)
    is_online = any(
        hint in blob
        for hint in [
            "online coaching",
            "remote coaching",
            "virtual coaching",
            "1:1 coaching",
        ]
    )
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
        outreach_angle = (
            "Pitch clearer positioning and conversion paths for fitness offers."
        )

    note = ""
    if lead.followers and not lead.booking_link:
        note = "Has audience attention but no clear booking CTA."
    elif lead.booking_link and not lead.has_lead_magnet:
        note = "Has sales intent but no top-of-funnel lead capture."

    return {
        "is_solo_online_coach": "yes" if is_fit else "no",
        "specialty": specialty,
        "country": lead.country or "US",
        "city": lead.city or "",
        "offer_type": "1:1" if is_online else "unknown",
        "maturity": maturity,
        "weakness": weakness,
        "outreach_angle": outreach_angle,
        "personalization_note": note,
    }
