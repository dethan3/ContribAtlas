from __future__ import annotations

import re

from contrib_atlas.models import CommitCategory

_CONVENTIONAL_COMMIT = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\([^)]+\))?(?:!)?:\s*",
    flags=re.IGNORECASE,
)

_TYPE_MAP: dict[str, CommitCategory] = {
    "feat": "feature",
    "feature": "feature",
    "fix": "fix",
    "bugfix": "fix",
    "perf": "performance",
    "performance": "performance",
    "test": "test",
    "tests": "test",
    "docs": "documentation",
    "doc": "documentation",
    "ci": "ci",
    "refactor": "refactor",
    "build": "build",
    "chore": "chore",
    "style": "style",
    "revert": "revert",
}


def classify_commit(message: str) -> CommitCategory:
    """Classify a commit message using deterministic, explainable rules."""
    first_line = message.strip().splitlines()[0] if message.strip() else ""
    lowered = first_line.lower()

    if lowered.startswith("merge ") or lowered.startswith("merge pull request"):
        return "merge"

    match = _CONVENTIONAL_COMMIT.match(first_line)
    if match:
        return _TYPE_MAP.get(match.group("type").lower(), "other")

    if lowered.startswith("revert "):
        return "revert"
    return "other"
