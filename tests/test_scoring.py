from models.lead import Lead
from scoring.lead_scorer import score_lead


def test_score_lead_assigns_hot_tier_for_strong_lead() -> None:
    lead = Lead(
        email="hello@example.com",
        email_status="valid",
        email_source="website",
        country="US",
        ai_icp_match="yes",
        website="https://coach.example.com",
        booking_link="https://calendly.com/coach",
        phone="555-555-5555",
        instagram_url="https://instagram.com/coach",
        offers_online_coaching="yes",
        has_pricing_page=True,
        has_testimonials=True,
        has_lead_magnet=True,
        followers=12000,
        weakness="No funnel optimization",
        services_found=["online coaching", "nutrition coaching"],
    )

    score_lead(lead)

    assert lead.lead_score >= 65
    assert lead.lead_tier == "hot"


def test_score_lead_keeps_weak_lead_in_review() -> None:
    lead = Lead(
        country="US",
        ai_icp_match="uncertain",
        followers=0,
    )

    score_lead(lead)

    assert lead.lead_score < 45
    assert lead.lead_tier == "review"
