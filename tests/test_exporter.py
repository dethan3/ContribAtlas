from contrib_atlas.exporter import render_markdown


def test_render_markdown_handles_empty_commit_categories() -> None:
    data = {
        "period": {"start_date": "2026-08-01", "end_date": "2026-08-07"},
        "user": {"login": "octocat"},
        "summary": {
            "unique_repositories": 0,
            "commits": 0,
            "pull_requests_opened": 0,
            "pull_requests_merged": 0,
            "issues_opened": 0,
            "issues_closed": 0,
            "total_activity_actions": 0,
        },
        "distributions": {
            "activity_actions": {},
            "commit_categories": {},
        },
        "repositories": [],
        "data_quality": {"is_complete": True, "truncated_searches": []},
    }

    markdown = render_markdown(data)
    assert "No commits found" in markdown
    assert "No LLM is used" in markdown
