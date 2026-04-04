"""Tests for individual_search module."""

from discovery import individual_search


def test_search_individual_query_returns_ddg_results(monkeypatch) -> None:
    """Test that search_individual_query returns DuckDuckGo results."""
    monkeypatch.setattr(
        individual_search,
        "search_query",
        lambda query, max_results=None: [
            {
                "query": query,
                "url": "https://coach.example.com",
                "title": "Coach",
                "body": "Coach body",
            }
        ],
    )

    hits = individual_search.search_individual_query("alex coach", max_results=3)

    assert hits == [
        {
            "query": "alex coach",
            "url": "https://coach.example.com",
            "title": "Coach",
            "body": "Coach body",
        }
    ]


def test_search_individual_query_retries_with_quotes_on_empty_results(
    monkeypatch,
) -> None:
    """Test that search retries with quoted query when first attempt returns nothing."""
    call_count = {"count": 0}

    def mock_search(query, max_results=None):
        call_count["count"] += 1
        if call_count["count"] == 1:
            # First call returns nothing
            return []
        # Second call (quoted) returns results
        return [
            {
                "query": query,
                "url": "https://coach.example.com",
                "title": "Coach",
                "body": "Coach body",
            }
        ]

    monkeypatch.setattr(individual_search, "search_query", mock_search)
    monkeypatch.setattr(individual_search.time, "sleep", lambda x: None)

    hits = individual_search.search_individual_query("alex coach", max_results=3)

    assert call_count["count"] == 2
    assert len(hits) == 1
    # The query should be restored to the original (without quotes)
    assert hits[0]["query"] == "alex coach"


def test_search_individual_query_does_not_retry_if_already_quoted(
    monkeypatch,
) -> None:
    """Test that already-quoted queries don't get double-quoted on retry."""
    call_count = {"count": 0}

    def mock_search(query, max_results=None):
        call_count["count"] += 1
        return []

    monkeypatch.setattr(individual_search, "search_query", mock_search)

    hits = individual_search.search_individual_query('"alex coach"', max_results=3)

    # Should only call once since query is already quoted
    assert call_count["count"] == 1
    assert hits == []


def test_search_individual_query_returns_empty_on_no_results(monkeypatch) -> None:
    """Test that empty results are returned when DDG finds nothing."""
    monkeypatch.setattr(
        individual_search,
        "search_query",
        lambda query, max_results=None: [],
    )
    monkeypatch.setattr(individual_search.time, "sleep", lambda x: None)

    hits = individual_search.search_individual_query(
        "nonexistent coach xyz", max_results=3
    )

    assert hits == []
