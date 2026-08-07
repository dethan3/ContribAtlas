from datetime import date

import httpx

from contrib_atlas.client import GitHubClient


def test_search_commits_builds_expected_query_and_parses_pagination() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/search/commits"
        assert "author:octocat" in request.url.params["q"]
        assert "author-date:2026-08-01..2026-08-07" in request.url.params["q"]
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [{"sha": "abc"}],
            },
        )

    transport = httpx.MockTransport(handler)
    with GitHubClient(transport=transport) as client:
        result = client.search_commits(
            "octocat",
            date(2026, 8, 1),
            date(2026, 8, 7),
            max_items=100,
        )

    assert len(requests) == 1
    assert result.meta.total_count == 1
    assert result.meta.retrieved_count == 1
    assert result.meta.truncated is False
