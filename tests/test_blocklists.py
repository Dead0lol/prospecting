from config import blocklists


def test_canonical_domain_and_domain_matches_handle_subdomains() -> None:
    assert blocklists.canonical_domain("https://www.Coach.Example.com/about") == (
        "coach.example.com"
    )
    assert blocklists.domain_matches("sub.kajabi.com", {"kajabi.com"}) is True
    assert blocklists.domain_matches("coach.example.com", {"kajabi.com"}) is False


def test_blocklist_and_source_domain_helpers_reflect_project_strategy() -> None:
    assert blocklists.is_blocked_domain("reddit.com") is True
    assert blocklists.is_link_hub_domain("linktr.ee") is True
    assert blocklists.is_accepted_source_domain("subdomain.kajabi.com") is True
    assert blocklists.is_non_primary_website_domain("anytimefitness.com") is True
    assert blocklists.is_non_primary_website_domain("coach.example.com") is False
