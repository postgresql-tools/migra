from __future__ import unicode_literals

import hashlib
import re

from sqlalchemy import text

HISTORY_TABLE = "migradiff_history"


def compute_migration_hash(sql_text):
    normalized = _normalize_sql(sql_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_sql(sql_text):
    lines = sql_text.split("\n")
    stripped_lines = [line.rstrip() for line in lines]
    result = "\n".join(stripped_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = result.strip()
    return result


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    id              BIGSERIAL PRIMARY KEY,
    migration_hash  TEXT NOT NULL,
    migration_name  TEXT,
    checksum        TEXT NOT NULL,
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    applied_by      TEXT,
    forward_sql     TEXT NOT NULL,
    rollback_sql    TEXT,
    rollback_status TEXT NOT NULL DEFAULT 'not_attempted',
    rolled_back_at  TIMESTAMPTZ,
    rolled_back_by  TEXT,
    environment_label TEXT,
    source           TEXT NOT NULL DEFAULT 'cli'
);

CREATE INDEX IF NOT EXISTS idx_{table}_migration_hash ON {table} (migration_hash);
""".format(table=HISTORY_TABLE)


def ensure_history_table(session):
    session.execute(text(CREATE_TABLE_SQL))
    session.commit()


def _current_user(session):
    row = session.execute(text("SELECT current_user")).scalar()
    return row


def record_applied(
    session,
    *,
    migration_hash,
    migration_name=None,
    forward_sql,
    rollback_sql=None,
    environment_label=None,
    applied_by=None,
):
    if applied_by is None:
        applied_by = _current_user(session)
    session.execute(
        text("""
        INSERT INTO {table}
            (migration_hash, migration_name, checksum, forward_sql,
             rollback_sql, environment_label, applied_by)
        VALUES
            (:migration_hash, :migration_name, :checksum, :forward_sql,
             :rollback_sql, :environment_label, :applied_by)
        """.format(table=HISTORY_TABLE)),
        {
            "migration_hash": migration_hash,
            "migration_name": migration_name,
            "checksum": migration_hash,
            "forward_sql": forward_sql,
            "rollback_sql": rollback_sql,
            "environment_label": environment_label,
            "applied_by": applied_by,
        },
    )
    session.commit()
    row = session.execute(text("SELECT lastval()")).scalar()
    return row


def record_rollback(
    session,
    migration_hash,
    *,
    status="rolled_back",
    rolled_back_by=None,
):
    if rolled_back_by is None:
        rolled_back_by = _current_user(session)

    row = session.execute(
        text("""
        SELECT id FROM {table}
        WHERE migration_hash = :migration_hash
        ORDER BY applied_at DESC
        LIMIT 1
        FOR UPDATE
        """.format(table=HISTORY_TABLE)),
        {"migration_hash": migration_hash},
    ).fetchone()

    if not row:
        raise ValueError(
            "MigraDiff: No history entry found for hash {}".format(migration_hash)
        )

    session.execute(
        text("""
        UPDATE {table}
        SET rollback_status = :status,
            rolled_back_at = now(),
            rolled_back_by = :rolled_back_by
        WHERE id = :id
        """.format(table=HISTORY_TABLE)),
        {
            "status": status,
            "rolled_back_by": rolled_back_by,
            "id": row[0],
        },
    )
    session.commit()


def get_applied_hashes(session):
    rows = session.execute(text("""
        SELECT DISTINCT migration_hash FROM {table}
        """.format(table=HISTORY_TABLE))).fetchall()
    return {row[0] for row in rows}


def get_history(session, environment_label=None, limit=None):
    conditions = []
    params = {}
    if environment_label is not None:
        conditions.append("environment_label = :environment_label")
        params["environment_label"] = environment_label

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit

    rows = session.execute(
        text("""
        SELECT id, migration_hash, migration_name, checksum,
               applied_at, applied_by, forward_sql, rollback_sql,
               rollback_status, rolled_back_at, rolled_back_by,
               environment_label, source
        FROM {table}
        {where}
        ORDER BY applied_at DESC
        {limit}
        """.format(table=HISTORY_TABLE, where=where_clause, limit=limit_clause)),
        params,
    ).fetchall()

    result = []
    for row in rows:
        result.append(
            {
                "id": row[0],
                "migration_hash": row[1],
                "migration_name": row[2],
                "checksum": row[3],
                "applied_at": str(row[4]) if row[4] else None,
                "applied_by": row[5],
                "forward_sql": row[6],
                "rollback_sql": row[7],
                "rollback_status": row[8],
                "rolled_back_at": str(row[9]) if row[9] else None,
                "rolled_back_by": row[10],
                "environment_label": row[11],
                "source": row[12],
            }
        )
    return result
