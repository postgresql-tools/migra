# Changelog

## [Unreleased]

### Added

- **Migration state tracking** (`migradiff_history` table):
  - `--status` / `--history` flags to view migration history from a database
  - `--record-history` flag to record generated migrations in the target DB
  - `--env-label` flag to tag history entries with an environment name
  - New module `migra/history.py` with `ensure_history_table()`,
    `record_applied()`, `record_rollback()`, `get_applied_hashes()`,
    `get_history()`, and `compute_migration_hash()`
  - SQLAlchemy Core implementation via `sqlbag`, no new dependencies
- **Multi-environment promotion** (`--promote`):
  - Colon-separated chain of 2+ database URLs or environment aliases
  - Conflict detection at each hop (target must not have hashes source lacks)
  - Composes with `--explain`, `--rollback`, `--advise`, `--force-destructive`
  - Environment aliases resolved from `~/.config/migradiff/environments.json`
  - `--record-history` integration per hop
- **Rollback execution tracking** (`--record-rollback`):
  - Records rollback status (`rolled_back` / `rollback_failed`) in the history table
  - Accepts a migration hash or rollback SQL file path
  - `--rollback-status` flag to mark failed rollback attempts
  - `--status` / `--history` output shows rollback annotations
- **New tests**: `test_history.py`, `test_command_promote.py`,
  `test_command_rollback_tracking.py` — all using real Postgres databases
  (no mocks), covering idempotent table creation, hash normalization,
  conflict detection, empty-diff hops, safe mode, and rollback tracking.

### Notes

- This is the foundational layer for the upcoming "Control Plane" feature set.
- Known limitation: `migradiff_history` records migrations as *generated*,
  not *applied* — see the README "Migration State Tracking" section for details.
- All new features work without AI extras (`anthropic` optional dependency).

## [1.7.2] - 2026-06-08
- Fix: Use PEP 621 [project] table for PyPI metadata (homepage, repository, bug tracker)

## [1.7.1] - 2026-06-08
- Fix: Update PyPI homepage and repository URLs to postgresql-tools/migra

## [1.6.0] — 2026-06-04

### Added

- `--explain-drift` flag: AI-powered schema drift analysis between two
  live PostgreSQL databases; compares tables, columns, types, indexes,
  constraints, views, enums, extensions, functions, and sequences;
  incorporates live table sizes for risk assessment; categorizes each
  change as BREAKING, WARNING, or INFO; powered by Claude Haiku.
- `--from-db` and `--to-db` connection string arguments for drift analysis.
- Database introspection module (`migra/db_inspector.py`) with
  `get_remote_schema()` and `compare_schemas()` for standalone use.
- AI drift explainer class (`migra/ai_drift.py`) following the same
  pattern as existing AI features.
- 60+ new tests for drift analysis, security, and CLI integration.

## [1.5.0] — 2026-06-01

### Added

- Full `COMMENT ON` diffing support — detects added, changed, and
  removed comments on tables, columns, views, materialized views,
  functions, sequences, types, indexes, constraints, and schemas.
- `--from-file` mode automatically includes `COMMENT ON` diffs
  (no additional flags needed).
- `--explain` and `--generate` now use `COMMENT ON` metadata as
  schema context, giving the AI semantic understanding of what
  columns and tables are *for*, not just their types.
- 48 new tests for comment diffing across all object types.

### Notes

- All `COMMENT ON` changes are classified as `safe` risk in
  `--output json` mode (no locks, no rewrites, fully reversible).
- Comments are applied after all structural changes in migration
  output order.

## [1.4.0] - 2026-06-01

### Added
- --generate flag: AI-powered migration generator from plain
  English descriptions; schema-aware using real table names and
  column types from live connection or schema file; safety rules
  refuse bulk destructive descriptions; soft warns on individual
  destructive operations; combinable with --advise for immediate
  risk assessment and --output json
- --advise flag: AI-powered performance risk analysis for any
  migration diff or file; classifies each statement as HIGH,
  MEDIUM, or LOW risk; identifies table locks, rewrites, and
  data loss; suggests zero-downtime safer alternatives;
  uses live table row counts when connection available for
  accurate lock duration estimates; combinable with --explain,
  --rollback, and --output json
