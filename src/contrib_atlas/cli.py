from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer

from contrib_atlas.analyzer import build_report
from contrib_atlas.client import (
    DEFAULT_API_BASE_URL,
    SEARCH_RESULT_HARD_LIMIT,
    GitHubAPIError,
    GitHubClient,
)
from contrib_atlas.exporter import write_json, write_markdown

app = typer.Typer(
    no_args_is_help=True,
    help="Collect and structure a GitHub user's recent contribution activity.",
)


@app.callback()
def main() -> None:
    """GitHub contribution analytics without an LLM."""


@app.command()
def analyze(
    username: Annotated[str, typer.Argument(help="GitHub username to analyze.")],
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="UTC calendar days to include (1-180)."),
    ] = 30,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for report files."),
    ] = Path("output"),
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output format: json, markdown, or both.",
        ),
    ] = "both",
    max_items: Annotated[
        int,
        typer.Option(
            "--max-items",
            help="Maximum records retrieved per search category (1-1000).",
        ),
    ] = SEARCH_RESULT_HARD_LIMIT,
    no_repo_enrichment: Annotated[
        bool,
        typer.Option(
            "--no-repo-enrichment",
            help="Skip per-repository metadata calls (language, stars, fork status).",
        ),
    ] = False,
    api_base_url: Annotated[
        str,
        typer.Option(
            "--api-base-url",
            help="GitHub API base URL; useful for GitHub Enterprise Server.",
        ),
    ] = DEFAULT_API_BASE_URL,
) -> None:
    """Analyze public activity and export normalized data plus deterministic statistics."""
    if not 1 <= days <= 180:
        raise typer.BadParameter("--days must be between 1 and 180")
    if not 1 <= max_items <= SEARCH_RESULT_HARD_LIMIT:
        raise typer.BadParameter("--max-items must be between 1 and 1000")
    if output_format not in {"json", "markdown", "both"}:
        raise typer.BadParameter("--format must be json, markdown, or both")

    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days - 1)
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    typer.echo(
        f"Analyzing {username} from {start_date.isoformat()} to {end_date.isoformat()}..."
    )
    if not token:
        typer.echo(
            (
                "No GITHUB_TOKEN/GH_TOKEN detected; public data will use GitHub's "
                "lower unauthenticated rate limit."
            ),
            err=True,
        )

    try:
        with GitHubClient(token=token, base_url=api_base_url) as client:
            collection = client.collect(
                username,
                start_date,
                end_date,
                max_items=max_items,
                enrich_repositories=not no_repo_enrichment,
            )
    except GitHubAPIError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    report = build_report(
        collection,
        start_date=start_date,
        end_date=end_date,
        requested_days=days,
    )

    stem = f"{username}-{start_date.isoformat()}-{end_date.isoformat()}"
    written: list[Path] = []
    if output_format in {"json", "both"}:
        json_path = output_dir / f"{stem}.json"
        write_json(report, json_path)
        written.append(json_path)
    if output_format in {"markdown", "both"}:
        markdown_path = output_dir / f"{stem}.md"
        write_markdown(report, markdown_path)
        written.append(markdown_path)

    summary = report.summary
    typer.echo(
        f"Found {summary['total_activity_actions']} activity actions across "
        f"{summary['unique_repositories']} repositories."
    )
    for path in written:
        typer.echo(f"Wrote {path}")


if __name__ == "__main__":
    app()
