from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contrib_atlas.models import ContributionReport


def write_json(report: ContributionReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown(report: ContributionReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report.to_dict()), encoding="utf-8")


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    period = data["period"]
    user = data["user"]
    distributions = data["distributions"]

    lines = [
        f"# GitHub Contribution Report: {user['login']}",
        "",
        f"Period: **{period['start_date']} → {period['end_date']} (UTC, inclusive)**",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Active repositories | {summary['unique_repositories']} |",
        f"| Commits | {summary['commits']} |",
        f"| Pull requests opened | {summary['pull_requests_opened']} |",
        f"| Pull requests merged | {summary['pull_requests_merged']} |",
        f"| Issues opened | {summary['issues_opened']} |",
        f"| Issues closed | {summary['issues_closed']} |",
        f"| Total activity actions | {summary['total_activity_actions']} |",
        "",
        "## Activity Mix",
        "",
        "| Activity | Count | Share |",
        "|---|---:|---:|",
    ]

    for name, metric in distributions["activity_actions"].items():
        lines.append(
            f"| {_humanize(name)} | {metric['count']} | {metric['percentage']:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Commit Categories",
            "",
            "| Category | Count | Share |",
            "|---|---:|---:|",
        ]
    )
    if distributions["commit_categories"]:
        for name, metric in distributions["commit_categories"].items():
            lines.append(
                f"| {_humanize(name)} | {metric['count']} | {metric['percentage']:.2f}% |"
            )
    else:
        lines.append("| No commits found | 0 | 0.00% |")

    lines.extend(
        [
            "",
            "## Repositories",
            "",
            "| Repository | Ownership | Actions | Commits | PRs opened | PRs merged | Issues opened | Issues closed | Language |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for repository in data["repositories"]:
        lines.append(
            "| [{name}]({url}) | {ownership} | {actions} | {commits} | {pro} | {prm} | {io} | {ic} | {language} |".format(
                name=repository["full_name"],
                url=repository["html_url"],
                ownership=repository["ownership"],
                actions=repository["activity_actions"],
                commits=repository["commits"],
                pro=repository["pull_requests_opened"],
                prm=repository["pull_requests_merged"],
                io=repository["issues_opened"],
                ic=repository["issues_closed"],
                language=repository["primary_language"] or "Unknown",
            )
        )

    lines.extend(
        [
            "",
            "## Data Quality",
            "",
            f"Complete within configured limits: **{'yes' if data['data_quality']['is_complete'] else 'no'}**",
            "",
        ]
    )
    if data["data_quality"]["truncated_searches"]:
        lines.append(
            "Truncated searches: "
            + ", ".join(data["data_quality"]["truncated_searches"])
        )
        lines.append("")

    lines.append(
        "This report is generated deterministically from GitHub data. No LLM is used."
    )
    lines.append("")
    return "\n".join(lines)


def _humanize(value: str) -> str:
    return value.replace("_", " ").title()