- --rollback flag: AI-generated reverse migration for any diff
  or migration file; deterministic reversals for safe operations
  (ADD COLUMN, CREATE INDEX, RENAME COLUMN); AI-reconstructed DDL
  for DROP TABLE and DROP COLUMN using source schema context;
  non-reversible operations (TRUNCATE) flagged explicitly;
  combinable with --explain and --output json

## [1.3.0] - 2026-05-30

### Added
- --explain flag: AI-powered plain English explanation of any
  migration diff, powered by Claude (Anthropic); identifies risks
  and suggests safer alternatives for destructive operations;
  entirely optional — requires pip install migradiff[ai] and an
  Anthropic API key; no data sent to MigraDiff servers
- --setup-ai command: interactive API key setup stored securely
  in ~/.migradiff/config.json (chmod 600); supports CLI flag,
  environment variable, and config file key resolution
- --from-migrations-dir mode: diff a directory of numbered migration
  files against a base schema without requiring a live branch database;
  supports Supabase timestamp format, Flyway versioned format, and
  standard numeric prefixes; files applied in correct numeric sort order

---

## [1.2.0] - 2026-05-29

### Added
- Smart column rename detection: when a DROP COLUMN + ADD COLUMN pair
  of the same type is detected in the same table, MigraDiff prompts
  the user to confirm a rename (ALTER TABLE ... RENAME COLUMN) instead
  of the destructive DROP + ADD path; --rename-columns flag for
  non-interactive rename acceptance; --no-rename-detection to disable
- --safe mode: MigraDiff now halts by default when destructive
  operations are detected (DROP TABLE, DROP COLUMN, DROP TYPE,
  TRUNCATE, type changes requiring cast); use --force-destructive
  to proceed; --unsafe preserved for backward compatibility with
  deprecation warning
- Enum evolution diffing: ALTER TYPE ... ADD VALUE IF NOT EXISTS for
  safe additions; DROP + CREATE for removals and reorders;
  removals classified as destructive in --output json mode
- Composite type diffing: detects field additions, removals, and type
  changes; generates safe drop + create DDL
- Domain diffing: detects constraint and base type changes

### Fixed
- Resolved pre-existing E721 flake8 warning (type comparison)
  in test suite — codebase now has zero flake8 warnings
- Materialized view CREATE statements now generated in correct
  dependency order via topological sort; circular dependencies
  produce a clear error instead of incorrect output

### Changed
- Pinned schemainspect==3.1.1663587362 for reproducible builds and
  test results (upgraded from 3.1.1663480743)

---

## [1.1.0] - 2026-05-29

### Fixed
- Resolved all DeprecationWarning and PendingDeprecationWarning raised
  under Python 3.12+ — replaced schemainspect's deprecated
  pkg_resources.resource_stream with importlib.resources via monkey-patch
- Improved error messages for unsupported object types in
  Changes.__getattr__ — errors now include the triggering object name
  and a link to report the issue
- --schema flag now correctly scopes diffs in multi-schema deployments;
  cross-schema dependency handling improved; unknown schema name now
  returns a clear error message
- RLS policy diffing on partition tables — alter_rls_statement no longer
  raises NotImplementedError on partition children
- Fixed InspectedRowPolicy.__eq__ typo (self.name == self.name →
  self.name == other.name) causing silent incorrect policy comparisons
- Updated test fixtures for schemainspect view column alias changes —
  resolves 6 pre-existing test failures

### Added
- docker-compose.yml for one-command local development environment
  with Postgres 16 and persistent volume
- --from-file mode: diff pg_dump -s schema files directly without
  a live database connection — no production credentials required
- .pre-commit-hooks.yaml: pre-commit hook for local schema drift
  detection
- --output json mode: structured diff output with per-statement risk
  classification (safe / warning / destructive) and summary metadata;
  credentials redacted from connection string fields
- Dockerfile: python:3.12-slim base, non-root user, minimal image size
- action.yml: GitHub Actions action for CI schema drift detection;
  supports connection strings, --from-file mode, JSON output,
  and fail_on_destructive flag

### Known Issues
- SQLAlchemy 2.0 deprecation warning in sqlbag dependency
  (createdrop.py:63) — upstream sqlbag is unmaintained; evaluate
  replacing with direct psycopg2 calls in a future session

---

## [1.0.0] - 2025-08-25
