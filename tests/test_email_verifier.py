"""Tests for the unified email verifier."""

from unittest.mock import MagicMock, patch

from verification.disify_client import DisifyResult
from verification import email_verifier


def test_verify_email_returns_missing_for_empty_email() -> None:
    result = email_verifier.verify_email("")
    assert result.status == "missing"

    result = email_verifier.verify_email("no-at-sign")
    assert result.status == "missing"


def test_verify_email_returns_cached_status(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: "valid")

    result = email_verifier.verify_email("cached@example.com")

    assert result.status == "valid"


def test_verify_email_returns_invalid_for_bad_format(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    disify_result = DisifyResult(
        email="bad@",
        format_valid=False,
        dns_valid=False,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=[],
        domain="",
    )
    monkeypatch.setattr(
        email_verifier, "validate_email_domain", lambda email: disify_result
    )

    cached = {}
    monkeypatch.setattr(
        email_verifier,
        "_set_cached",
        lambda email, status, smtp_code=None: cached.setdefault(email, status),
    )

    result = email_verifier.verify_email("bad@")

    assert result.status == "invalid"
    assert result.error == "invalid_format"


def test_verify_email_returns_disposable_for_temp_domains(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    disify_result = DisifyResult(
        email="user@tempmail.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=True,
        is_role_account=False,
        is_free_provider=False,
        mx_records=["mx.tempmail.com"],
        domain="tempmail.com",
    )
    monkeypatch.setattr(
        email_verifier, "validate_email_domain", lambda email: disify_result
    )
    monkeypatch.setattr(
        email_verifier, "_set_cached", lambda email, status, smtp_code=None: None
    )

    result = email_verifier.verify_email("user@tempmail.com")

    assert result.status == "disposable"


def test_verify_email_returns_invalid_for_no_mx(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    disify_result = DisifyResult(
        email="user@nodomain.invalid",
        format_valid=True,
        dns_valid=False,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=[],
        domain="nodomain.invalid",
    )
    monkeypatch.setattr(
        email_verifier, "validate_email_domain", lambda email: disify_result
    )
    monkeypatch.setattr(
        email_verifier, "_set_cached", lambda email, status, smtp_code=None: None
    )

    result = email_verifier.verify_email("user@nodomain.invalid")

    assert result.status == "invalid"
    assert result.error == "no_mx_records"


def test_verify_email_returns_valid_when_smtp_250_and_not_catch_all(
    monkeypatch,
) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    disify_result = DisifyResult(
        email="hello@realcoach.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=["mx.realcoach.com"],
        domain="realcoach.com",
    )
    monkeypatch.setattr(
        email_verifier, "validate_email_domain", lambda email: disify_result
    )
    monkeypatch.setattr(email_verifier, "_smtp_check", lambda email, mx: 250)
    monkeypatch.setattr(
        email_verifier, "_is_catch_all_domain", lambda domain, mx: False
    )
    monkeypatch.setattr(
        email_verifier, "_set_cached", lambda email, status, smtp_code=None: None
    )

    result = email_verifier.verify_email("hello@realcoach.com")

    assert result.status == "valid"
    assert result.smtp_code == 250


def test_verify_email_returns_catch_all_when_domain_accepts_all(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    disify_result = DisifyResult(
        email="anyone@catchall.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=["mx.catchall.com"],
        domain="catchall.com",
    )
    monkeypatch.setattr(
        email_verifier, "validate_email_domain", lambda email: disify_result
    )
    monkeypatch.setattr(email_verifier, "_smtp_check", lambda email, mx: 250)
    monkeypatch.setattr(email_verifier, "_is_catch_all_domain", lambda domain, mx: True)
    monkeypatch.setattr(
        email_verifier, "_set_cached", lambda email, status, smtp_code=None: None
    )

    result = email_verifier.verify_email("anyone@catchall.com")

    assert result.status == "catch-all"


def test_verify_email_returns_invalid_for_smtp_550(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    disify_result = DisifyResult(
        email="nonexistent@example.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=["mx.example.com"],
        domain="example.com",
    )
    monkeypatch.setattr(
        email_verifier, "validate_email_domain", lambda email: disify_result
    )
    monkeypatch.setattr(email_verifier, "_smtp_check", lambda email, mx: 550)
    monkeypatch.setattr(
        email_verifier, "_set_cached", lambda email, status, smtp_code=None: None
    )

    result = email_verifier.verify_email("nonexistent@example.com")

    assert result.status == "invalid"
    assert result.smtp_code == 550


def test_verify_email_returns_risky_on_smtp_error(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    disify_result = DisifyResult(
        email="test@blocked.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=["mx.blocked.com"],
        domain="blocked.com",
    )
    monkeypatch.setattr(
        email_verifier, "validate_email_domain", lambda email: disify_result
    )
    monkeypatch.setattr(
        email_verifier,
        "_smtp_check",
        lambda email, mx: (_ for _ in ()).throw(ConnectionRefusedError("blocked")),
    )
    monkeypatch.setattr(
        email_verifier, "_set_cached", lambda email, status, smtp_code=None: None
    )

    result = email_verifier.verify_email("test@blocked.com")

    assert result.status == "risky"
    assert "smtp_error" in result.error


def test_verify_emails_batch_deduplicates_and_handles_errors(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: None)

    def mock_verify(email: str):
        if email == "boom@example.com":
            raise RuntimeError("verification exploded")
        return email_verifier.VerificationResult(email=email, status="valid")

    monkeypatch.setattr(email_verifier, "verify_email", mock_verify)

    results = email_verifier.verify_emails_batch(
        ["good@example.com", "good@example.com", "boom@example.com"],
        max_workers=2,
    )

    assert results == {
        "good@example.com": "valid",
        "boom@example.com": "risky",
    }


def test_verify_email_address_backward_compat_returns_string(monkeypatch) -> None:
    monkeypatch.setattr(email_verifier, "_get_cached", lambda email: "valid")

    status = email_verifier.verify_email_address("test@example.com")

    assert status == "valid"
    assert isinstance(status, str)
