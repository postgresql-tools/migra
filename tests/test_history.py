from __future__ import unicode_literals

import io

from sqlbag import S, temporary_database


def outs():
    return io.StringIO(), io.StringIO()


class TestComputeMigrationHash:
    def test_basic_hash(self):
        from migra.history import compute_migration_hash

        h1 = compute_migration_hash("ALTER TABLE users ADD COLUMN email text;")
        h2 = compute_migration_hash("ALTER TABLE users ADD COLUMN email text;")
        assert h1 == h2
        assert len(h1) == 64

    def test_whitespace_normalization(self):
        from migra.history import compute_migration_hash

        sql_a = "ALTER TABLE users ADD COLUMN email text;"
        sql_b = "  ALTER TABLE users ADD COLUMN email text;\n\n"
        assert compute_migration_hash(sql_a) == compute_migration_hash(sql_b)

    def test_trailing_whitespace_per_line(self):
        from migra.history import compute_migration_hash

        sql_a = "ALTER TABLE users ADD COLUMN email text;\nALTER TABLE posts ADD COLUMN title text;"
        sql_b = "ALTER TABLE users ADD COLUMN email text;   \nALTER TABLE posts ADD COLUMN title text;   "
        assert compute_migration_hash(sql_a) == compute_migration_hash(sql_b)

    def test_collapsed_blank_lines(self):
        from migra.history import compute_migration_hash

        sql_a = "LINE1\n\nLINE2"
        sql_b = "LINE1\n\n\n\n\nLINE2"
        assert compute_migration_hash(sql_a) == compute_migration_hash(sql_b)

    def test_different_sql_different_hash(self):
        from migra.history import compute_migration_hash

        h1 = compute_migration_hash("ALTER TABLE users ADD COLUMN email text;")
        h2 = compute_migration_hash("ALTER TABLE users DROP COLUMN email;")
        assert h1 != h2


class TestEnsureHistoryTable:
    def test_table_creation_idempotent(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import ensure_history_table

                ensure_history_table(s)
                ensure_history_table(s)

                # Verify table exists by querying it
                rows = s.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_name = 'migradiff_history'"
                ).fetchall()
                assert len(rows) == 1

                # Verify columns
                cols = s.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = 'migradiff_history' "
                    "ORDER BY ordinal_position"
                ).fetchall()
                col_names = [c[0] for c in cols]
                assert "id" in col_names
                assert "migration_hash" in col_names
                assert "checksum" in col_names
                assert "applied_at" in col_names
                assert "applied_by" in col_names
                assert "forward_sql" in col_names
                assert "rollback_sql" in col_names
                assert "rollback_status" in col_names
                assert "rolled_back_at" in col_names
                assert "rolled_back_by" in col_names
                assert "environment_label" in col_names
                assert "source" in col_names

    def test_default_rollback_status(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import ensure_history_table, record_applied

                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="abc123",
                    forward_sql="SELECT 1;",
                )
                row = s.execute(
                    "SELECT rollback_status FROM migradiff_history"
                ).fetchone()
                assert row[0] == "not_attempted"


