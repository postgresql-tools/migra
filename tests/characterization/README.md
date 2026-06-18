# CLI Characterization Tests

## What this catches

This suite **pins the current observable CLI output** of
`migra.command.run()` for every AI-powered flag combination, so that
future refactors of `command.py`, `ai_explain.py`, `ai_drift.py`, or
`db_inspector.py` get caught by a diff against a freshly generated
baseline.

It detects **unintentional drift** in:
- Error messages (wording, formatting, exit codes)
- Output format (section headers, JSON structure, spacing)
- Flag interaction (combined `--explain --rollback --advise` output
  shape)

## What this does NOT catch

- **Correctness** — there are no assertions like "the migration SQL
  should contain ALTER TABLE". We only assert "the output changed
  relative to the last CI run".
- **Live API behavior** — Anthropic is fully mocked. Real API changes
  (new response formats, errors) will not be detected here.
- **Postgres behavior** — no real database assertions beyond fixture
  loading (and even that is exercised only in `--from-file` scenarios).

## Why nothing is committed to git

Baseline files (`_artifacts/*.json`) are **generated in CI on every
run** and **compared within that same run**. They are never persisted
to the repository.

This avoids:
- Stale baselines that drift from what the code actually produces
- PR noise from updating golden files on every intentional output
  change
- Repository bloat on a small public project

The trade-off is that comparison is against the **most recent CI run on
the base branch**, not against a curated golden file. If no prior
artifact exists (first run, or expired after 5-day retention), the
comparison step logs a warning and uploads the current run as the new
reference point — it does not fail the build.

## Flag combinations covered

See `tests/characterization/scenarios.py` for the full list. Currently
includes:

| Category | Scenarios |
|----------|-----------|
| Error paths | Each AI flag (`--explain`, `--rollback`, `--advise`, `--generate`, `--explain-drift`) with missing API key |
| Error paths | Each AI flag with missing `anthropic` package (ImportError) |
| Error paths | `--explain-drift` with RuntimeError from mocked Anthropic |
| Empty diff | Each AI flag on identical schemas (via `"EMPTY"` sentinel) |
| Rich output | `--explain`, `--rollback`, `--advise` with `--from-file` and real fixtures |
| JSON output | `--explain --output json` with both empty and real diff |
| Combined flags | `--explain --rollback --advise` together |
| Generate | `--generate` with and without `--from-file` schema context |

## How to read the CI job summary

When the `characterize` CI job runs, it:

1. **Phase A**: Runs every scenario, captures stdout/stderr/status, and
   uploads the JSON artifacts with a 5-day retention.
2. **Phase B**: Downloads the most recent artifact from the base branch
   (`master`), diffs scenario-by-scenario, and writes the result to the
   job summary (visible in the GitHub Actions UI).

The summary table looks like:

```
+--------------------------------+------------------+
| Scenario                       | Result           |
+--------------------------------+------------------+
| explain_no_key                 | MATCH            |
| explain_empty_diff             | DRIFT            |
| explain_with_file_everything   | MATCH            |
| ...                            | ...              |
+--------------------------------+------------------+
Summary: 21 total, 20 match, 1 drift, 0 missing
```

When **DRIFT** is reported, the unified diff for that scenario is
printed in the job logs. You can expand the "Compare against base
branch" step to see exactly which field changed.

## Decision guide for maintainers

### "Drift is fine, ship it"

If the output change is intentional (e.g. you rewrote an error message,
added a new field to JSON output, reformatted a section header), simply
confirm the new output is correct and move on. **There is no baseline
file to update** — the next CI run on `master` will automatically
record the new output as the reference.

### "Drift means a regression"

If the diff reveals an unintended change (e.g. an error message lost
critical information, JSON output dropped a field, a combined flag
stopped printing a section), fix the regression in your branch. The
characterization suite is informational — it does not block merging —
but ignoring it means reviewers won't see a warning on the next PR
either.

### "I want to see what the current output looks like"

Each artifact JSON file is a structured capture of one scenario. You
can download the CI artifact zip from the Actions UI and inspect
individual `*.json` files. The format is:

```json
{
  "name": "explain_empty_diff",
  "args": ["--explain", "EMPTY", "EMPTY"],
  "status": 0,
  "stdout": "...",
  "stderr": "...",
  "description": "..."
}
```

## Upgrade path

If this prove valuable and stable, the team may choose to promote it to
**committed baselines** — check the JSON artifacts into the repo under
`tests/characterization/baselines/` and compare against those instead
of against a CI artifact from the base branch. That would:

- Make drift detection deterministic (same golden file every time)
- Remove the CI artifact download step
- Require intentional updates to baseline files (PR reviewers must
  approve the diff)

The current generate-in-CI approach is intentionally simpler to start
with, avoiding baseline staleness and PR noise until the team has lived
with the suite for a few weeks and trusts the signal.
