import pytest
from click.testing import CliRunner

from youtube_helper.cli.main import cli
from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists "
        "(id, title, privacy_status, video_count) "
        "VALUES (?, ?, ?, ?)",
        ("PL1", "My Favorites", "private", 10),
    )
    conn.execute(
        "INSERT INTO playlists "
        "(id, title, privacy_status, video_count) "
        "VALUES (?, ?, ?, ?)",
        ("PL2", "Watch Later Export 2026-03-02", "private", 5),
    )
    conn.execute(
        "INSERT INTO videos "
        "(id, title, channel_name, watch_progress) "
        "VALUES (?, ?, ?, ?)",
        ("V1", "Cool Video", "Cool Channel", 0.0),
    )
    conn.execute(
        "INSERT INTO playlist_videos "
        "(playlist_id, video_id, position) "
        "VALUES (?, ?, ?)",
        ("PL1", "V1", 0),
    )
    conn.commit()
    conn.close()
    return db_path


class TestPlaylistList:
    def test_lists_playlists(self, seeded_db):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["playlist", "list", "--db-path", seeded_db]
        )
        assert result.exit_code == 0
        assert "My Favorites" in result.output

    def test_empty_db_shows_message(self, db_path):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["playlist", "list", "--db-path", db_path]
        )
        assert result.exit_code == 0


class TestPlaylistShow:
    def test_shows_playlist_videos(self, seeded_db):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["playlist", "show", "favorites",
             "--db-path", seeded_db],
        )
        assert result.exit_code == 0
        assert "Cool Video" in result.output

    def test_no_match_shows_message(self, seeded_db):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["playlist", "show", "xyznonexistent",
             "--db-path", seeded_db],
        )
        assert result.exit_code == 0
        assert "No playlist matching" in result.output
