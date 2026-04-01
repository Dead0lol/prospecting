from models.lead import Lead


def test_lead_to_dict_serializes_list_fields() -> None:
    lead = Lead(
        business_name="Coach Example",
        services_found=["online coaching", "nutrition coaching"],
        social_links=["https://instagram.com/coach", "https://youtube.com/@coach"],
        notes=["from_search", "has_pricing"],
    )

    data = lead.to_dict()

    assert data["business_name"] == "Coach Example"
    assert data["services_found"] == "online coaching, nutrition coaching"
    assert (
        data["social_links"]
        == "https://instagram.com/coach, https://youtube.com/@coach"
    )
    assert data["notes"] == "from_search | has_pricing"


def test_lead_defaults_are_safe() -> None:
    lead = Lead()

    assert lead.lead_tier == "review"
    assert lead.email_status == "unknown"
    assert lead.services_found == []
    assert lead.social_links == []
    assert lead.notes == []
    assert isinstance(lead.raw_payload, dict)
