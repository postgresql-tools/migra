# Status

Snapshot of current work-in-progress on this branch. Update as work progresses; this is not a
changelog (see CHANGELOG.md for that).

## Current branch: `feature/apply-flag` (off `main` at `46c2447`)

Migration state tracking (`--status`/`--history`/`--record-history`/`--promote`/
`--record-rollback`) and the CI-trigger/SQLAlchemy-2.x fixes are already merged to `main`
(PRs #8, #9, #10) — see git log, not this file, for that history.

**In progress / uncommitted:**
- Modified: `CHANGELOG.md`, `README.md`, `migra/command.py`, `CLAUDE.md`,
  `PROJECT_PLAN.md`, `PROJECT_PLAN2.md` — new `--apply` flag
- New: `tests/test_command_apply.py`

**What `--apply` does:** executes the generated migration against `dburl_from` in a single
transaction instead of only printing it; on success, automatically records it in `dburl_from`'s
`migradiff_history` table (no need to also pass `--record-history`); on failure, rolls back
everything and records nothing, exits 4. Rejected up front when combined with `--from-file` or
`--promote` — see CLAUDE.md's "Migration state tracking" section for the from/target direction
reasoning.

**Verified 2026-08-08:** 11 new tests pass (including a direct atomicity test against
`_apply_migration()` that forces a mid-migration failure); full suite is 353 passed / 2 skipped,
no regressions; flake8 and black clean; also verified against SQLAlchemy 2.0.51 in an isolated
venv (no other raw-SQL issues found).

**Next steps:** commit, push, open PR. Known follow-up (not done here): reconcile `--promote`'s
from/to direction with `--apply` before wiring the two together (see PROJECT_PLAN.md backlog).
