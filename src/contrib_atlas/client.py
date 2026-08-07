from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx

from contrib_atlas.classifier import classify_commit
from contrib_atlas.models import (
    CollectionResult,
    CommitRecord,
    IssueRecord,
    PullRequestRecord,
    RepositoryRecord,
    SearchMeta,
    UserProfile,
)

DEFAULT_API_BASE_URL = "https://api.github.com"
DEFAULT_API_VERSION = "2026-03-10"
SEARCH_RESULT_HARD_LIMIT = 1_000


class GitHubAPIError(RuntimeError):
    """A GitHub API request failed."""


@dataclass(frozen=True, slots=True)
class SearchPageResult:
    items: list[dict[str, Any]]
    meta: SearchMeta


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = DEFAULT_API_BASE_URL,
        api_version: str = DEFAULT_API_VERSION,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": api_version,
            "User-Agent": "ContribAtlas/0.1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise GitHubAPIError(f"Unable to reach GitHub: {exc}") from exc

        if response.is_success:
            payload = response.json()
            if not isinstance(payload, dict):
                raise GitHubAPIError(f"Unexpected GitHub response for {path}")
            return payload

        message = "Unknown GitHub API error"
        try:
            body = response.json()
            message = body.get("message", message)
        except ValueError:
            pass

        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")
        rate_note = ""
        if remaining == "0":
            rate_note = f" Rate limit exhausted; reset epoch: {reset or 'unknown'}."

        raise GitHubAPIError(
            f"GitHub API returned {response.status_code}: {message}.{rate_note}"
        )

    def get_user(self, username: str) -> UserProfile:
        data = self._get(f"/users/{username}")
        return UserProfile(
            login=data["login"],
            name=data.get("name"),
            bio=data.get("bio"),
            html_url=data["html_url"],
            public_repos=int(data.get("public_repos", 0)),
            followers=int(data.get("followers", 0)),
            created_at=data["created_at"],
        )

    def _search(
        self,
        path: str,
        *,
        query: str,
        max_items: int,
        sort: str | None = None,
        order: str = "desc",
    ) -> SearchPageResult:
        target = min(max_items, SEARCH_RESULT_HARD_LIMIT)
        page = 1
        items: list[dict[str, Any]] = []
        total_count = 0
        incomplete_results = False

        while len(items) < target:
            per_page = min(100, target - len(items))
            params: dict[str, Any] = {
                "q": query,
                "per_page": per_page,
                "page": page,
                "order": order,
            }
            if sort:
                params["sort"] = sort

            payload = self._get(path, params=params)
            total_count = int(payload.get("total_count", 0))
            incomplete_results = incomplete_results or bool(payload.get("incomplete_results"))
            page_items = payload.get("items", [])
            if not isinstance(page_items, list):
                raise GitHubAPIError(f"Unexpected search result for {path}")
            items.extend(page_items)

            if not page_items or len(page_items) < per_page:
                break
            page += 1

        items = items[:target]
        truncated = incomplete_results or total_count > len(items)
        return SearchPageResult(
            items=items,
            meta=SearchMeta(
                total_count=total_count,
                retrieved_count=len(items),
                truncated=truncated,
            ),
        )

    def search_commits(
        self,
        username: str,
        start_date: date,
        end_date: date,
        *,
        max_items: int,
    ) -> SearchPageResult:
        query = (
            f"author:{username} "
            f"author-date:{start_date.isoformat()}..{end_date.isoformat()}"
        )
        return self._search(
            "/search/commits",
            query=query,
            max_items=max_items,
            sort="author-date",
        )

    def search_issues(
        self,
        username: str,
        start_date: date,
        end_date: date,
        *,
        action: str,
        max_items: int,
    ) -> SearchPageResult:
        if action not in {"created", "closed"}:
            raise ValueError("issue action must be 'created' or 'closed'")
        query = (
            f"is:issue author:{username} "
            f"{action}:{start_date.isoformat()}..{end_date.isoformat()}"
        )
        return self._search(
            "/search/issues",
            query=query,
            max_items=max_items,
            sort="created" if action == "created" else "updated",
        )

    def search_pull_requests(
        self,
        username: str,
        start_date: date,
        end_date: date,
        *,
        action: str,
        max_items: int,
    ) -> SearchPageResult:
        if action not in {"created", "merged"}:
            raise ValueError("pull request action must be 'created' or 'merged'")
        query = (
            f"is:pr author:{username} "
            f"{action}:{start_date.isoformat()}..{end_date.isoformat()}"
        )
        sort = "created" if action == "created" else "updated"
        return self._search(
            "/search/issues",
            query=query,
            max_items=max_items,
            sort=sort,
        )

    def get_repository(self, full_name: str) -> RepositoryRecord:
        data = self._get(f"/repos/{full_name}")
        owner = data.get("owner", {}).get("login") or full_name.split("/", 1)[0]
        return RepositoryRecord(
            full_name=data["full_name"],
            owner=owner,
            name=data["name"],
            html_url=data["html_url"],
            description=data.get("description"),
            primary_language=data.get("language"),
            stars=int(data.get("stargazers_count", 0)),
            forks=int(data.get("forks_count", 0)),
            is_fork=bool(data.get("fork")),
            archived=bool(data.get("archived")),
        )

    def collect(
        self,
        username: str,
        start_date: date,
        end_date: date,
        *,
        max_items: int = SEARCH_RESULT_HARD_LIMIT,
        enrich_repositories: bool = True,
        max_repositories_to_enrich: int = 100,
    ) -> CollectionResult:
        user = self.get_user(username)
        commit_search = self.search_commits(
            username, start_date, end_date, max_items=max_items
        )
        pr_opened_search = self.search_pull_requests(
            username, start_date, end_date, action="created", max_items=max_items
        )
        pr_merged_search = self.search_pull_requests(
            username, start_date, end_date, action="merged", max_items=max_items
        )
        issue_opened_search = self.search_issues(
            username, start_date, end_date, action="created", max_items=max_items
        )
        issue_closed_search = self.search_issues(
            username, start_date, end_date, action="closed", max_items=max_items
        )

        commits = [self._parse_commit(item) for item in commit_search.items]
        prs_opened = [self._parse_pull_request(item) for item in pr_opened_search.items]
        prs_merged = [self._parse_pull_request(item) for item in pr_merged_search.items]
        issues_opened = [self._parse_issue(item) for item in issue_opened_search.items]
        issues_closed = [self._parse_issue(item) for item in issue_closed_search.items]

        repository_names = sorted(
            {
                record.repository
                for record in [
                    *commits,
                    *prs_opened,
                    *prs_merged,
                    *issues_opened,
                    *issues_closed,
                ]
            }
        )
        repositories: list[RepositoryRecord] = []
        if enrich_repositories:
            for full_name in repository_names[:max_repositories_to_enrich]:
                try:
                    repositories.append(self.get_repository(full_name))
                except GitHubAPIError:
                    # Activity remains useful even if one repository disappears or becomes private.
                    continue

        return CollectionResult(
            user=user,
            commits=commits,
            pull_requests_opened=prs_opened,
            pull_requests_merged=prs_merged,
            issues_opened=issues_opened,
            issues_closed=issues_closed,
            repositories=repositories,
            search_meta={
                "commits": commit_search.meta,
                "pull_requests_opened": pr_opened_search.meta,
                "pull_requests_merged": pr_merged_search.meta,
                "issues_opened": issue_opened_search.meta,
                "issues_closed": issue_closed_search.meta,
            },
        )

    @staticmethod
    def _parse_commit(item: dict[str, Any]) -> CommitRecord:
        commit = item.get("commit", {})
        message = commit.get("message", "")
        repository = item.get("repository", {}).get("full_name")
        if not repository:
            repository = _repository_from_api_url(item.get("repository_url", ""))
        first_line = message.strip().splitlines()[0] if message.strip() else ""
        return CommitRecord(
            sha=item["sha"],
            repository=repository,
            message=first_line,
            authored_at=commit.get("author", {}).get("date", ""),
            committed_at=commit.get("committer", {}).get("date", ""),
            html_url=item["html_url"],
            category=classify_commit(message),
            is_merge=first_line.lower().startswith("merge "),
        )

    @staticmethod
    def _parse_pull_request(item: dict[str, Any]) -> PullRequestRecord:
        pull_request = item.get("pull_request", {})
        repository = _repository_from_api_url(item.get("repository_url", ""))
        return PullRequestRecord(
            id=int(item["id"]),
            number=int(item["number"]),
            repository=repository,
            title=item.get("title", ""),
            state=item.get("state", "unknown"),
            created_at=item.get("created_at", ""),
            closed_at=item.get("closed_at"),
            merged_at=pull_request.get("merged_at"),
            html_url=item["html_url"],
            draft=bool(item.get("draft", False)),
        )

    @staticmethod
    def _parse_issue(item: dict[str, Any]) -> IssueRecord:
        repository = _repository_from_api_url(item.get("repository_url", ""))
        return IssueRecord(
            id=int(item["id"]),
            number=int(item["number"]),
            repository=repository,
            title=item.get("title", ""),
            state=item.get("state", "unknown"),
            created_at=item.get("created_at", ""),
            closed_at=item.get("closed_at"),
            html_url=item["html_url"],
            comments=int(item.get("comments", 0)),
        )


def _repository_from_api_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 3 and parts[0] == "repos":
        return f"{parts[1]}/{parts[2]}"
    return "unknown/unknown"


def unique_by_id(records: Iterable[PullRequestRecord | IssueRecord]) -> list[Any]:
    seen: set[int] = set()
    result: list[Any] = []
    for record in records:
        if record.id not in seen:
            seen.add(record.id)
            result.append(record)
    return result
