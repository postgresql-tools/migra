# CI/CD Notes

## Known Limitations

### schemainspect + setuptools dependency

The `schemainspect` package (a dependency for PostgreSQL introspection) 
uses deprecated `pkg_resources` from `setuptools`. This creates an import-time 
dependency that requires `setuptools` to be available at Python runtime.

**Impact:** GitHub Actions CI requires explicit setuptools installation steps.

**Mitigation:** Added `setuptools` to pyproject.toml dependencies and 
CI workflow installs it before running tests.

**Background:** schemainspect is unmaintained by upstream (djrobstep). 
A future migration to a maintained schema inspection library would resolve this.

### PostgreSQL 17 view definition qualifiers

PostgreSQL 17 changed `pg_get_viewdef()` to emit table-qualified column
names (e.g., `SELECT t.id FROM t` instead of `SELECT id FROM t`). This
causes fixture test failures because expected SQL was generated on PG ≤ 16.

**Status:** PG 17 removed from CI test matrix until schemainspect is
updated or a normalization layer is added to strip qualifiers from
view definitions.

---

## Workflow

- **CI** runs on: push to `main` or `master`, PRs targeting `main` or `master`
  - Lint (flake8, black)
  - Test matrix (4 Python versions × 3 Postgres versions = 12 jobs)
  - Coverage report

- **CD** runs on: git tags matching `v*`
  - Build package
  - Publish to PyPI
  - Create GitHub release

### `main` vs `master` branch protection (2026-08-08)

`main` is the actual GitHub default branch (`gh repo view --json defaultBranchRef`
confirms this), but only `master` has branch protection configured — 13 required
status checks (`Lint` + the 12-job test matrix), `strict` status checks, no force
pushes/deletions. `main` has **no protection at all**
(`gh api repos/.../branches/main/protection` returns 404). This means PRs merged
into `main` today get no required CI gate. The workflow trigger was fixed here
to run on both branches, but the branch protection *rule* itself still needs to
be applied to `main` — that's a repo-settings change, not a workflow file change,
and hasn't been done yet.
