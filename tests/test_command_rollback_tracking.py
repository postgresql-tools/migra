from __future__ import unicode_literals

import io

from sqlalchemy import text
from sqlbag import S, temporary_database


def outs():
    return io.StringIO(), io.StringIO()


def _create_table(db_url, table_name, columns="id int primary key"):
    with S(db_url) as s:
        s.execute(text("CREATE TABLE {} ({});".format(table_name, columns)))


class TestRecordRollbackCli:
    def test_record_rollback_after_applied(self):
        with temporary_database(host="localhost") as db_url:
            from migra.history import ensure_history_table, record_applied

            with S(db_url) as s:
                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="abc123hash",
                    forward_sql="SELECT 1;",
                    environment_label="dev",
                )

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--record-rollback",
                    "abc123hash",
                    db_url,
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0
            assert "Rollback recorded" in out.getvalue()

            from migra.history import get_history

            with S(db_url) as s:
                entries = get_history(s)
            assert len(entries) == 1
            assert entries[0]["rollback_status"] == "rolled_back"
            assert entries[0]["rolled_back_at"] is not None

    def test_record_rollback_failed_status(self):
        with temporary_database(host="localhost") as db_url:
            from migra.history import ensure_history_table, record_applied

            with S(db_url) as s:
                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="abc123hash",
                    forward_sql="SELECT 1;",
                )

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--record-rollback",
                    "abc123hash",
                    db_url,
                    "--rollback-status",
                    "rollback_failed",
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0

            from migra.history import get_history

            with S(db_url) as s:
                entries = get_history(s)
            assert entries[0]["rollback_status"] == "rollback_failed"

    def test_record_rollback_from_file(self):
        import os
        import tempfile

        with temporary_database(host="localhost") as db_url:
            from migra.history import (
                compute_migration_hash,
                ensure_history_table,
                record_applied,
            )

            sql_content = "ALTER TABLE users DROP COLUMN email;"
            actual_hash = compute_migration_hash(sql_content)
            with S(db_url) as s:
                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash=actual_hash,
                    forward_sql=sql_content,
                )

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sql", delete=False
            ) as f:
                f.write(sql_content)
                f.flush()
                rollback_file = f.name

            try:
                from migra.command import parse_args, run

                args = parse_args(
                    [
                        "--record-rollback",
                        rollback_file,
                        db_url,
                    ]
                )
                out, err = outs()
                status = run(args, out=out, err=err)
                assert status == 0
                assert "Rollback recorded" in out.getvalue()
            finally:
                os.unlink(rollback_file)

    def test_missing_history_entry(self):
        with temporary_database(host="localhost") as db_url:
            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--record-rollback",
                    "nonexistent",
                    db_url,
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 1
            assert "No history entry found" in err.getvalue()

    def test_missing_db_url(self):
        from migra.command import parse_args, run

        args = parse_args(
            [
                "--record-rollback",
                "abc123",
            ]
        )
        out, err = outs()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "requires a database URL" in err.getvalue()


class TestStatusAfterRollback:
    def test_status_shows_rolled_back_annotation(self):
        with temporary_database(host="localhost") as db_url:
            from migra.history import (
                ensure_history_table,
                record_applied,
                record_rollback,
            )

            with S(db_url) as s:
                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="abc123",
                    forward_sql="SELECT 1;",
                )
                record_rollback(s, "abc123", status="rolled_back")

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--status",
                    db_url,
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0
            output = out.getvalue()
            assert "ROLLED BACK" in output
