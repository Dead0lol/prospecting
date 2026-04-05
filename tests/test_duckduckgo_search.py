from discovery import duckduckgo_search


def test_build_queries_covers_primary_modifier_instagram_and_platform_lanes() -> None:
    queries = duckduckgo_search.build_queries(
        ["online fitness coach"],
        ["book a call", "work with me"],
        ["kajabi.com"],
    )

    assert queries == [
        '"online fitness coach"',
        '"online fitness coach" "book a call"',
        '"online fitness coach" "work with me"',
        '"online fitness coach" site:instagram.com',
        '"online fitness coach" "book a call" site:instagram.com',
        '"online fitness coach" "work with me" site:instagram.com',
        '"online fitness coach" site:kajabi.com',
    ]


def test_search_query_retries_and_deduplicates_results(monkeypatch) -> None:
    attempts = []

    def _mock_search(query: str, max_results: int, region: str, safesearch: str):
        attempts.append((query, region, safesearch, max_results))
        if len(attempts) == 1:
            raise RuntimeError("temporary DDG failure")
        return [
            {
                "query": query,
                "url": "https://coach.example.com",
                "title": "Coach One",
                "body": "fitness coach",
            },
            {
                "query": query,
                "url": "https://coach.example.com",
                "title": "Coach One duplicate",
                "body": "fitness coach duplicate",
            },
        ]

    monkeypatch.setattr(duckduckgo_search, "_search_ddgs_once", _mock_search)
    monkeypatch.setattr(duckduckgo_search.settings, "discovery_delay_seconds", 0)

    hits = duckduckgo_search.search_query(
        '"online fitness coach" site:instagram.com',
        max_results=5,
    )

    assert [hit["url"] for hit in hits] == ["https://coach.example.com"]
    assert hits[0]["query"] == '"online fitness coach" site:instagram.com'
    assert attempts[0][1:3] == ("us-en", "off")
    assert attempts[1][1:3] == ("wt-wt", "off")


def test_discover_candidates_stops_when_target_reached(monkeypatch) -> None:
    calls = []

    def _mock_search(query: str):
        calls.append(query)
        if query == "q1":
            return [
                {"query": query, "url": "https://coach-a.example.com", "title": "", "body": ""},
                {"query": query, "url": "https://coach-a.example.com", "title": "", "body": ""},
            ]
        if query == "q2":
            return [
                {"query": query, "url": "https://coach-b.example.com", "title": "", "body": ""}
            ]
        raise AssertionError(f"Unexpected query: {query}")

    monkeypatch.setattr(duckduckgo_search, "search_query", _mock_search)
    monkeypatch.setattr(duckduckgo_search.settings, "max_discovery_queries", 10)

    candidates = duckduckgo_search.discover_candidates(["q1", "q2", "q3"], target=2)

    assert [candidate["url"] for candidate in candidates] == [
        "https://coach-a.example.com",
        "https://coach-b.example.com",
    ]
    assert calls == ["q1", "q2"]
