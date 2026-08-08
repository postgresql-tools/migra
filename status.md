# Status

Snapshot of current work-in-progress on this branch. Update as work progresses; this is not a
changelog (see CHANGELOG.md for that).

## Current branch: `new-feature-6-18-2026`

**In progress / uncommitted:**
- Modified: `CHANGELOG.md`, `README.md`, `migra/command.py` — migration state
  tracking (`--status`/`--history`/`--record-history`/`--promote`/`--record-rollback`)
- New: `LICENSING.md` (unrelated), `migra/history.py`, `tests/test_command_promote.py`,
  `tests/test_command_rollback_tracking.py`, `tests/test_history.py`
- Also uncommitted (not part of this task): `PROJECT_PLAN.md`, `PROJECT_PLAN2.md`
  updated 2026-08-08 to reflect actual shipped state (they were stale, describing
  v1.5.1 as current when v1.7.2 was already released)

**Verified 2026-08-08:** all 32 new tests pass against a real Postgres instance;
full suite is 342 passed / 2 skipped; flake8 and black are clean; CLI smoke-tested
end-to-end (`--status`, `--record-history`, `--promote`, `--record-rollback`
round-tripped correctly). Feature is code-complete.

**Next steps:** merge this branch and release as v1.8.0 (see PROJECT_PLAN.md
"Next Steps" for the follow-on backlog: `--apply`, native `--fail-on-destructive`).
