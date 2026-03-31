from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, List
from urllib.parse import urlparse

from models.lead import Lead


def deduplicate_leads(leads: Iterable[Lead]) -> List[Lead]:
    buckets: OrderedDict[str, Lead] = OrderedDict()
    for lead in leads:
        key = _build_key(lead)
        existing = buckets.get(key)
        if existing is None:
            buckets[key] = lead
        else:
            buckets[key] = _pick_better(existing, lead)
    return list(buckets.values())


def _build_key(lead: Lead) -> str:
    if lead.email:
        return f"email:{lead.email.lower()}"
    if lead.instagram_username:
        return f"ig:{lead.instagram_username.lower()}"
    if lead.website:
        return f"domain:{urlparse(lead.website).netloc.lower()}"
    return f"name:{lead.business_name.lower()}:{lead.city.lower()}"


def _pick_better(a: Lead, b: Lead) -> Lead:
    score_a = _completeness_score(a)
    score_b = _completeness_score(b)
    return a if score_a >= score_b else b


def _completeness_score(lead: Lead) -> int:
    score = 0
    for field in [lead.email, lead.website, lead.instagram_url, lead.contact_name, lead.specialty, lead.booking_link]:
        if field:
            score += 1
    score += min(lead.followers // 1000, 3)
    return score
