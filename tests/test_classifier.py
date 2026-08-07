import pytest

from contrib_atlas.classifier import classify_commit


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("feat: add analyzer", "feature"),
        ("feat(cli)!: change output schema", "feature"),
        ("fix(api): handle rate limits", "fix"),
        ("perf: reduce requests", "performance"),
        ("test: add fixtures", "test"),
        ("docs: improve README", "documentation"),
        ("ci: run pytest", "ci"),
        ("refactor: split collector", "refactor"),
        ("Merge pull request #12 from user/branch", "merge"),
        ("Revert \"feat: add analyzer\"", "revert"),
        ("Update analyzer behavior", "other"),
        ("", "other"),
    ],
)
def test_classify_commit(message: str, expected: str) -> None:
    assert classify_commit(message) == expected
