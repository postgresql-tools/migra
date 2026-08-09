# Status

Snapshot of current work-in-progress on this branch. Update as work progresses; this is not a
changelog (see CHANGELOG.md for that).

## Current branch: `fix/multi-schema-filtering` (off `main` at `a762dec`)

Migration state tracking, the CI-trigger/SQLAlchemy-2.x fixes, and `--apply` are already merged
to `main` (PRs #8–#11) — see git log, not this file, for that history.

**In progress / uncommitted:**
- Modified: `CHANGELOG.md`, `migra/migra.py`, `migra/util.py`, `tests/test_migra.py`
- New: `tests/FIXTURES/multischema/`, `tests/FIXTURES/exclude_multischema/`

**The bug:** `--schema public,reporting` was documented as supported but silently produced an
empty diff — the raw comma-joined string was passed straight to `schemainspect`, which compares
it for *exact* equality against each object's schema name. Single-schema and no-schema calls were
never affected.

**The fix:** `migra/util.py` gains `parse_schema_arg()`/`filter_inspector_schemas()` (the latter
reuses schemainspect's own `PROPS` list rather than duplicating it, so it stays in sync with
whatever object types schemainspect tracks). `migra/migra.py` gains `_get_inspector()`, wired into
all 5 of `Migration`'s inspector-construction call sites; single/no-schema calls pass straight
through unchanged, only 2+ comma-separated names take the new post-filter path.

**Verified 2026-08-08:** new tests (`test_multischema`, `test_multischema_whitespace_tolerant`,
`test_exclude_multischema`) each include a third, unlisted schema in the fixture to prove
filtering actually excludes it, not just that it happens to work with one schema; also exercises
`Migration.apply()` directly (via `do_fixture_test`'s second half), not just the CLI path. Full
suite: 356 passed / 2 skipped, no regressions. flake8/black clean.

**Next steps:** commit, push, open PR.