class TestRecordAppliedAndGetAppliedHashes:
    def test_round_trip(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import (
                    ensure_history_table,
                    get_applied_hashes,
                    record_applied,
                )

                ensure_history_table(s)

                record_applied(
                    s,
                    migration_hash="hash001",
                    forward_sql="CREATE TABLE t1 (id int);",
                )
                record_applied(
                    s,
                    migration_hash="hash002",
                    forward_sql="ALTER TABLE t1 ADD COLUMN name text;",
                )

                hashes = get_applied_hashes(s)
                assert hashes == {"hash001", "hash002"}

    def test_duplicate_hash(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import (
                    ensure_history_table,
                    get_applied_hashes,
                    record_applied,
                )

                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="hash001",
                    forward_sql="CREATE TABLE t1 (id int);",
                )
                record_applied(
                    s,
                    migration_hash="hash001",
                    forward_sql="CREATE TABLE t1 (id int);",
                )
                hashes = get_applied_hashes(s)
                assert hashes == {"hash001"}

    def test_record_with_metadata(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import (
                    ensure_history_table,
                    get_history,
                    record_applied,
                )

                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="hash001",
                    migration_name="v001_create_users",
                    forward_sql="CREATE TABLE users (id int);",
                    rollback_sql="DROP TABLE users;",
                    environment_label="dev",
                    applied_by="test_user",
                )

                entries = get_history(s)
                assert len(entries) == 1
                e = entries[0]
                assert e["migration_hash"] == "hash001"
                assert e["migration_name"] == "v001_create_users"
                assert e["forward_sql"] == "CREATE TABLE users (id int);"
                assert e["rollback_sql"] == "DROP TABLE users;"
                assert e["environment_label"] == "dev"
                assert e["applied_by"] == "test_user"
                assert e["checksum"] == "hash001"
                assert e["source"] == "cli"
                assert e["rollback_status"] == "not_attempted"

    def test_record_applied_returns_id(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import ensure_history_table, record_applied

                ensure_history_table(s)
                new_id = record_applied(
                    s,
                    migration_hash="hash001",
                    forward_sql="SELECT 1;",
                )
                assert new_id is not None
                assert isinstance(new_id, int)
                assert new_id > 0


class TestRecordRollback:
    def test_update_most_recent_matching_row(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import (
                    ensure_history_table,
                    get_history,
                    record_applied,
                    record_rollback,
                )

                ensure_history_table(s)

                record_applied(
                    s,
                    migration_hash="abc123",
                    forward_sql="V1",
                )
                record_applied(
                    s,
                    migration_hash="abc123",
                    forward_sql="V2",
                )

                record_rollback(s, "abc123", status="rolled_back")
                entries = get_history(s)
                assert len(entries) == 2
                most_recent = entries[0]
                assert most_recent["forward_sql"] == "V2"
                assert most_recent["rollback_status"] == "rolled_back"
                assert most_recent["rolled_back_at"] is not None
                assert most_recent["rolled_back_by"] is not None

                older = entries[1]
                assert older["forward_sql"] == "V1"
                assert older["rollback_status"] == "not_attempted"
                assert older["rolled_back_at"] is None

    def test_rollback_failed_status(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import (
                    ensure_history_table,
                    get_history,
                    record_applied,
                    record_rollback,
                )

                ensure_history_table(s)
                record_applied(
                    s,
                    migration_hash="abc123",
                    forward_sql="SELECT 1;",
                )
                record_rollback(s, "abc123", status="rollback_failed")

                entries = get_history(s)
                assert entries[0]["rollback_status"] == "rollback_failed"

    def test_no_matching_row_raises(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import ensure_history_table, record_rollback

                ensure_history_table(s)
                import pytest

                with pytest.raises(ValueError, match="No history entry found"):
                    record_rollback(s, "nonexistent_hash")


class TestGetHistory:
    def test_empty_history(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import ensure_history_table, get_history

                ensure_history_table(s)
                entries = get_history(s)
                assert entries == []

    def test_limit(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import (
                    ensure_history_table,
                    get_history,
                    record_applied,
                )

                ensure_history_table(s)
                for i in range(5):
                    record_applied(
                        s,
                        migration_hash="hash{:03d}".format(i),
                        forward_sql="SELECT {};".format(i),
                    )

                limited = get_history(s, limit=3)
                assert len(limited) == 3
                # Most recent first
                assert limited[0]["migration_hash"] == "hash004"

                unlimited = get_history(s)
                assert len(unlimited) == 5

    def test_filter_by_environment(self):
        with temporary_database(host="localhost") as db_url:
            with S(db_url) as s:
                from migra.history import (
                    ensure_history_table,
                    get_history,
                    record_applied,
                )

                ensure_history_table(s)

                record_applied(
                    s,
                    migration_hash="hash001",
                    forward_sql="SELECT 1;",
                    environment_label="dev",
                )
                record_applied(
                    s,
                    migration_hash="hash002",
                    forward_sql="SELECT 2;",
                    environment_label="prod",
                )

                dev_entries = get_history(s, environment_label="dev")
                assert len(dev_entries) == 1
                assert dev_entries[0]["migration_hash"] == "hash001"

                prod_entries = get_history(s, environment_label="prod")
                assert len(prod_entries) == 1
                assert prod_entries[0]["migration_hash"] == "hash002"

                all_entries = get_history(s)
                assert len(all_entries) == 2
