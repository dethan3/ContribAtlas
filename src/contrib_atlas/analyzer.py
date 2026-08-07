from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import date
from typing import Any

from contrib_atlas.client import unique_by_id
from contrib_atlas.models import CollectionResult, ContributionReport


def _percentages(counter: Counter[str]) -> dict[str, dict[str, float | int]]:
    total = sum(counter.values())
    return {
        key: {
            "count": count,
            "percentage": round((count / total * 100) if total else 0.0, 2),
        }
        for key, count in counter.most_common()
    }


def build_report(
    collection: CollectionResult,
    *,
    start_date: date,
    end_date: date,
    requested_days: int,
) -> ContributionReport:
    unique_prs = unique_by_id(
        [*collection.pull_requests_opened, *collection.pull_requests_merged]
    )
    unique_issues = unique_by_id([*collection.issues_opened, *collection.issues_closed])

    action_counter = Counter(
        {
            "commits": len(collection.commits),
            "pull_requests_opened": len(collection.pull_requests_opened),
            "pull_requests_merged": len(collection.pull_requests_merged),
            "issues_opened": len(collection.issues_opened),
            "issues_closed": len(collection.issues_closed),
        }
    )
    action_counter += Counter()  # Drop zero and negative values from Counter iteration semantics.

    commit_category_counter = Counter(commit.category for commit in collection.commits)

    repo_action_counter: Counter[str] = Counter()
    for record in collection.commits:
        repo_action_counter[record.repository] += 1
    for records in (
        collection.pull_requests_opened,
        collection.pull_requests_merged,
        collection.issues_opened,
        collection.issues_closed,
    ):
        for record in records:
            repo_action_counter[record.repository] += 1

    repo_metadata = {repo.full_name: repo for repo in collection.repositories}
    ownership_counter: Counter[str] = Counter()
    language_counter: Counter[str] = Counter()
    repository_rows: list[dict[str, Any]] = []
    username = collection.user.login.lower()

    repo_commit_counts = Counter(record.repository for record in collection.commits)
    repo_pr_opened_counts = Counter(record.repository for record in collection.pull_requests_opened)
    repo_pr_merged_counts = Counter(record.repository for record in collection.pull_requests_merged)
    repo_issue_opened_counts = Counter(record.repository for record in collection.issues_opened)
    repo_issue_closed_counts = Counter(record.repository for record in collection.issues_closed)

    for full_name, action_count in repo_action_counter.most_common():
        owner = full_name.split("/", 1)[0]
        ownership = "owned" if owner.lower() == username else "external"
        ownership_counter[ownership] += action_count
        metadata = repo_metadata.get(full_name)
        language = metadata.primary_language if metadata else None
        language_counter[language or "Unknown"] += action_count

        repository_rows.append(
            {
                "full_name": full_name,
                "ownership": ownership,
                "activity_actions": action_count,
                "commits": repo_commit_counts[full_name],
                "pull_requests_opened": repo_pr_opened_counts[full_name],
                "pull_requests_merged": repo_pr_merged_counts[full_name],
                "issues_opened": repo_issue_opened_counts[full_name],
                "issues_closed": repo_issue_closed_counts[full_name],
                "primary_language": language,
                "stars": metadata.stars if metadata else None,
                "forks": metadata.forks if metadata else None,
                "is_fork": metadata.is_fork if metadata else None,
                "archived": metadata.archived if metadata else None,
                "html_url": (
                    metadata.html_url
                    if metadata
                    else f"https://github.com/{full_name}"
                ),
            }
        )

    truncated_searches = [
        name for name, meta in collection.search_meta.items() if meta.truncated
    ]

    total_actions = sum(action_counter.values())
    total_unique_objects = len(collection.commits) + len(unique_prs) + len(unique_issues)

    return ContributionReport(
        schema_version="1.0",
        generated_at=ContributionReport.generated_now(),
        period={
            "requested_days": requested_days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
            "date_range_semantics": "inclusive UTC calendar dates",
        },
        user=asdict(collection.user),
        summary={
            "unique_repositories": len(repo_action_counter),
            "enriched_repositories": len(collection.repositories),
            "commits": len(collection.commits),
            "merge_commits": sum(commit.is_merge for commit in collection.commits),
            "unique_pull_requests": len(unique_prs),
            "pull_requests_opened": len(collection.pull_requests_opened),
            "pull_requests_merged": len(collection.pull_requests_merged),
            "unique_issues": len(unique_issues),
            "issues_opened": len(collection.issues_opened),
            "issues_closed": len(collection.issues_closed),
            "total_activity_actions": total_actions,
            "total_unique_objects": total_unique_objects,
        },
        distributions={
            "activity_actions": _percentages(action_counter),
            "commit_categories": _percentages(commit_category_counter),
            "repository_activity": _percentages(repo_action_counter),
            "repository_ownership_activity": _percentages(ownership_counter),
            "repository_primary_language_activity": _percentages(language_counter),
        },
        repositories=repository_rows,
        records={
            "commits": [asdict(record) for record in collection.commits],
            "pull_requests_opened": [
                asdict(record) for record in collection.pull_requests_opened
            ],
            "pull_requests_merged": [
                asdict(record) for record in collection.pull_requests_merged
            ],
            "issues_opened": [asdict(record) for record in collection.issues_opened],
            "issues_closed": [asdict(record) for record in collection.issues_closed],
        },
        data_quality={
            "searches": {
                name: asdict(meta) for name, meta in collection.search_meta.items()
            },
            "truncated_searches": truncated_searches,
            "is_complete": not truncated_searches,
            "notes": [
                "GitHub search exposes at most 1,000 results per search query.",
                "Private contributions are visible only when the supplied token can access them.",
                "Language percentages are weighted by activity actions and use each repository's primary language; they are not code-line percentages.",
                "Lifecycle actions are counted separately, so one PR may contribute both an opened and a merged action.",
            ],
        },
    )
