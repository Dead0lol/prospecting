from extraction.email_extractor import extract_emails, pick_best_email


def test_extract_emails_normalizes_and_deduplicates() -> None:
    text = "Reach HELLO@example.com or hello@example.com and coach@example.org"

    emails = extract_emails(text)

    assert emails == ["coach@example.org", "hello@example.com"]


def test_pick_best_email_prefers_priority_prefix_on_matching_domain() -> None:
    emails = [
        "owner@other.com",
        "coach@fit.example.com",
        "hello@fit.example.com",
        "test@fit.example.com",
    ]

    best = pick_best_email(emails, domain="fit.example.com")

    assert best == "hello@fit.example.com"


def test_pick_best_email_filters_bad_patterns() -> None:
    emails = ["test@example.com", "wordpress@example.com", "real@example.com"]

    best = pick_best_email(emails, domain="example.com")

    assert best == "real@example.com"


def test_extract_emails_filters_vendor_telemetry_addresses() -> None:
    text = """
    Contact hello@coach.example.com
    18d2f96d279149989b95faf0a4b41882@sentry-next.wixpress.com
    alerts@sentry.io
    """

    emails = extract_emails(text)

    assert emails == ["hello@coach.example.com"]


def test_pick_best_email_ignores_vendor_telemetry_fallbacks() -> None:
    emails = [
        "18d2f96d279149989b95faf0a4b41882@sentry-next.wixpress.com",
        "coach@gmail.com",
    ]

    best = pick_best_email(emails)

    assert best == "coach@gmail.com"
