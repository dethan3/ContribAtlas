# ContribAtlas

**Turn GitHub activity into structured contribution data.**

ContribAtlas is a deterministic CLI that collects and structures a GitHub user's recent open-source contribution activity. The first version deliberately uses **no LLM**: GitHub data collection, normalization, classification, aggregation, percentages, and exports are all handled by ordinary code.

The resulting JSON is designed to be a stable input for a separate LLM reporting layer later.

## What it measures

For an inclusive UTC date range of 1–180 days:

- authored commits;
- pull requests opened;
- pull requests merged;
- issues opened;
- issues closed;
- unique repositories involved;
- owned versus external repository activity;
- activity-action percentages;
- deterministic commit categories based on Conventional Commit prefixes;
- repository primary-language activity share;
- data completeness and search truncation metadata.

A lifecycle object may produce more than one action. For example, a PR opened and merged in the period contributes one `pull_requests_opened` action and one `pull_requests_merged` action. The report also exposes deduplicated PR and issue object counts.

## Why Python

This project is primarily a data collection and transformation pipeline. Python keeps the CLI small, makes JSON/data processing straightforward, and leaves a clean path for later analytics or LLM integrations without coupling them to the collector.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Authentication

Public data works without authentication, but GitHub applies a much lower unauthenticated rate limit. Set one of these environment variables for normal use:

```bash
export GITHUB_TOKEN="your_token"
# or
export GH_TOKEN="your_token"
```

The token is read only from the environment; it is not accepted as a CLI argument to reduce accidental shell-history exposure.

## Usage

General form:

```bash
catlas analyze [github_id] --days [time]
```

Parameters:

- `[github_id]`: the GitHub username/login to analyze, for example `dethan3`. Use the account ID that appears in a profile URL such as `github.com/dethan3`.
- `[time]`: the lookback period. **Currently this is an integer number of days only**, from `1` to `180`. Hours (`12h`) and weeks (`2w`) are not currently accepted; use the equivalent number of days instead.

Example:

```bash
catlas analyze dethan3 --days 7
```

Options:

```text
--days 1..180
--output-dir PATH
--format json|markdown|both
--max-items 1..1000
--no-repo-enrichment
--api-base-url URL
```

A more complete example:

```bash
catlas analyze dethan3 \
  --days 30 \
  --format both \
  --output-dir output
```

Outputs:

```text
output/
├── dethan3-2026-07-09-2026-08-07.json
└── dethan3-2026-07-09-2026-08-07.md
```

## JSON contract

The top-level schema is versioned, with a machine-readable contract at `schemas/report.schema.json`:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-08-07T07:00:00+00:00",
  "period": {},
  "user": {},
  "summary": {},
  "distributions": {},
  "repositories": [],
  "records": {},
  "data_quality": {}
}
```

This separation is intentional:

```text
GitHub API
    ↓
collector + normalizer
    ↓
structured JSON facts
    ↓
optional LLM summarizer (future, separate package/service)
```

## Deterministic commit classification

The classifier maps Conventional Commit prefixes:

| Prefix | Category |
|---|---|
| `feat` | feature |
| `fix` | fix |
| `perf` | performance |
| `test` | test |
| `docs` | documentation |
| `ci` | ci |
| `refactor` | refactor |
| `build` | build |
| `chore` | chore |
| `style` | style |
| `revert` | revert |
| merge commits | merge |
| everything else | other |

No semantic claim is made beyond those visible rules.

## Data limitations

- GitHub Search exposes at most 1,000 results for a single query. Every report includes truncation metadata.
- Private contributions require a token with access to the relevant repositories.
- Repository language share uses GitHub's primary repository language weighted by activity actions. It is not a line-of-code language breakdown.
- Commit attribution follows GitHub's commit search and therefore depends on GitHub's author identity matching.
- Search endpoints have a separate, more restrictive rate limit than ordinary REST endpoints.

## Tests

```bash
ruff check .
pytest
```

## Planned next steps

1. Add response caching and incremental refresh.
2. Add review/comment participation metrics.
3. Add JSON Schema compatibility tests and migration tooling.
4. Build a separate optional LLM summary layer that consumes the report JSON only.
5. Add a small web/API surface after the CLI contract stabilizes.

## License

MIT
