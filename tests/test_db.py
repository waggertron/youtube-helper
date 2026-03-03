import sqlite3
from pathlib import Path
import pytest
from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import get_current_version, run_migrations


class TestConnection:
    def test_get_connection_returns_connection(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_connection_has_wal_mode(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_connection_has_foreign_keys(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        conn.close()

    def test_connection_has_row_factory(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestMigrations:
    def test_fresh_db_has_version_zero(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        assert get_current_version(db_path) == 0

    def test_run_migrations_applies_initial(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        applied = run_migrations(db_path)
        assert len(applied) > 0
        assert 1 in applied

    def test_migrations_are_idempotent(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        first_run = run_migrations(db_path)
        second_run = run_migrations(db_path)
        assert len(first_run) > 0
        assert len(second_run) == 0

    def test_version_increments_after_migration(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        assert get_current_version(db_path) >= 1

    def test_initial_schema_creates_tables(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        conn = get_connection(db_path)
        tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        assert "playlists" in tables
        assert "videos" in tables
        assert "playlist_videos" in tables
        assert "watch_history" in tables
        assert "liked_videos" in tables
        assert "downloads" in tables
        conn.close()


class TestDbCli:
    def test_db_init(self, runner, tmp_path):
        from youtube_helper.cli.main import cli
        db_path = str(tmp_path / "test.db")
        result = runner.invoke(cli, ["db", "init", "--db-path", db_path])
        assert result.exit_code == 0
        assert "Database" in result.output

    def test_db_status(self, runner, tmp_path):
        from youtube_helper.cli.main import cli
        db_path = str(tmp_path / "test.db")
        runner.invoke(cli, ["db", "init", "--db-path", db_path])
        result = runner.invoke(cli, ["db", "status", "--db-path", db_path])
        assert result.exit_code == 0
