"""Tests for Disify API client."""

from unittest.mock import MagicMock, patch

from verification.disify_client import (
    DisifyResult,
    validate_email_domain,
    _get_cached,
    _set_cached,
)


def test_disify_result_is_deliverable_domain_true_when_valid() -> None:
    result = DisifyResult(
        email="test@example.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=["mx.example.com"],
        domain="example.com",
    )
    assert result.is_deliverable_domain is True


def test_disify_result_is_deliverable_domain_false_when_disposable() -> None:
    result = DisifyResult(
        email="test@tempmail.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=True,
        is_role_account=False,
        is_free_provider=False,
        mx_records=["mx.tempmail.com"],
        domain="tempmail.com",
    )
    assert result.is_deliverable_domain is False


def test_disify_result_is_deliverable_domain_false_when_no_dns() -> None:
    result = DisifyResult(
        email="test@invalid.invalid",
        format_valid=True,
        dns_valid=False,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=[],
        domain="invalid.invalid",
    )
    assert result.is_deliverable_domain is False


def test_validate_email_domain_returns_cached_result(monkeypatch) -> None:
    cached = DisifyResult(
        email="cached@example.com",
        format_valid=True,
        dns_valid=True,
        is_disposable=False,
        is_role_account=False,
        is_free_provider=False,
        mx_records=[],
        domain="example.com",
    )
    monkeypatch.setattr("verification.disify_client._get_cached", lambda email: cached)

    result = validate_email_domain("cached@example.com")

    assert result.email == "cached@example.com"
    assert result.format_valid is True


def test_validate_email_domain_calls_api_when_not_cached(monkeypatch) -> None:
    monkeypatch.setattr("verification.disify_client._get_cached", lambda email: None)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "format": True,
        "dns": True,
        "disposable": False,
        "role": True,
        "free": False,
        "domain": "example.com",
        "mx_info": ["mx1.example.com", "mx2.example.com"],
    }
    mock_response.raise_for_status = MagicMock()

    cached_results = []
    monkeypatch.setattr(
        "verification.disify_client._set_cached",
        lambda result: cached_results.append(result),
    )

    with patch("verification.disify_client.requests.get", return_value=mock_response):
        result = validate_email_domain("admin@example.com")

    assert result.email == "admin@example.com"
    assert result.format_valid is True
    assert result.dns_valid is True
    assert result.is_disposable is False
    assert result.is_role_account is True
    assert result.mx_records == ["mx1.example.com", "mx2.example.com"]
    assert len(cached_results) == 1


def test_validate_email_domain_handles_api_error_gracefully(monkeypatch) -> None:
    monkeypatch.setattr("verification.disify_client._get_cached", lambda email: None)
    monkeypatch.setattr("verification.disify_client._set_cached", lambda result: None)

    with patch(
        "verification.disify_client.requests.get",
        side_effect=Exception("API down"),
    ):
        result = validate_email_domain("test@example.com")

    # Should return sensible defaults on error
    assert result.email == "test@example.com"
    assert result.format_valid is True  # basic @ check
    assert result.dns_valid is True  # assume true, let SMTP verify
    assert result.is_disposable is False
    assert result.domain == "example.com"
