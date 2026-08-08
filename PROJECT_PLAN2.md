# MigraDiff Project Plan (Updated)

## Project Overview

**MigraDiff** is an actively maintained fork of djrobstep/migra (PostgreSQL schema diff tool). 

- **Package:** `migradiff` (PyPI)
- **CLI:** `migra` (backward compatible)
- **Repo:** https://github.com/postgresql-tools/migra
- **Maintainer:** Leo (Lateos)
- **License:** MIT

---

## Business Targets

| Metric | Target | Timeline |
|--------|--------|----------|
| **Revenue (ARR)** | $1–2M | Year 1 |
| **Customer Base** | 200–300 customers | Year 1 |
| **Exit** | Supabase/Redgate | Year 2–3 |
| **Exit Value** | $10–20M | Year 2–3 |

---

## Completed Features

### v1.3.0 (Sessions 009–010) — 2026-05-30
- `--explain`: plain-English explanation of migrations
- `--from-migrations-dir`: load migrations from directory

### v1.4.0 (Sessions 011–013) — 2026-06-01
- `--rollback`: generates reversal migration SQL
- `--advise`: deterministic + AI performance/risk assessment
- `--generate`: writes migration SQL from plain-English description

### v1.5.0 (Session 017) — 2026-06-01
- COMMENT ON diffing: detects added/changed/removed comments across all
  object types; automatic in `--from-file` mode; feeds `--explain`/`--generate`
  as schema context. (There is no separate `--comment-on` flag — this runs
  by default; the plan previously described it as a flag, which was wrong.)

### v1.6.0 — 2026-06-04
- `--explain-drift`: AI-powered schema drift analysis between two live
  databases (`--from-db`/`--to-db`), BREAKING/WARNING/INFO categorization,
  live table sizes for risk assessment
- `migra/db_inspector.py`: standalone `get_remote_schema()`/`compare_schemas()`

### v1.7.x — 2026-06-08
- PyPI metadata fixes (PEP 621 `[project]` table, homepage/repo URLs)
- Repo moved from `migradiff/migra` to `postgresql-tools/migra`

### Multi-language docs & licensing (merged pre-1.7.2, docs-only, no version bump)
- README translated into 6 languages (fr, de, ja, zh, hi, he) alongside English
- Licensing section (personal story + Business License ask) added to all READMEs

### Migration state tracking — code-complete, not yet released
- `--status` / `--history`: view migration history from a `migradiff_history` table
- `--record-history` / `--env-label`: record generated migrations against a target DB
- `--promote`: chain migrations across environments (`dev:staging:prod` or
  `~/.config/migradiff/environments.json` aliases) with conflict detection per hop
- `--record-rollback` / `--rollback-status`: close the audit loop on executed rollbacks
- New module `migra/history.py`; 32 new tests (`test_history.py`,
  `test_command_promote.py`, `test_command_rollback_tracking.py`)
- Verified 2026-08-08: all 32 new tests pass against a real Postgres instance,
  full suite (342 tests) passes, flake8/black clean, and the CLI was smoke-tested
  end-to-end (`--status`, `--record-history`, `--promote`, `--record-rollback`
  round-tripped correctly against live databases)
- Documented in CHANGELOG `[Unreleased]` and README's "Migration State Tracking"
  section; sitting uncommitted on branch `new-feature-6-18-2026` — next release
  will be **v1.8.0**

### Infrastructure (Session 018)
- ✅ Production CI/CD pipeline
- ✅ Branch protection on master
- ✅ Automated PyPI releases on tags
- ✅ GitHub Actions workflows (lint + test matrix + coverage)

---

## Current Version

**v1.7.2** (released 2026-06-08 — matches `pyproject.toml` and PyPI)

Migration state tracking (above) is feature-complete and fully tested on
`new-feature-6-18-2026` but not yet merged or released.

Test counts (actual, `pytest tests -q`, excluding the separate
characterization suite): **342 passed, 2 skipped**, verified 2026-08-08.

---

## Free Tier Roadmap

### Shipped: `--explain-drift` (v1.6.0) and multi-language README

Both were originally planned as "Session 019" and "Session 020" — both are
done. See "Completed Features" above for what actually shipped:
`--explain-drift` in v1.6.0 (2026-06-04), and the README translations.

Note: this document originally planned Spanish (README.es.md) instead of
Hindi/Hebrew for the language set — that changed during implementation.
The 6 languages that actually shipped are fr, de, ja, zh, hi, he (no
Spanish); see `PROJECT_PLAN.md` for the corrected rationale.

### Shipped: migration state tracking and `--apply`

