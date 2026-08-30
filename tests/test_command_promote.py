from __future__ import unicode_literals

import io

from sqlalchemy import text
from sqlbag import S, temporary_database


def outs():
    return io.StringIO(), io.StringIO()


def _create_table(db_url, table_name, columns="id int primary key"):
    with S(db_url) as s:
        s.execute(text("CREATE TABLE {} ({});".format(table_name, columns)))


def _create_schema_from_sql(db_url, sql):
    with S(db_url) as s:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                s.execute(text(stmt))


class TestPromoteHappyPath:
    def test_two_env_chain(self):
        with temporary_database(host="localhost") as dev, temporary_database(
            host="localhost"
        ) as staging:
            _create_table(dev, "users")
            _create_schema_from_sql(
                staging,
                "CREATE TABLE users (id int primary key);"
                " CREATE TABLE posts (id int primary key);",
            )

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--unsafe",
                    "--promote",
                    "{}:{}".format(dev, staging),
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0
            output = out.getvalue()
            assert "=== " in output
            assert "create table" in output or "No changes needed" in output

    def test_three_env_chain(self):
        with temporary_database(host="localhost") as dev, temporary_database(
            host="localhost"
        ) as staging, temporary_database(host="localhost") as prod:
            _create_table(dev, "users")
            _create_table(dev, "posts")
            _create_schema_from_sql(
                staging,
                "CREATE TABLE users (id int primary key);"
                " CREATE TABLE posts (id int primary key);",
            )
            _create_schema_from_sql(
                prod,
                "CREATE TABLE users (id int primary key);"
                " CREATE TABLE posts (id int primary key);"
                " CREATE TABLE comments (id int primary key);",
            )

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--unsafe",
                    "--promote",
                    "{}:{}:{}".format(dev, staging, prod),
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0


class TestPromoteConflictDetection:
    def test_staging_ahead_of_dev_conflict(self):
        with temporary_database(host="localhost") as dev, temporary_database(
            host="localhost"
        ) as staging:
            _create_table(dev, "users")
            _create_table(staging, "users")
            _create_table(staging, "posts")

            from migra.command import parse_args, run
            from migra.history import ensure_history_table, record_applied

            with S(dev) as s:
                ensure_history_table(s)
            with S(staging) as s:
                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="hash_not_in_dev",
                    forward_sql="CREATE TABLE posts (id int);",
                    environment_label="staging",
                )

            args = parse_args(
                [
                    "--unsafe",
                    "--promote",
                    "{}:{}".format(dev, staging),
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 1
            assert "CONFLICT" in err.getvalue()
            assert "hash_not_in" in err.getvalue()


class TestPromoteEmptyDiff:
    def test_identical_envs_no_output(self):
        with temporary_database(host="localhost") as dev, temporary_database(
            host="localhost"
        ) as staging:
            _create_table(dev, "users")
            _create_table(staging, "users")

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--unsafe",
                    "--promote",
                    "{}:{}".format(dev, staging),
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0
            output = out.getvalue()
            assert "No changes needed" in output


class TestPromoteSafeMode:
    def test_destructive_halts_chain(self):
        with temporary_database(host="localhost") as dev, temporary_database(
            host="localhost"
        ) as staging:
            _create_schema_from_sql(
                dev,
                "CREATE TABLE users (id int primary key);"
                " CREATE TABLE posts (id int primary key);",
            )
            _create_table(staging, "users")

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--promote",
                    "{}:{}".format(dev, staging),
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 1
            assert "Destructive" in err.getvalue()

    def test_force_destructive_allows_chain(self):
        with temporary_database(host="localhost") as dev, temporary_database(
            host="localhost"
        ) as staging:
            _create_schema_from_sql(
                dev,
                "CREATE TABLE users (id int primary key);"
                " CREATE TABLE posts (id int primary key);",
            )
            _create_table(staging, "users")

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--force-destructive",
                    "--promote",
                    "{}:{}".format(dev, staging),
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0


class TestPromoteRecordHistory:
    def test_record_history_per_hop(self):
        with temporary_database(host="localhost") as dev, temporary_database(
            host="localhost"
        ) as staging:
            _create_table(dev, "users")
            _create_schema_from_sql(
                staging,
                "CREATE TABLE users (id int primary key);"
                " CREATE TABLE posts (id int primary key);",
            )

            from migra.command import parse_args, run

            args = parse_args(
                [
                    "--unsafe",
                    "--record-history",
                    "--env-label",
                    "staging",
                    "--promote",
                    "{}:{}".format(dev, staging),
                ]
            )
            out, err = outs()
            status = run(args, out=out, err=err)
            assert status == 0

            from migra.history import get_history

            with S(staging) as s:
                entries = get_history(s)
            assert len(entries) >= 1
            assert entries[0]["environment_label"] == "staging"


class TestPromoteInvalidArgs:
    def test_single_env_error(self):
        from migra.command import parse_args, run

        args = parse_args(
            [
                "--promote",
                "dev",
            ]
        )
        out, err = outs()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "requires at least 2" in err.getvalue()

    def test_unknown_alias_error(self):
        from migra.command import parse_args, run

        args = parse_args(
            [
                "--promote",
                "dev:nonexistent_alias_xyz",
            ]
        )
        out, err = outs()
        status = run(args, out=out, err=err)
        assert status == 1
        assert "Unknown environment alias" in err.getvalue()
