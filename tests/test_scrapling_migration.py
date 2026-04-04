from typing import Any, Dict, cast

from scrapling.engines.toolbelt.custom import Response

from extraction import linktree_parser, website_crawler
from resolution import link_resolver


def _response(url: str, html: str, status: int = 200) -> Response:
    return Response(
        url=url,
        content=html,
        status=status,
        reason="OK" if status < 400 else "Error",
        cookies={},
        headers={},
        request_headers={},
    )


def test_parse_link_hub_extracts_links_with_scrapling(monkeypatch) -> None:
    html = """
    <html><body>
      <a href="/about">About</a>
      <a href="offers">Offers</a>
      <a href="https://coach.example.com">Site</a>
      <a href="mailto:coach@example.com">Email</a>
    </body></html>
    """
    monkeypatch.setattr(
        linktree_parser.Fetcher,
        "get",
        lambda url, **kwargs: _response(url, html),
    )

    parsed = cast(Dict[str, Any], linktree_parser.parse_link_hub("https://linktr.ee/coach"))

    assert "About" in parsed["text"]
    assert parsed["links"] == [
        "https://coach.example.com",
        "https://linktr.ee/about",
        "https://linktr.ee/offers",
        "mailto:coach@example.com",
    ]


def test_resolve_external_url_uses_scrapling_fetcher(monkeypatch) -> None:
    call_kwargs = {}

    def _mock_get(url, **kwargs):
        call_kwargs.update(kwargs)
        return _response("https://coach.example.com/home", "<html></html>")

    monkeypatch.setattr(
        link_resolver.Fetcher,
        "get",
        _mock_get,
    )

    resolved = link_resolver.resolve_external_url("https://short.url/x")

    assert resolved == {
        "resolved_url": "https://coach.example.com/home",
        "resolved_type": "website",
    }
    assert call_kwargs["follow_redirects"] is True
    assert call_kwargs["headers"]["User-Agent"]
    assert call_kwargs["timeout"] > 0


def test_crawl_website_extracts_core_signals_from_scrapling_response(monkeypatch) -> None:
    html = """
    <html>
      <head>
        <title>Alex Carter | Online Fitness Coach</title>
        <meta name="description" content="Coach Alex helps with online coaching." />
      </head>
      <body>
        Contact us: coach@example.com
        <a href="mailto:hello@example.com">Email</a>
        <a href="https://instagram.com/alexcoach">IG</a>
        <a href="https://calendly.com/alex/book">Book</a>
        <a href="/pricing">Pricing</a>
        <script>pricing hidden in scripts should not be parsed as visible text</script>
        <div>testimonials and client results</div>
        <div>online coaching and nutrition coaching</div>
      </body>
    </html>
    """

    monkeypatch.setattr(website_crawler.settings, "max_pages_per_site", 1)
    monkeypatch.setattr(website_crawler, "_fetch", lambda url: _response(url, html))

    result = cast(Dict[str, Any], website_crawler.crawl_website("https://coach.example.com"))

    assert result["website_title"] == "Alex Carter | Online Fitness Coach"
    assert result["website_description"] == "Coach Alex helps with online coaching."
    assert result["emails"] == ["coach@example.com", "hello@example.com"]
    assert result["socials"]["instagram_url"] == "https://instagram.com/alexcoach"
    assert result["booking_link"] == "https://calendly.com/alex/book"
    assert result["has_pricing_page"] is True
    assert result["has_testimonials"] is True
    assert result["offers_online_coaching"] == "yes"


def test_crawl_website_filters_vendor_telemetry_emails(monkeypatch) -> None:
    html = """
    <html>
      <body>
        hello@coach.example.com
        18d2f96d279149989b95faf0a4b41882@sentry-next.wixpress.com
      </body>
    </html>
    """

    monkeypatch.setattr(website_crawler.settings, "max_pages_per_site", 1)
    monkeypatch.setattr(website_crawler, "_fetch", lambda url: _response(url, html))

    result = cast(
        Dict[str, Any], website_crawler.crawl_website("https://coach.example.com")
    )

    assert result["emails"] == ["hello@coach.example.com"]


def test_crawl_website_resolves_relative_links_from_final_response_url(monkeypatch) -> None:
    html = """
    <html><body>
      <a href="/pricing">Pricing</a>
    </body></html>
    """

    monkeypatch.setattr(website_crawler.settings, "max_pages_per_site", 1)
    monkeypatch.setattr(
        website_crawler,
        "_fetch",
        lambda url: _response("https://coach.example.com/landing/", html),
    )

    result = cast(Dict[str, Any], website_crawler.crawl_website("https://short.url/coach"))

    assert result["pricing_page"] == "https://coach.example.com/pricing"


def test_crawl_website_uses_redirect_target_for_followup_paths(monkeypatch) -> None:
    requested_urls = []

    def _mock_fetch(url: str):
        requested_urls.append(url)
        if url == "https://short.url/coach":
            return _response("https://coach.example.com/landing/", "<html></html>")
        if url == "https://coach.example.com/about":
            return _response(url, "<html></html>")
        raise AssertionError(f"Unexpected fetch URL: {url}")

    monkeypatch.setattr(website_crawler.settings, "max_pages_per_site", 2)
    monkeypatch.setattr(website_crawler, "_fetch", _mock_fetch)

    result = cast(Dict[str, Any], website_crawler.crawl_website("https://short.url/coach"))

    assert requested_urls == [
        "https://short.url/coach",
        "https://coach.example.com/about",
    ]
    assert result["website"] == "https://coach.example.com/landing/"
