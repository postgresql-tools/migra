from __future__ import unicode_literals

import io

from sqlalchemy import text
from sqlbag import S, temporary_database


def outs():
    return io.StringIO(), io.StringIO()


def _create_table(db_url, table_name, columns="id int primary key"):
    with S(db_url) as s:
        s.execute(text("CREATE TABLE {} ({});".format(table_name, columns)))


def _table_exists(db_url, table_name):
    with S(db_url) as s:
        row = s.execute(
            text(
                "SELECT 1 FROM information_schema.tables"
                " WHERE table_name = :table_name"
            ),
            {"table_name": table_name},
        ).fetchone()
    return row is not None


class TestApplyHappyPath:
    def test_apply_creates_table_in_dburl_from(self):
        with temporary_database(host="localhost") as from_db, temporary_database(
            host="localhost"
        ) as target_db:
            _create_table(target_db, "widgets")
            assert not _table_exists(from_db, "widgets")

            from migra.command import parse_args, run

            args = parse_args(["--apply", from_db, target_db])
            out, err = outs()
            status = run(args, out=out, err=err)

            assert status == 2
            assert "-- Applied " in out.getvalue()
            assert "statement(s)" in out.getvalue()
            assert _table_exists(from_db, "widgets")

    def test_apply_records_history_against_dburl_from(self):
        with temporary_database(host="localhost") as from_db, temporary_database(
            host="localhost"
        ) as target_db:
            _create_table(target_db, "widgets")

            from migra.command import parse_args, run

            args = parse_args(["--apply", from_db, target_db])
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 2

            from migra.history import ensure_history_table, get_history

            with S(from_db) as s:
                entries = get_history(s)
            assert len(entries) == 1
            assert entries[0]["rollback_status"] == "not_attempted"
            assert "CREATE TABLE" in entries[0]["forward_sql"].upper()

            # A plain --record-history (without --apply) should NOT also have
            # written a second entry into dburl_target's history table -- in
            # fact its history table should never even have been created.
            with S(target_db) as s:
                ensure_history_table(s)
                target_entries = get_history(s)
            assert target_entries == []

    def test_apply_with_env_label(self):
        with temporary_database(host="localhost") as from_db, temporary_database(
            host="localhost"
        ) as target_db:
            _create_table(target_db, "widgets")

            from migra.command import parse_args, run

            args = parse_args(["--apply", "--env-label", "prod", from_db, target_db])
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 2

            from migra.history import get_history

            with S(from_db) as s:
                entries = get_history(s)
            assert entries[0]["environment_label"] == "prod"

    def test_apply_json_output(self):
        with temporary_database(host="localhost") as from_db, temporary_database(
            host="localhost"
        ) as target_db:
            _create_table(target_db, "widgets")

            from migra.command import parse_args, run
            import json

            args = parse_args(["--apply", "--output", "json", from_db, target_db])
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 2

            data = json.loads(out.getvalue())
            assert data["apply"]["applied"] is True
            assert data["apply"]["statement_count"] == len(data["statements"])
            assert data["apply"]["history_recorded"] is True
            assert _table_exists(from_db, "widgets")


class TestApplyNoChanges:
    def test_no_diff_is_a_noop(self):
        with temporary_database(host="localhost") as from_db, temporary_database(
            host="localhost"
        ) as target_db:
            from migra.command import parse_args, run

            args = parse_args(["--apply", from_db, target_db])
            out, err = outs()
            status = run(args, out=out, err=err)

            assert status == 0
            assert "Applied" not in out.getvalue()
            # Nothing to apply, so the history table should never even be
            # created.
            assert not _table_exists(from_db, "migradiff_history")


class TestApplySafety:
    def test_destructive_change_blocked_without_force(self):
        with temporary_database(host="localhost") as from_db, temporary_database(
            host="localhost"
        ) as target_db:
            _create_table(from_db, "widgets")
            # target_db has no "widgets" table -> dropping it would be
            # destructive.

            from migra.command import parse_args, run

            args = parse_args(["--apply", from_db, target_db])
            out, err = outs()
            status = run(args, out=out, err=err)

            assert status == 1
            assert "Destructive operations detected" in err.getvalue()
            # The table must still exist -- --apply must never execute
            # anything once safe-mode has already rejected the migration.
            assert _table_exists(from_db, "widgets")

    def test_destructive_change_applied_with_force_destructive(self):
        with temporary_database(host="localhost") as from_db, temporary_database(
            host="localhost"
        ) as target_db:
            _create_table(from_db, "widgets")

            from migra.command import parse_args, run

            args = parse_args(["--apply", "--force-destructive", from_db, target_db])
            out, err = outs()
            status = run(args, out=out, err=err)

            assert status == 2
            assert not _table_exists(from_db, "widgets")


class TestApplyIncompatibleFlags:
    def test_rejected_with_from_file(self):
        from migra.command import parse_args, run

        args = parse_args(["--apply", "--from-file", "a.sql", "b.sql"])
        out, err = outs()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "--apply is not supported with --from-file" in err.getvalue()

    def test_rejected_with_promote(self):
        from migra.command import parse_args, run

        args = parse_args(["--apply", "--promote", "dev:staging"])
        out, err = outs()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "--apply is not supported with --promote" in err.getvalue()


class TestApplyMigrationHelper:
    """Unit tests against _apply_migration() directly, so we can deterministically
    force a mid-migration failure and assert atomicity -- something that's hard
    to trigger reliably by going through the full diff-generation pipeline."""

    def test_failed_statement_rolls_back_and_records_nothing(self):
        with temporary_database(host="localhost") as db_url:
            from migra.command import _apply_migration

            result = _apply_migration(
                db_url,
                [
                    "CREATE TABLE ok_table (id int primary key);",
                    "THIS IS NOT VALID SQL;",
                ],
                sql_output="CREATE TABLE ok_table (id int primary key);\n\n"
                "THIS IS NOT VALID SQL;\n\n",
                rollback_sql=None,
                env_label=None,
            )

            assert result["applied"] is False
            assert result["error"] is not None
            assert result["history_recorded"] is False

            # The whole transaction must have rolled back -- ok_table must
            # NOT exist despite being a valid statement that ran first.
            assert not _table_exists(db_url, "ok_table")
            assert not _table_exists(db_url, "migradiff_history")

    def test_successful_apply_records_history(self):
        with temporary_database(host="localhost") as db_url:
            from migra.command import _apply_migration

            sql = "CREATE TABLE widgets (id int primary key);"
            result = _apply_migration(
                db_url,
                [sql],
                sql_output=sql,
                rollback_sql="DROP TABLE widgets;",
                env_label="staging",
            )

            assert result["applied"] is True
            assert result["history_recorded"] is True
            assert _table_exists(db_url, "widgets")

            from migra.history import get_history

            with S(db_url) as s:
                entries = get_history(s)
            assert len(entries) == 1
            assert entries[0]["rollback_sql"] == "DROP TABLE widgets;"
            assert entries[0]["environment_label"] == "staging"
