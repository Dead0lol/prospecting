from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Lead:
    lead_score: int = 0
    lead_tier: str = "review"
    business_name: str = ""
    contact_name: str = ""
    email: str = ""
    email_status: str = "unknown"
    email_source: str = ""
    website: str = ""
    country: str = ""
    city: str = ""
    instagram_url: str = ""
    instagram_username: str = ""
    followers: int = 0
    linkedin_url: str = ""
    youtube_url: str = ""
    tiktok_url: str = ""
    phone: str = ""
    specialty: str = ""
    offers_online_coaching: str = "unknown"
    offer_type: str = "unknown"
    booking_link: str = ""
    pricing_page: str = ""
    has_pricing_page: bool = False
    has_lead_magnet: bool = False
    has_testimonials: bool = False
    platform: str = "unknown"
    weakness: str = ""
    outreach_angle: str = ""
    personalization_note: str = ""
    ice_breaker: str = ""
    source_url: str = ""
    source_type: str = ""
    source_query: str = ""
    source_confidence: str = "medium"
    business_category: str = ""
    bio_text: str = ""
    website_title: str = ""
    website_description: str = ""
    services_found: List[str] = field(default_factory=list)
    social_links: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=utc_now)
    verified_at: str = ""
    ai_icp_match: str = "uncertain"
    ai_maturity: str = "unknown"
    run_id: str = ""
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["services_found"] = ", ".join(self.services_found)
        data["social_links"] = ", ".join(self.social_links)
        data["notes"] = " | ".join(self.notes)
        return data


SHEET_COLUMNS = [
    "lead_score",
    "lead_tier",
    "contact_name",
    "email",
    "email_status",
    "email_source",
    "business_name",
    "specialty",
    "country",
    "city",
    "instagram_url",
    "instagram_username",
    "followers",
    "website",
    "offers_online_coaching",
    "offer_type",
    "booking_link",
    "has_lead_magnet",
    "has_pricing_page",
    "has_testimonials",
    "platform",
    "weakness",
    "outreach_angle",
    "personalization_note",
    "ice_breaker",
    "phone",
    "linkedin_url",
    "youtube_url",
    "tiktok_url",
    "source_url",
    "source_type",
    "source_query",
    "source_confidence",
    "business_category",
    "bio_text",
    "website_title",
    "website_description",
    "services_found",
    "social_links",
    "notes",
    "discovered_at",
    "verified_at",
    "ai_icp_match",
    "ai_maturity",
    "run_id",
]
