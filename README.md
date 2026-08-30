# MigraDiff

<div align="center">

**Choose a language:**  
[English](README.md) | 
[हिन्दी](README.hi.md) | 
[中文](README.zh.md) | 
[日本語](README.ja.md) | 
[Français](README.fr.md) | 
[Deutsch](README.de.md) | 
[עברית](README.he.md)

</div>

---

# migra — PostgreSQL Schema Diff Tool

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**The actively maintained fork of [djrobstep/migra](https://github.com/djrobstep/migra).**

migra compares two PostgreSQL database schemas and generates the SQL
migration script needed to transform one into the other. Drop it into
your CI pipeline and stop writing `ALTER TABLE` by hand.

---

## Why This Fork

The original `migra` was officially deprecated in 2024. This fork picks
up where it left off — fixing known issues, adding Python 3.12+ support,
and extending coverage for advanced PostgreSQL features.

If you were using `djrobstep/migra`, this is your drop-in continuation.
Nothing has changed about how the tool works. We're just keeping the
lights on and making it better.

**A note on naming:** This is an independent community fork. The CLI 
command remains `migra` for drop-in backward compatibility with 
existing scripts and pipelines. The package name is `migradiff` to 
distinguish it from the deprecated upstream. If you are looking for 
the original djrobstep/migra, it is archived at 
https://github.com/djrobstep/migra.

---

## Quickstart

### Install

```bash
pip install migradiff
```

Requires Python 3.10+ and a running PostgreSQL instance (12+).

To install from source:

```bash
git clone https://github.com/postgresql-tools/migra
cd migra
pip install -e .
```

> **Note:** PyPI package is available on all releases.

### Basic Usage

Point migra at two database connections and it outputs the DDL needed
to migrate from one to the other:

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

Output is plain SQL — pipe it, review it, apply it:

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### Schema Dumps (No Live Connection Required)

If you can't or don't want to point migra at a live database, use
`pg_dump -s` to generate a schema dump and diff that instead:

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

This is the recommended approach for CI pipelines and security-conscious
environments — no production credentials required.

### Migrations Directory (No Live Branch Database Required)

If your target state is defined by a folder of migration files:

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff applies the migrations to an ephemeral database and diffs the
result. Supports Supabase, Flyway, and standard numeric naming conventions.

### Scoped to a Schema

```bash
# Single schema
migra --schema myschema postgres://db_a postgres://db_b

# Multiple schemas (comma-separated)
migra --schema public,reporting postgres://db_a postgres://db_b
```

### JSON Output

For programmatic consumption or CI pipelines:

```bash
migra --output json postgres://db_a postgres://db_b
```

Output includes per-statement risk classification (`safe`, `warning`,
`destructive`) and a summary with overall risk level.

---

## AI-Powered Explanation (Optional)

MigraDiff can explain any migration in plain English — what each
change does, what risks it carries, and safer alternatives for
destructive operations.

    migra --explain postgres://db_a postgres://db_b

Output:

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

Powered by Claude (Anthropic). Bring your own API key — no data
is sent to MigraDiff servers.

### Setup

Install the AI extras:

    pip install migradiff[ai]

Configure your API key once:

    migra --setup-ai

Or set the environment variable:

    export ANTHROPIC_API_KEY=sk-ant-...

Get an API key at https://console.anthropic.com

### AI Rollback Generation (--rollback)

Generate the exact reverse migration — the SQL needed to undo
any migration:

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff uses your source schema context to reconstruct DROP
TABLE and DROP COLUMN reversals accurately. Non-reversible
operations (TRUNCATE, bulk DELETE) are flagged explicitly.

Combine with --explain for a complete picture:

    migra --explain --rollback postgres://db_a postgres://db_b

Requires `pip install migradiff[ai]` and an Anthropic API key.

### AI Schema Drift Analysis (--explain-drift)

Compare two live PostgreSQL databases and get an AI-powered
explanation of their differences — ideal for answering "What
changed in production?":

    migra --explain-drift \
        --from-db "postgresql://user:pass@old.example.com/db" \
        --to-db "postgresql://user:pass@prod.example.com/db"

Output categorizes each change as BREAKING, WARNING, or INFO,
and includes live table sizes for risk assessment:

    Schema Drift Analysis: old → prod

    Changes Detected:

    1. Table "users" — DROPPED
       - Columns: id, email, created_at

    2. Table "accounts" — MODIFIED
       - Column "status" type changed: VARCHAR → ENUM
       - New column: "last_login_at"

    Risk Analysis:
    - BREAKING: "users" table was dropped. Historical data loss.
    - INFO: New "accounts.last_login_at" column. No migration needed.

Requires `pip install migradiff[ai]` and an Anthropic API key.

### AI Performance Advisor (--advise)

Before applying any migration, get a performance risk assessment
— locking behavior, table rewrite risk, and zero-downtime
alternatives:

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff analyzes each statement for PostgreSQL-specific risks:
table locks, full rewrites, irreversible data loss. When a live
connection is provided, table row counts are used to estimate
lock duration at your actual data scale.

Combine all three AI features for a complete picture:

    migra --explain --advise --rollback postgres://db_a postgres://db_b

Requires pip install migradiff[ai] and an Anthropic API key.

### AI Migration Generator (--generate)

Describe what you want in plain English — MigraDiff generates
the migration SQL grounded in your actual schema:

    migra --generate "add email verification to users table" \
      postgres://db_production

Unlike generic AI tools, MigraDiff knows your real table names,
column types, and constraints — no hallucinated column names or
wrong types.

Generate and immediately review the risk:

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

Requires pip install migradiff[ai] and an Anthropic API key.

---

## Migration State Tracking

MigraDiff now includes a migration state tracking system that records
generated migrations in a `migradiff_history` table in your target
databases. This is the foundation for multi-environment promotion and
rollback tracking.

### ⚠ Known Limitation

Without `--apply` (below), `migradiff_history` only records that a
migration was **generated/reviewed** for a target database, not that the
SQL was necessarily *executed*. If you generate SQL and pipe it to `psql`
yourself, calling `migra --record-history` only tells MigraDiff "this
migration was proposed" — it has no way to know whether your `psql` step
actually succeeded. Use `--apply` when you want MigraDiff itself to run
the migration and only record history on confirmed success.

Be explicit about this in your pipeline so you don't assume false
guarantees about whether a migration has actually been applied.

### View Migration History

```bash
# Show recent history (last 10 entries)
migra --status postgres://db_target

# Show full history
migra --history postgres://db_target
```

Output includes:
- **Hash** (short, 8 chars) — identifies the migration
- **Name** — optional human label
- **Applied At** — when the migration was generated/recorded
- **Applied By** — database user who recorded it
- **Rollback** — rollback status (ROLLED BACK, ROLLBACK FAILED, or -)

JSON output is supported:

```bash
migra --status postgres://db_target --output json
```

### Record Migration History

After generating a migration diff, record it in the target database:

```bash
migra --record-history postgres://db_target_a postgres://db_target_b
```

This calls `ensure_history_table()` and inserts a row with the
generated SQL hash, the forward SQL, and an optional environment label.

Use `--env-label` to tag the entry:

```bash
migra --record-history --env-label staging postgres://db_a postgres://db_b
```

### Applying Migrations (`--apply`)

`--apply` executes the generated migration directly against `dburl_from`
(the first positional argument — "the database you want to migrate", same
database the README's basic usage example pipes to `psql`) instead of only
printing it:

```bash
migra --apply postgres://db_production postgres://db_branch
```

On success, MigraDiff automatically records the migration in
`dburl_from`'s `migradiff_history` table — you don't need to also pass
`--record-history`. If any statement fails, the whole migration is rolled
back as a single transaction (nothing is partially applied) and **nothing
is recorded**, since it wasn't actually applied. The command exits non-zero
(exit code 4) so pipelines can detect the failure.

```bash
migra --apply --env-label prod postgres://db_production postgres://db_branch
```

`--apply` respects the same safety gates as everything else: destructive
statements are blocked unless `--force-destructive` (or `--unsafe`) is
given, and the block happens *before* anything is executed.

`--apply` is not supported with `--from-file` (there's no live database to
apply to — the schema files get loaded into temporary throwaway databases)
or with `--promote` (not implemented yet).

### Multi-Environment Promotion (`--promote`)

`--promote` generates migrations along a chain of environments, with
conflict detection at each hop:

```bash
migra --unsafe --promote dev:staging:prod
```

This:
1. Connects to dev, staging, and prod
2. Verifies staging's `migradiff_history` is a subset of dev's
   (no unknown migrations in staging)
3. Generates the `dev → staging` diff and prints it
4. Generates the `staging → prod` diff and prints it
5. If `--record-history` is also given, records each hop against
   the target environment's history table

Environment names are resolved from
`~/.config/migradiff/environments.json`:

```json
{
    "dev": "postgresql://localhost/dev",
    "staging": "postgresql://staging.example.com/db",
    "prod": "postgresql://prod.example.com/db"
}
```

You can also mix aliases with literal URLs:

```bash
migra --promote dev:postgresql://custom-host/db:prod
```

Conflict example — if staging has a migration that dev doesn't:

```
MigraDiff: CONFLICT in promotion chain postgres://dev → postgres://staging
  postgres://staging has migrations not found in postgres://dev:
    abc1234deadbeef
  Resolve the conflict before continuing the chain.
```

If two adjacent environments already match:

```
No changes needed: postgres://dev → postgres://staging
```

`--promote` composes with `--explain`, `--rollback`, `--advise`,
`--force-destructive`, and `--output json` the same way a normal
two-argument diff does.

### Rollback Tracking (`--record-rollback`)

After executing a rollback, record it to close the audit loop:

```bash
migra --record-rollback <migration_hash_or_file> postgres://db_target
```

You can also mark a rollback as failed:

```bash
migra --record-rollback abc1234 --rollback-status rollback_failed postgres://db_target
```

The `--status` and `--history` views then show the rollback state:

```
Hash         Name                 Applied At                 Applied By       Rollback
----------- -------------------- -------------------------- ---------------- --------------------
abc1234      v001_create_users    2026-06-18T12:00:00Z      deploy_bot       ROLLED BACK 2026-06-18T13:00:00Z
```

---

## Development Setup

The test suite requires a running PostgreSQL instance. The easiest
way to get one is via Docker Compose:

```bash
docker compose up -d
```

This starts a Postgres 16 container on localhost:5432 with trust
authentication. No password required.

To stop it:

```bash
docker compose down
```

Data persists between restarts via the `migradiff-pgdata` volume.
To reset completely:

```bash
docker compose down -v
```

---

## Docker

No Python environment? Use the official image:

```bash
docker run --rm ghcr.io/postgresql-tools/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

Add schema diffing to your pull request workflow:

```yaml
- uses: postgresql-tools/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

Fail the build automatically if destructive operations are detected:

```yaml
- uses: postgresql-tools/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

Use schema dump files instead of live connections:

```yaml
- uses: postgresql-tools/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

See [docs/action-usage.md](docs/action-usage.md) for full configuration options.

---

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/postgresql-tools/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

See `pre-commit-config.example.yaml` in the repo root for full
configuration options.

---

## What migra Understands

- Tables, columns, constraints, indexes
- Views and materialized views
- Functions and stored procedures
- Sequences
- Enums, composite types, domains
- Row-Level Security (RLS) policies
- Foreign data wrappers
- Column-level privileges
- Partitioned tables
- Object comments (`COMMENT ON`)

---

## Improvements Over Upstream

| Area | Upstream (deprecated) | This Fork |
|---|---|---|
| Python 3.12+ | Deprecation warnings | Clean — no warnings |
| RLS policies | Partial, equality bug | Full CREATE/DROP, partition support |
| Error messages | Cryptic on unsupported types | Actionable with object name and issue link |
| --schema flag | Edge cases in multi-schema DBs | Comma-separated, cross-schema dependencies resolved |
| pg_dump input | Not supported | First-class `--from-file` mode |
| JSON output | Not supported | `--output json` with risk classification |
| Docker image | None | `ghcr.io/postgresql-tools/migra` |
| GitHub Action | None | `postgresql-tools/migra-action` |
| Pre-commit hook | None | `.pre-commit-hooks.yaml` |
| Dev environment | Manual Docker commands | `docker compose up -d` |
| AI explanation | None | `--explain` flag with Claude — plain English diff explanation, risk analysis, safer alternatives |
| COMMENT ON diffing | Not supported | Full diffing — add/change/remove across all object types |
| AI drift analysis | None | `--explain-drift` — compare two live databases, AI explains differences with risk categorization |

See [CHANGELOG.md](CHANGELOG.md) for the full fix history.

---

## Known Limitations

migra generates the SQL diff — it does not apply it. Review every
generated script before running against production. Destructive
operations (`DROP TABLE`, `DROP COLUMN`) are flagged in JSON output
mode but not blocked in plain SQL mode.

migra requires a live PostgreSQL connection to introspect schemas,
or schema dump files via `--from-file`. It does not parse raw DDL text.

---

## Contributing Notice

Thank you for your interest in this project. Please note that we are
currently not accepting any external code contributions, pull requests,
bug fixes, or feature submissions at this time.

Any pull requests opened will be automatically closed without review.

---

## Licensing

MigraDiff is **free and open source** under the MIT license.

**All features work for everyone.** No paywalls, no code restrictions, no gatekeeping.

### A Quick Story

I spent 8+ years as an engineer at Philips, supporting hospital IT systems that keep patients safe. When the VC who acquired our division let me go, I was 50+ years old in a market where age matters. Finding another job became nearly impossible. I still need to support my family and put food on the table.

That's why MigraDiff exists. I'm building tools that help you, because this is how I stay employed.

### Here's the Ask

**If you're a student, hobbyist, or open source project:** MIT license, free forever. No agreement needed.

**If you're a for-profit company using MigraDiff:** Please sign a Business License Agreement. This isn't about gatekeeping code—every feature stays free, you run it locally, nothing changes for you technically. It's about fairness: if my tool is helping you make money, help me feed my family.

You still own everything. You control your data. You access all features. We're just being transparent about how we sustain development.

I'm not asking for charity. I'm asking for fairness.

[Get a Business License](https://lateos.ai/license) | [View MIT License](LICENSE)

---

## Acknowledgements

This project is a fork of [djrobstep/migra](https://github.com/djrobstep/migra),
created and originally maintained by Robert Lechte. The core diffing
engine is his work. We are grateful for it.