`--status`/`--history`/`--promote`/`--record-rollback` merged into `main`
2026-08-08 (PRs #8–#10; no version bump/tag yet — still on v1.7.2).
`--apply` (execute the migration against `dburl_from` instead of only
printing it, with automatic history recording on confirmed success — see
README's "Applying Migrations" section) shipped shortly after on top of
that. Neither has been cut into a tagged release yet; `pyproject.toml`
still reads 1.7.2. Bumping to v1.8.0 and publishing is still outstanding.

### Planned (Backlog)

| Feature | Effort | Value | Notes |
|---------|--------|-------|-------|
| Native `--fail-on-destructive` flag | Low | High | Currently this behavior only exists inside the GitHub Action's `action-entrypoint.sh`. CircleCI/GitLab/pre-commit users have no equivalent without wrapping the CLI themselves. |
| `--apply` + `--promote` | Medium | Medium | `--apply` currently refuses to run when `--promote` is also given — `--promote`'s from/to direction needs to be reconciled with which database `--apply` should actually execute against before this is safe to wire up. |
| `--document` | Medium-High | High | Schema documentation generation |
| Multi-schema hardening | Medium | High | `Migration.__init__` (`migra/migra.py`) still hard-rejects `schema` + `exclude_schema` together; cross-schema FK/dependency ordering in `add_all_changes()` hasn't had a dedicated multi-tenant test pass |
| pgvector support | Low | Medium | Modern Postgres vector types — unconfirmed whether `schemainspect` already round-trips them |
| `--suggest-indexes` | Medium | Medium | AI recommends useful indexes; can reuse `AIAdvisor`'s existing table-stats extraction |
| `--dry-run` | Low | Medium | Preview what `--apply` would do without executing it |

---

## Enterprise Tier (Post v1.6.0)

**Gating:** HMAC-signed license key (`MIGRADIFF-ENT-{base64}-{hmac}`)

### Features (Roadmap)

| Feature | Phase | Timeline | Notes |
|---------|-------|----------|-------|
| Hosted AI key | Phase 1 | Month 2–3 | Users don't manage Anthropic API key |
| Shadow Run | Phase 1 | Month 3–4 | Firecracker microVMs for safe testing |
| Team RBAC | Phase 2 | Month 4–5 | Multiple users, role-based access |
| Audit trail dashboard | Phase 2 | Month 5–6 | Compliance, change history, who-did-what |
| PR comment injection | Phase 2 | Month 6–7 | GitHub App auto-comments on PRs |
| Compliance reporting | Phase 3 | Month 7–8 | SOC 2, audit logs, retention policies |

---

## Free vs Enterprise Split

### **Free Tier (Local, User-Controlled)**
- `--explain` (explain migrations)
- `--rollback` (generate reversals)
- `--advise` (risk assessment)
- `--generate` (write from plain English)
- `--explain-drift` (compare live databases)
- `--document` (schema documentation)
- `--comment-on` (diff annotations)
- pgvector support
- Docker/GitHub Actions/pre-commit integration
- Multi-language README

**Monetization:** Community adoption, word-of-mouth, visibility to Supabase/Redgate

### **Enterprise Tier (Hosted/Managed)**
- Hosted Anthropic API key management
- Shadow Run (safe migration testing in isolated VMs)
- Team RBAC (multiple users, permissions)
- Audit trail dashboard (compliance, history)
- PR comment injection (GitHub App integration)
- Compliance reporting (SOC 2, audit logs)

**Pricing model:** 
- Free: forever
- Team: $299/month (5 users, audit logs, team management)
- Enterprise: custom pricing (large scale, compliance, SLA)

---

## Key Architecture Decisions

### Build System
- Poetry (dependency management)
- Python 3.10+ (floor version)
- setuptools (explicit dependency for schemainspect compatibility)

### AI Features
- Claude Haiku (cost-effective, fast)
- User's own Anthropic API key (free tier)
- Temperature 0 (deterministic outputs)
- Lazy imports (only load when used)

### Data Provenance
- All AI training data pipelines use cryptographic audit traceability
- Content hash (SHA-256), source_url, harvest_timestamp
- HMAC-SHA-256 signed pipeline_manifest.json
- License quarantine file (no split leakage)

### CI/CD
- GitHub Actions (lint, test matrix, coverage)
- Branch protection on `master` (CI required)
- Automated PyPI release on version tags
- Feature branch workflow (always test before merge)

### Database Support
- PostgreSQL 12+ (tested 14, 15, 16, 17)
- schemainspect for schema introspection
- sqlbag for connection management
- No ORM dependency (raw SQL + AST parsing)

---

## Known Limitations

### schemainspect + setuptools dependency
The `schemainspect` package (upstream: djrobstep, unmaintained) uses deprecated `pkg_resources` which requires `setuptools` at runtime. Added as explicit dependency in pyproject.toml.

**Migration path (future):** Replace with maintained schema inspection library or migrate to Rust.

### docker-compose.yml referenced but missing from repo
`README.md`'s "Development Setup" section and the CHANGELOG (v1.1.0 entry)
both reference a `docker-compose.yml` for one-command local Postgres, but
no such file currently exists in the repo root. Verified 2026-08-08 by
spinning up Postgres manually (`docker run postgres:16 ...`) to run the
test suite instead.

---

## Version History

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| v1.1.0 | 2026-05-29 | --from-file, --output json, pre-commit hook |
| v1.2.0 | 2026-05-29 | Column rename detection, --safe/--force-destructive, enum/composite/domain diffing |
| v1.3.0 | 2026-05-30 | --explain, --setup-ai, --from-migrations-dir |
| v1.4.0 | 2026-06-01 | --rollback, --advise, --generate |
| v1.5.0 | 2026-06-01 | COMMENT ON diffing |
| v1.6.0 | 2026-06-04 | --explain-drift |
| v1.7.1 | 2026-06-08 | PyPI homepage/repo URL fix |
| v1.7.2 | 2026-06-08 | PEP 621 metadata fix (current release) |
| v1.8.0 | TBD | Migration state tracking (--status/--history/--promote/--record-rollback) — code-complete, unreleased |

Multi-language READMEs and the Licensing section merged as docs-only PRs
without a dedicated version bump — not tied to a CHANGELOG entry.

---

## Marketing & Positioning

### Free Tier Positioning
"The AI-powered PostgreSQL migration tool that explains, reverses, and predicts risk in real-time."

### Enterprise Positioning
"Safe, auditable database migrations for teams. Compliance-ready. Built for scale."

### Competitive Advantages
1. **AI-native:** Every migration gets explained and risk-assessed
2. **Safe-by-default:** Detects dangerous patterns before deployment
3. **Multi-language:** Explains diffs, docs, and README in 6+ languages
4. **Live database aware:** `--explain-drift` compares reality, not just migrations
5. **Open source:** Free tier drives adoption, enterprise tier funds development

---

## Acquisition Narrative

**For Redgate (Flyway competitor):**
- Redgate owns Flyway (migration tool)
- MigraDiff fills the "schema analysis" gap
- Combined: Flyway migrations + MigraDiff intelligence = best-in-class

**For Supabase (PostgreSQL platform):**
- Supabase sells managed PostgreSQL
- MigraDiff drives migration adoption
- Combined: Supabase + MigraDiff = seamless developer experience

**Valuation basis:**
- v1.6.0: $3–4M ARR → $15–25M exit (3–5x revenue multiple)
- Enterprise adoption (Year 2): $5–8M ARR → $25–40M exit (5–7x multiple)

---

## Success Metrics (OKRs)

### Q2 2026
- ✅ v1.5.0 shipped
- ✅ CI/CD pipeline live
- ✅ v1.6.0 shipped (`--explain-drift`)
- ⏳ 50+ GitHub stars (unverified — outside what a code/repo analysis can confirm)
- ⏳ 1k+ monthly PyPI downloads (unverified — outside what a code/repo analysis can confirm)

### Q3 2026
- ✅ Multi-language README shipped (docs-only PR, no dedicated version bump)
- ⏳ v1.8.0 shipped (migration state tracking — code-complete, awaiting release)
- ⏳ `--document`, pgvector support (not yet started)
- ⏳ 10+ enterprise customers ($30k–$100k MRR) (unverified)
- ⏳ 100+ GitHub stars (unverified)
- ⏳ 5k+ monthly PyPI downloads (unverified)

### Q4 2026
- ⏳ Enterprise tier revenue: $50k/month ARR
- ⏳ Acquisition conversations with Redgate/Supabase
- ⏳ Featured on r/PostgreSQL, HackerNews
- ⏳ 10k+ monthly PyPI downloads

---

## Team & Workload

**Team:** Leo (solo, Lateos founder)

**Time allocation:**
- MigraDiff: 50% (revenue priority)
- npm-scan: 20% (security research)
- Other Lateos projects: 30% (pgAudit, ESLint, WAL-G forks)

**Engineering discipline:**
- Tests first, stop conditions on every prompt
- Three-phase workflow: reproduce → fix → document
- CI/CD validates every change before merge to master
- CLAUDE.md convention anchor for consistency
- Production-grade pipeline: feature branch → PR → CI → merge → release

---

## Next Steps

1. **Cut v1.8.0** — migration state tracking and `--apply` are both merged
   to `main` and fully tested, but `pyproject.toml` is still at 1.7.2 and
   nothing has been tagged/published to PyPI yet.

2. **Native `--fail-on-destructive` CLI flag**
   - Promote the GitHub Action's destructive-detection behavior into
     `command.py` itself so non-Action CI users (CircleCI, GitLab, plain
     scripts) get it too

3. **Reconcile `--promote`'s direction with `--apply`** before wiring the
   two together — see the Planned/Backlog table above.

4. **Post v1.8.0:** Enterprise tier planning
   - Design licensing system
   - Plan hosted features
   - Build enterprise marketing narrative

---

**Document version:** Updated 2026-08-08 (reconciled with actual repo/code state, incl. `--apply`)  
**Last updated by:** Claude (with Leo)  
**Repository:** https://github.com/postgresql-tools/migra
