# tests/test_web_reset.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    """Seed the database with playlists, videos, playlist_videos, liked_videos, and queue ops."""
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title, privacy_status, video_count) "
        "VALUES ('PL1', 'Test Playlist', 'private', 2)"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V1', 'Video One', 'Channel A', 0.0)"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V2', 'Video Two', 'Channel B', 75.0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('PL1', 'V1', 0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('PL1', 'V2', 1)"
    )
    conn.execute(
        "INSERT INTO liked_videos (video_id, liked_at) "
        "VALUES ('V1', datetime('now'))"
    )
    conn.execute(
        "INSERT INTO operation_queue (type, params, status) "
        "VALUES ('sync', '{}', 'completed')"
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def app(seeded_db):
    return create_app(db_path=seeded_db)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestResetEndpoint:
    @pytest.mark.asyncio
    async def test_reset_clears_all_tables(self, client, seeded_db):
        """POST /api/reset should delete all data from all user tables."""
        # Verify data exists before reset
        conn = get_connection(seeded_db)
        assert conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM playlist_videos").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM liked_videos").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM operation_queue").fetchone()[0] == 1
        conn.close()

        # Call reset endpoint
        resp = await client.post("/api/reset")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Database cleared"

        # Verify all tables are empty
        conn = get_connection(seeded_db)
        assert conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM playlist_videos").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM liked_videos").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM operation_queue").fetchone()[0] == 0
        conn.close()

    @pytest.mark.asyncio
    async def test_reset_on_empty_database(self, db_path):
        """POST /api/reset should succeed even when the database is already empty."""
        app = create_app(db_path=db_path)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reset")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Database cleared"
