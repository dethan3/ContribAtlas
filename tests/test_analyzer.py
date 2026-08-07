from datetime import date

from contrib_atlas.analyzer import build_report
from contrib_atlas.models import (
    CollectionResult,
    CommitRecord,
    IssueRecord,
    PullRequestRecord,
    RepositoryRecord,
    SearchMeta,
    UserProfile,
)


def test_build_report_counts_actions_and_deduplicates_objects() -> None:
    user = UserProfile(
        login="octocat",
        name="Octo Cat",
        bio=None,
        html_url="https://github.com/octocat",
        public_repos=2,
        followers=10,
        created_at="2011-01-01T00:00:00Z",
    )
    commit = CommitRecord(
        sha="abc",
        repository="octocat/demo",
        message="feat: add report",
        authored_at="2026-08-05T00:00:00Z",
        committed_at="2026-08-05T00:00:00Z",
        html_url="https://github.com/octocat/demo/commit/abc",
        category="feature",
        is_merge=False,
    )
    pr = PullRequestRecord(
        id=10,
        number=1,
        repository="octocat/demo",
        title="Add report",
        state="closed",
        created_at="2026-08-04T00:00:00Z",
        closed_at="2026-08-05T00:00:00Z",
        merged_at="2026-08-05T00:00:00Z",
        html_url="https://github.com/octocat/demo/pull/1",
        draft=False,
    )
    issue = IssueRecord(
        id=20,
        number=2,
        repository="other/project",
        title="Document API",
        state="closed",
        created_at="2026-08-03T00:00:00Z",
        closed_at="2026-08-06T00:00:00Z",
        html_url="https://github.com/other/project/issues/2",
        comments=2,
    )
    collection = CollectionResult(
        user=user,
        commits=[commit],
        pull_requests_opened=[pr],
        pull_requests_merged=[pr],
        issues_opened=[issue],
        issues_closed=[issue],
        repositories=[
            RepositoryRecord(
                full_name="octocat/demo",
                owner="octocat",
                name="demo",
                html_url="https://github.com/octocat/demo",
                description=None,
                primary_language="Python",
                stars=3,
                forks=1,
                is_fork=False,
                archived=False,
            )
        ],
        search_meta={
            key: SearchMeta(total_count=1, retrieved_count=1, truncated=False)
            for key in (
                "commits",
                "pull_requests_opened",
                "pull_requests_merged",
                "issues_opened",
                "issues_closed",
            )
        },
    )

    report = build_report(
        collection,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 7),
        requested_days=7,
    )

    assert report.summary["unique_repositories"] == 2
    assert report.summary["total_activity_actions"] == 5
    assert report.summary["total_unique_objects"] == 3
    assert report.summary["unique_pull_requests"] == 1
    assert report.summary["unique_issues"] == 1
    assert report.distributions["commit_categories"]["feature"]["percentage"] == 100.0
    assert report.distributions["repository_ownership_activity"]["owned"]["count"] == 3
    assert report.distributions["repository_ownership_activity"]["external"]["count"] == 2
