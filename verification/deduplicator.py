from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, List
from urllib.parse import urlparse

from models.lead import Lead


def deduplicate_leads(leads: Iterable[Lead]) -> List[Lead]:
    buckets: OrderedDict[str, Lead] = OrderedDict()
    key_to_primary: dict[str, str] = {}

    for lead in leads:
        keys = _build_keys(lead)
        primary_matches = [key_to_primary[key] for key in keys if key in key_to_primary]
        primary_matches = list(dict.fromkeys(primary_matches))

        if not primary_matches:
            primary_key = keys[0] if keys else f"name:{lead.business_name.lower()}:{lead.city.lower()}"
            buckets[primary_key] = lead
            for key in keys:
                key_to_primary[key] = primary_key
            continue

        primary_key = primary_matches[0]
        merged = _merge_leads(buckets[primary_key], lead)

        for other_primary in primary_matches[1:]:
            merged = _merge_leads(merged, buckets.pop(other_primary))
            for alias, alias_primary in list(key_to_primary.items()):
                if alias_primary == other_primary:
                    key_to_primary[alias] = primary_key

        buckets[primary_key] = merged
        for key in _build_keys(merged):
            key_to_primary[key] = primary_key

    return list(buckets.values())


def _build_keys(lead: Lead) -> List[str]:
    keys: List[str] = []
    if lead.email:
        keys.append(f"email:{lead.email.lower()}")

    ig_username = _canonical_instagram_username(lead)
    if ig_username:
        keys.append(f"ig:{ig_username}")

    domain = _canonical_domain(lead.website)
    if domain:
        keys.append(f"domain:{domain}")

    source_domain = _canonical_domain(lead.source_url)
    if source_domain and source_domain != domain:
        keys.append(f"source_domain:{source_domain}")

    if not keys:
        keys.append(f"name:{lead.business_name.lower()}:{lead.city.lower()}")
    return keys


def _canonical_instagram_username(lead: Lead) -> str:
    if lead.instagram_username:
        return lead.instagram_username.strip().lower().lstrip("@")

    url = (lead.instagram_url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return ""
    return path.split("/", 1)[0].lower().lstrip("@")


def _canonical_domain(url: str) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower().lstrip("www.")


def _pick_better(a: Lead, b: Lead) -> Lead:
    score_a = _completeness_score(a)
    score_b = _completeness_score(b)
    return a if score_a >= score_b else b


def _merge_leads(a: Lead, b: Lead) -> Lead:
    primary = _pick_better(a, b)
    secondary = b if primary is a else a

    for field in Lead.__dataclass_fields__.keys():
        primary_value = getattr(primary, field)
        secondary_value = getattr(secondary, field)

        if isinstance(primary_value, list):
            merged_list = list(dict.fromkeys([*primary_value, *secondary_value]))
            setattr(primary, field, [item for item in merged_list if item])
            continue

        if isinstance(primary_value, dict):
            merged_dict = dict(secondary_value)
            merged_dict.update(primary_value)
            setattr(primary, field, merged_dict)
            continue

        if not primary_value and secondary_value:
            setattr(primary, field, secondary_value)

    if primary.lead_score < secondary.lead_score:
        primary.lead_score = secondary.lead_score
        primary.lead_tier = secondary.lead_tier

    return primary


def _completeness_score(lead: Lead) -> int:
    score = 0
    for field in [lead.email, lead.website, lead.instagram_url, lead.contact_name, lead.specialty, lead.booking_link]:
        if field:
            score += 1
    if _canonical_instagram_username(lead):
        score += 2
    score += min(lead.followers // 1000, 3)
    return score
