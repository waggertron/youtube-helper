from __future__ import annotations

import sqlite3
from pathlib import Path

from youtube_helper.db.connection import get_connection

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "migrations"


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_versions (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def get_current_version(db_path: str) -> int:
    conn = get_connection(db_path)
    _ensure_version_table(conn)
    row = conn.execute("SELECT MAX(version) FROM _schema_versions").fetchone()
    version = row[0] or 0
    conn.close()
    return version


def _discover_migrations() -> list[tuple[int, str, Path]]:
    migrations = []
    if not MIGRATIONS_DIR.exists():
        return migrations
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        parts = sql_file.stem.split("_", 1)
        version = int(parts[0])
        name = parts[1] if len(parts) > 1 else sql_file.stem
        migrations.append((version, name, sql_file))
    return migrations


def run_migrations(db_path: str) -> list[int]:
    conn = get_connection(db_path)
    _ensure_version_table(conn)
    current = conn.execute("SELECT MAX(version) FROM _schema_versions").fetchone()[0] or 0
    applied = []
    for version, name, path in _discover_migrations():
        if version <= current:
            continue
        sql = path.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO _schema_versions (version, name) VALUES (?, ?)",
            (version, name),
        )
        conn.commit()
        applied.append(version)
    conn.close()
    return applied
