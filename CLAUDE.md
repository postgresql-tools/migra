# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MigraDiff (package `migradiff`, CLI command `migra`) — an actively maintained fork of the deprecated
`djrobstep/migra`. It compares two PostgreSQL schemas (live connections, `pg_dump -s` files, or a
migrations directory applied to an ephemeral DB) and generates the SQL needed to transform one into
the other.

**Contributing notice:** per `CONTRIBUTION_GUIDE.md` and the README, this repo is not currently
accepting external PRs — keep that in mind if asked to open one.

## Commands

Tests require a live PostgreSQL instance (12+, container uses 16) on `localhost:5432` with trust auth:

```bash
docker compose up -d      # start Postgres for the test suite
docker compose down       # stop it (add -v to wipe the data volume)
```

```bash
make test    # py.test -x -svv --cov-report term-missing --cov migra tests
make lint    # flake8 .   (config in .flake8: ignores E501, W503)
make fmt     # isort . && black .
make clean   # remove .pyc, .cache, build artifacts
```

Run a single test: `pytest tests/test_command_promote.py::test_name -svv`

CI (CircleCI, `.circleci/config.yml`) runs `make lint` then `make test` against Postgres 14 on every
branch, and publishes to PyPI + tags a release from `master`.

## Architecture

### Core diff engine (upstream-derived, keep changes surgical)

- `migra/migra.py` — `Migration` class: wraps two `DBInspector`/connection-string/schema-dump sources
  (`schemainspect.get_inspector`), and `add_all_changes()` sequences every category of change
  (schemas, extensions, enums, sequences, triggers, RLS, constraints, indexes, tables, domains,
  privileges, comments, ...) in an order that respects PostgreSQL dependency rules — drops before
  creates, dependents before dependencies. **This ordering is load-bearing**; don't reshuffle it
  without understanding why each step is where it is.
- `migra/changes.py` — `Changes` class plus the `get_*_changes`/`statements_from_differences`
  functions that walk `schemainspect` inspector objects and emit SQL for each object type.
  `util.differences()` is the generic added/removed/modified/unmodified diff primitive everything
  else is built on.
- `migra/statements.py` — `Statements` (a `list` subclass) accumulates generated SQL and refuses to
  render (`.sql`) if any statement contains DROP while `safe=True` (`UnsafeMigrationException`) —
  this is the `--unsafe` flag's underlying gate.
- `migra/db_inspector.py` — lower-level live-DB comparison helpers (table sizes, per-object-type
  compare functions) used mainly by the AI drift/advise features rather than core diffing.

### CLI (`migra/command.py`, the biggest file — ~57KB)

- `parse_args()` defines every flag; `run()`/`_run_inner()` is the dispatch body; `do_command()` is
  the `pyproject.toml` entry point (`migra = 'migra:do_command'`).
- Handles multiple input modes: two DB URLs, `--from-file` (pg_dump output), `--from-migrations-dir`
  (applies migration files to an ephemeral DB — supports Supabase/Flyway/numeric naming, see
  `discover_migration_files`/`apply_migrations`).
- Post-processes raw diff output for safety/UX: destructive-statement detection
  (`_check_for_destructive`), column-rename detection (`detect_column_renames`, vs. a naive
  drop+add), risk classification for `--output json` (`classify_sql_statement`), credential
  redaction in error output (`redact_credentials`).
- `--status`/`--history`/`--promote`/`--record-rollback`/`--apply` etc. talk to `migra/history.py`.

### Migration state tracking (`migra/history.py`)

A `migradiff_history` table (`HISTORY_TABLE`), keyed by a SHA-256 hash of normalized SQL
(`compute_migration_hash`). This is the basis for `--promote` (multi-environment promotion),
`--record-rollback`, and `--apply`. **Important semantic, easy to get backwards**: a plain
`--record-history` (without `--apply`) writes into `dburl_target`'s history table and only means
"this migration was generated/reviewed for that target" — not that it was executed anywhere.
`--apply` (`_apply_migration()` in `command.py`) is the one path that actually executes SQL: it runs
the migration against `dburl_from` (the database being migrated — see the CLI's own help text and
the README's `psql dburl_from < migration.sql` convention) inside a single transaction, and only on
confirmed success does it record history — into `dburl_from`'s table, not `dburl_target`'s. A failed
`--apply` rolls back everything and records nothing. `--apply` is rejected up front (before any
dispatch) when combined with `--from-file` (dburl_from would be an ephemeral throwaway database) or
`--promote` (the chain's from/to direction is not yet reconciled with `--apply`'s execution target).

### AI features (optional extra: `pip install migradiff[ai]`, needs `ANTHROPIC_API_KEY`)

- `migra/ai_explain.py` — one file holding four related-but-distinct features, each with its own
  prompt builder + client class: `AIExplainer` (`--explain`), `AIRollback` (`--rollback`, includes a
  fully deterministic non-AI rollback path in `generate_deterministic_rollback` plus AI-assisted
  reconstruction using `extract_schema_context`), `AIAdvisor` (`--advise`, performance/lock risk),
  `AIGenerator` (`--generate`, plain-English → grounded SQL via `extract_relevant_schema`). Also
  owns API key config (`~/.migradiff` style config dir, `--setup-ai`, `resolve_api_key`,
  `redact_api_key`).
- `migra/ai_drift.py` — `DriftExplainer` (`--explain-drift`): compares two *live* databases (not a
  generated migration) and explains the difference, categorizing BREAKING/WARNING/INFO.
- All AI calls are opt-in per the README's privacy framing ("bring your own API key — no data sent
  to MigraDiff servers"); don't add code paths that phone home elsewhere.

### Tests

- `tests/` mirrors the module layout (`test_ai_explain.py`, `test_command_promote.py`, etc.) and
  needs the live Postgres from `docker compose up -d`.
- `tests/conftest.py` monkey-patches `sqlbag.createdrop` create/drop/exists functions to work
  around a Postgres-specific issue in the upstream `sqlbag` dependency — don't remove this shim
  without checking `sqlbag`'s current behavior.
- `tests/characterization/` is a separate CLI characterization suite (`capture.py`, `scenarios.py`)
  that snapshots CLI behavior for the AI-flag surface, independent of the DB-driven unit tests.
