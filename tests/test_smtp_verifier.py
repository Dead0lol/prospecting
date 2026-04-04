from verification import smtp_verifier


def test_verify_email_address_returns_invalid_when_mx_lookup_fails(monkeypatch) -> None:
    cached = {}
    monkeypatch.setattr(smtp_verifier, "_get_cached", lambda email: None)
    monkeypatch.setattr(
        smtp_verifier,
        "_mx_host",
        lambda domain: (_ for _ in ()).throw(RuntimeError("no mx")),
    )
    monkeypatch.setattr(
        smtp_verifier,
        "_set_cached",
        lambda email, status: cached.setdefault(email, status),
    )

    status = smtp_verifier.verify_email_address("hello@example.com")

    assert status == "invalid"
    assert cached == {"hello@example.com": "invalid"}


def test_verify_email_address_returns_catch_all_for_accept_all_domain(monkeypatch) -> None:
    cached = {}
    monkeypatch.setattr(smtp_verifier, "_get_cached", lambda email: None)
    monkeypatch.setattr(smtp_verifier, "_mx_host", lambda domain: "mx.example.com")
    monkeypatch.setattr(smtp_verifier, "_smtp_check", lambda email, mx: 250)
    monkeypatch.setattr(smtp_verifier, "is_catch_all_domain", lambda domain: True)
    monkeypatch.setattr(
        smtp_verifier,
        "_set_cached",
        lambda email, status: cached.setdefault(email, status),
    )

    status = smtp_verifier.verify_email_address("hello@example.com")

    assert status == "catch-all"
    assert cached == {"hello@example.com": "catch-all"}


def test_verify_emails_batch_deduplicates_and_marks_worker_errors_unknown(
    monkeypatch,
) -> None:
    monkeypatch.setattr(smtp_verifier, "_get_cached", lambda email: None)

    def _mock_verify(email: str) -> str:
        if email == "boom@example.com":
            raise RuntimeError("smtp exploded")
        return "valid"

    monkeypatch.setattr(smtp_verifier, "verify_email_address", _mock_verify)

    results = smtp_verifier.verify_emails_batch(
        ["good@example.com", "good@example.com", "boom@example.com"],
        max_workers=2,
    )

    assert results == {
        "good@example.com": "valid",
        "boom@example.com": "unknown",
    }
