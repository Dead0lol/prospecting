from models.lead import Lead
from verification.deduplicator import deduplicate_leads


def test_deduplicate_leads_merges_matching_email_and_preserves_best_fields() -> None:
    first = Lead(
        business_name="Coach One",
        email="hello@example.com",
        website="https://coach.example.com",
        services_found=["online coaching"],
        notes=["from_website"],
        lead_score=55,
        lead_tier="good",
    )
    second = Lead(
        business_name="Coach One",
        email="hello@example.com",
        instagram_url="https://instagram.com/coachone/",
        contact_name="Alex Coach",
        services_found=["nutrition coaching"],
        notes=["from_instagram"],
        lead_score=72,
        lead_tier="hot",
    )

    leads = deduplicate_leads([first, second])

    assert len(leads) == 1
    merged = leads[0]
    assert merged.email == "hello@example.com"
    assert merged.website == "https://coach.example.com"
    assert merged.instagram_url == "https://instagram.com/coachone/"
    assert merged.contact_name == "Alex Coach"
    assert merged.lead_score == 72
    assert merged.lead_tier == "hot"
    assert set(merged.services_found) == {"online coaching", "nutrition coaching"}
    assert set(merged.notes) == {"from_website", "from_instagram"}
