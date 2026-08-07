from pathlib import Path

from typer.testing import CliRunner

from contrib_atlas.cli import app
from contrib_atlas.models import CollectionResult, SearchMeta, UserProfile


class FakeGitHubClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def __enter__(self) -> "FakeGitHubClient":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def collect(self, *args: object, **kwargs: object) -> CollectionResult:
        return CollectionResult(
            user=UserProfile(
                login="octocat",
                name="Octo Cat",
                bio=None,
                html_url="https://github.com/octocat",
                public_repos=1,
                followers=1,
                created_at="2011-01-01T00:00:00Z",
            ),
            commits=[],
            pull_requests_opened=[],
            pull_requests_merged=[],
            issues_opened=[],
            issues_closed=[],
            repositories=[],
            search_meta={
                name: SearchMeta(total_count=0, retrieved_count=0, truncated=False)
                for name in (
                    "commits",
                    "pull_requests_opened",
                    "pull_requests_merged",
                    "issues_opened",
                    "issues_closed",
                )
            },
        )


def test_cli_writes_json_and_markdown(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("contrib_atlas.cli.GitHubClient", FakeGitHubClient)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["analyze", "octocat", "--days", "7", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert len(list(tmp_path.glob("*.json"))) == 1
    assert len(list(tmp_path.glob("*.md"))) == 1
    assert "Found 0 activity actions" in result.output
