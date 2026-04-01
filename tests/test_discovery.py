from discovery.instagram_parser import parse_followers, parse_ig_snippet
from discovery.web_search import quick_reject_website, split_candidate_urls
from models.lead import Lead
from pipeline import _has_coach_signals


def test_parse_followers_handles_millions_and_thousands() -> None:
    assert parse_followers("1.2M followers") == 1_200_000
    assert parse_followers("10.8K followers") == 10_800
    assert parse_followers("1,234 followers") == 1234


def test_parse_ig_snippet_extracts_name_username_and_followers() -> None:
    candidate = {
        "url": "https://www.instagram.com/alexcoach/",
        "title": "Alex Carter | Online Fitness Coach",
        "body": "535 posts 10.8K followers 173 following DM for online coaching",
    }

    parsed = parse_ig_snippet(candidate)

    assert parsed["instagram_username"] == "alexcoach"
    assert parsed["contact_name"] == "Alex Carter"
    assert parsed["followers"] == 10_800


def test_split_candidate_urls_keeps_instagram_and_accepted_platforms() -> None:
    candidates = [
        {
            "url": "https://www.instagram.com/coachperson/",
            "title": "Coach Person",
            "body": "fitness coach",
        },
        {
            "url": "https://coach.example.com/",
            "title": "Coach Person | Online Coaching",
            "body": "book a call",
        },
        {
            "url": "https://kajabi.com/products/coach-offer",
            "title": "Coach Offer",
            "body": "fitness course",
        },
        {
            "url": "https://reddit.com/r/fitness",
            "title": "thread",
            "body": "discussion",
        },
    ]

    split = split_candidate_urls(candidates)

    assert [item["url"] for item in split["instagram"]] == [
        "https://www.instagram.com/coachperson/"
    ]
    assert [item["url"] for item in split["websites"]] == [
        "https://coach.example.com/",
        "https://kajabi.com/products/coach-offer",
    ]


def test_quick_reject_website_rejects_junk_and_deep_paths() -> None:
    assert quick_reject_website("https://buzzfeed.com/article/coach-list") is True
    assert quick_reject_website("https://coach.example.com/blog/2024/10/post") is True
    assert quick_reject_website("https://coach.example.com/") is False


def test_has_coach_signals_rejects_non_fitness_business_site() -> None:
    lead = Lead(
        email="info@callcenterstudio.com",
        has_pricing_page=True,
        instagram_url="https://www.instagram.com/ccs4cx",
        website_title="User Manual for Call Center Studio - Easy Guide",
        website_description="Access the call center studio user manual for all screens.",
    )

    assert _has_coach_signals(lead) is False
