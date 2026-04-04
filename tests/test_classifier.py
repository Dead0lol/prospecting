import json

from enrichment import ai_classifier
from models.lead import Lead


def test_heuristic_classify_detects_established_online_coach_signals() -> None:
    lead = Lead(
        website_title="Sarah Jones | Online Fitness Coach for Women",
        website_description="1:1 online coaching for busy women who want fat loss results.",
        services_found=["online coaching", "fat loss"],
        has_testimonials=True,
        has_pricing_page=True,
        booking_link="https://calendly.com/sarah/apply",
        followers=8_500,
    )

    result = ai_classifier.heuristic_classify(lead)

    assert result["is_solo_online_coach"] == "yes"
    assert result["specialty"] == "fat loss"
    assert result["offer_type"] == "1:1"
    assert result["maturity"] == "established"
    assert "lead magnet" in result["weakness"].lower()
    assert "online coaching" in result["outreach_angle"].lower()
    assert "top-of-funnel" in result["personalization_note"].lower()


def test_heuristic_classify_marks_scaled_when_followers_are_high() -> None:
    lead = Lead(
        website_title="Jordan Lee Fitness",
        website_description="Online coaching and macro coaching for men.",
        followers=20_500,
    )

    result = ai_classifier.heuristic_classify(lead)

    assert result["is_solo_online_coach"] == "yes"
    assert result["maturity"] == "scaled"


def test_classify_lead_uses_openrouter_when_enabled(monkeypatch) -> None:
    captured = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "is_solo_online_coach": "yes",
                                        "specialty": "macro coaching",
                                        "country": "CA",
                                        "city": "Toronto",
                                        "offer_type": "1:1",
                                        "maturity": "scaled",
                                        "weakness": "No lead magnet.",
                                        "outreach_angle": "Tighten conversion funnel.",
                                        "personalization_note": "Strong audience and clear offer.",
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def _mock_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr(ai_classifier.settings, "enable_ai", True)
    monkeypatch.setattr(ai_classifier.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        ai_classifier.settings, "openrouter_model", "openai/gpt-4o-mini"
    )
    monkeypatch.setattr(ai_classifier.settings, "openrouter_delay_seconds", 0)
    monkeypatch.setattr(ai_classifier.request, "urlopen", _mock_urlopen)

    result = ai_classifier.classify_lead(
        Lead(
            website_title="Coach Example",
            website_description="Online fitness coach",
            services_found=["online coaching"],
        )
    )

    assert captured["url"] == ai_classifier.OPENROUTER_URL
    assert captured["timeout"] == ai_classifier.settings.request_timeout_seconds
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["body"]["model"] == "openai/gpt-4o-mini"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert result["specialty"] == "macro coaching"
    assert result["city"] == "Toronto"


def test_classify_lead_falls_back_to_heuristic_when_openrouter_errors(
    monkeypatch,
) -> None:
    monkeypatch.setattr(ai_classifier.settings, "enable_ai", True)
    monkeypatch.setattr(ai_classifier.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        ai_classifier.request,
        "urlopen",
        lambda req, timeout: (_ for _ in ()).throw(RuntimeError("network error")),
    )

    lead = Lead(
        website_title="Coach Example",
        website_description="Online fitness coach",
        services_found=["online coaching"],
    )
    result = ai_classifier.classify_lead(lead)

    assert result == ai_classifier.heuristic_classify(lead)
