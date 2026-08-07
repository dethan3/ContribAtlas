from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

CommitCategory = Literal[
    "feature",
    "fix",
    "performance",
    "test",
    "documentation",
    "ci",
    "refactor",
    "build",
    "chore",
    "style",
    "revert",
    "merge",
    "other",
]


@dataclass(frozen=True, slots=True)
class UserProfile:
    login: str
    name: str | None
    bio: str | None
    html_url: str
    public_repos: int
    followers: int
    created_at: str


@dataclass(frozen=True, slots=True)
class CommitRecord:
    sha: str
    repository: str
    message: str
    authored_at: str
    committed_at: str
    html_url: str
    category: CommitCategory
    is_merge: bool


@dataclass(frozen=True, slots=True)
class PullRequestRecord:
    id: int
    number: int
    repository: str
    title: str
    state: str
    created_at: str
    closed_at: str | None
    merged_at: str | None
    html_url: str
    draft: bool


@dataclass(frozen=True, slots=True)
class IssueRecord:
    id: int
    number: int
    repository: str
    title: str
    state: str
    created_at: str
    closed_at: str | None
    html_url: str
    comments: int


@dataclass(frozen=True, slots=True)
class RepositoryRecord:
    full_name: str
    owner: str
    name: str
    html_url: str
    description: str | None
    primary_language: str | None
    stars: int
    forks: int
    is_fork: bool
    archived: bool


@dataclass(frozen=True, slots=True)
class SearchMeta:
    total_count: int
    retrieved_count: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class CollectionResult:
    user: UserProfile
    commits: list[CommitRecord]
    pull_requests_opened: list[PullRequestRecord]
    pull_requests_merged: list[PullRequestRecord]
    issues_opened: list[IssueRecord]
    issues_closed: list[IssueRecord]
    repositories: list[RepositoryRecord]
    search_meta: dict[str, SearchMeta]


@dataclass(slots=True)
class ContributionReport:
    schema_version: str
    generated_at: str
    period: dict[str, Any]
    user: dict[str, Any]
    summary: dict[str, Any]
    distributions: dict[str, Any]
    repositories: list[dict[str, Any]]
    records: dict[str, list[dict[str, Any]]]
    data_quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def generated_now(cls) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
