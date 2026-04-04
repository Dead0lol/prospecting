from datetime import datetime, timezone

from models.lead import Lead
import pipeline


def test_rotate_queries_uses_saved_offset_and_advances_window(monkeypatch) -> None:
    saved_offsets = []
    monkeypatch.setattr(pipeline, "_load_discovery_offset", lambda total_queries: 2)
    monkeypatch.setattr(
        pipeline,
        "_save_discovery_offset",
        lambda offset, total_queries: saved_offsets.append((offset, total_queries)),
    )

    rotated = pipeline._rotate_queries(["q1", "q2", "q3", "q4"], window=2)

    assert rotated == ["q3", "q4", "q1", "q2"]
    assert saved_offsets == [(4, 4)]


def test_verify_leads_in_batch_marks_missing_and_applies_statuses(monkeypatch) -> None:
    leads = [
        Lead(email="hello@example.com"),
        Lead(email="info@example.com"),
        Lead(),
    ]

    monkeypatch.setattr(
        pipeline,
        "verify_emails_batch",
        lambda emails: {
            "hello@example.com": "valid",
            "info@example.com": "catch-all",
        },
    )

    pipeline.verify_leads_in_batch(leads)

    assert leads[0].email_status == "valid"
    assert leads[1].email_status == "catch-all"
    assert leads[2].email_status == "missing"
    assert leads[0].verified_at
    assert leads[1].verified_at


def test_find_email_for_lead_uses_guesses_when_website_exists(monkeypatch) -> None:
    lead = Lead(
        business_name="Alex Coach",
        contact_name="Alex Carter",
        website="https://coach.example.com",
    )
    monkeypatch.setattr(
        pipeline,
        "guess_emails",
        lambda name, domain: ["hello@coach.example.com"],
    )

    pipeline.find_email_for_lead(lead)

    assert lead.email == "hello@coach.example.com"
    assert lead.email_source == "guessed"


def test_find_website_for_ig_lead_uses_individual_query_search(monkeypatch) -> None:
    lead = Lead(
        contact_name="Alex Carter",
        instagram_username="alexcarterfit",
    )
    calls = []

    def _mock_search(query: str, max_results: int = 5):
        calls.append((query, max_results))
        return [
            {
                "query": query,
                "url": "https://alexcarterfit.com",
                "title": "Alex Carter Fitness",
                "body": "Alex Carter online fitness coach",
            }
        ]

    monkeypatch.setattr(pipeline, "search_individual_query", _mock_search)

    pipeline._find_website_for_ig_lead(lead)

    assert lead.website == "https://alexcarterfit.com"
    assert calls == [("alexcarterfit fitness coach website", 5)]
