from datetime import datetime, timedelta, timezone
import json

from models.lead import Lead
from verification import seen_tracker


class _FakeCachePath:
    def __init__(self, payload: str = "", exists: bool = True) -> None:
        self.payload = payload
        self._exists = exists

    def exists(self) -> bool:
        return self._exists

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.payload

    def write_text(self, payload: str, encoding: str = "utf-8") -> None:
        self.payload = payload
        self._exists = True


def test_load_seen_cache_normalizes_values(monkeypatch) -> None:
    cache_path = _FakeCachePath(
        json.dumps(
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "emails": [" Hello@Example.com ", ""],
                "instagrams": ["@CoachOne", "https://www.instagram.com/CoachTwo/"],
                "domains": ["WWW.Example.com", ""],
            }
        )
    )
    monkeypatch.setattr(seen_tracker, "SEEN_CACHE_PATH", cache_path)

    loaded = seen_tracker._load_seen_cache()

    assert loaded == {
        "emails": {"hello@example.com"},
        "instagrams": {"coachone", "coachtwo"},
        "domains": {"www.example.com"},
    }


def test_load_seen_cache_ignores_expired_entries(monkeypatch) -> None:
    cache_path = _FakeCachePath(
        json.dumps(
            {
                "saved_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                "emails": ["hello@example.com"],
                "instagrams": ["coachone"],
                "domains": ["example.com"],
            }
        )
    )
    monkeypatch.setattr(seen_tracker, "SEEN_CACHE_PATH", cache_path)

    assert seen_tracker._load_seen_cache() is None


def test_remember_and_match_seen_identities(monkeypatch) -> None:
    cache_path = _FakeCachePath("", exists=False)
    monkeypatch.setattr(seen_tracker, "SEEN_CACHE_PATH", cache_path)

    seen = seen_tracker._empty_seen()
    lead = Lead(
        email="HELLO@example.com",
        instagram_url="https://www.instagram.com/CoachOne/",
        website="https://www.CoachExample.com/about",
        source_url="https://linktr.ee/coachone",
    )

    seen_tracker.remember_lead_identities(lead, seen)

    assert "hello@example.com" in seen["emails"]
    assert "coachone" in seen["instagrams"]
    assert "coachexample.com" in seen["domains"]
    assert "linktr.ee" in seen["domains"]
    assert seen_tracker.is_seen_lead(
        Lead(
            email="hello@example.com",
            instagram_username="@coachone",
            website="https://coachexample.com",
        ),
        seen,
    )
