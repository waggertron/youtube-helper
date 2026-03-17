# tests/test_web_watch_later.py
import json
from unittest.mock import AsyncMock, patch

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
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title, source) "
        "VALUES ('WL', 'Watch Later', 'browser')"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V1', 'Watched Video', 'Ch A', 80.0)"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name, watch_progress) "
        "VALUES ('V2', 'Unwatched Video', 'Ch B', 10.0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('WL', 'V1', 0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('WL', 'V2', 1)"
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


class TestWatchLaterRoutes:
    @pytest.mark.asyncio
    async def test_list_all(self, client):
        resp = await client.get("/api/watch-later")
        assert resp.status_code == 200
        assert len(resp.json()["videos"]) == 2

    @pytest.mark.asyncio
    async def test_watched(self, client):
        resp = await client.get(
            "/api/watch-later/watched", params={"threshold": 50}
        )
        assert resp.status_code == 200
        videos = resp.json()["videos"]
        assert len(videos) == 1
        assert videos[0]["title"] == "Watched Video"

    @pytest.mark.asyncio
    async def test_unwatched(self, client):
        resp = await client.get(
            "/api/watch-later/unwatched", params={"threshold": 50}
        )
        assert resp.status_code == 200
        videos = resp.json()["videos"]
        assert len(videos) == 1
        assert videos[0]["title"] == "Unwatched Video"

    @pytest.mark.asyncio
    async def test_import_watch_later(self, client, seeded_db):
        takeout_data = json.dumps([{
            "contentDetails": {"videoId": "NEW_VID"},
            "snippet": {"title": "New Video", "resourceId": {"videoId": "NEW_VID"}}
        }])
        resp = await client.post(
            "/api/watch-later/import",
            files={"file": ("watch-later.json", takeout_data.encode(), "application/json")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        # Verify DB
        conn = get_connection(seeded_db)
        row = conn.execute("SELECT * FROM videos WHERE id = 'NEW_VID'").fetchone()
        assert row is not None
        assert row["title"] == "New Video"
        pv = conn.execute(
            "SELECT * FROM playlist_videos WHERE playlist_id = 'WL' AND video_id = 'NEW_VID'"
        ).fetchone()
        assert pv is not None
        conn.close()

    @pytest.mark.asyncio
    async def test_export_watch_later(self, client):
        with patch("youtube_helper.web.routes.watch_later.handle_export", new_callable=AsyncMock) as mock:
            mock.return_value = {"exported": 2, "playlist_id": "PLnew"}
            resp = await client.post(
                "/api/watch-later/export",
                json={"target": "My Videos", "threshold": 50}
            )
            assert resp.status_code == 200
            assert resp.json()["exported"] == 2

    @pytest.mark.asyncio
    async def test_purge_returns_202(self, client):
        with patch("youtube_helper.browser.watch_later.purge_videos_from_watch_later", new_callable=AsyncMock) as mock:
            mock.return_value = {"removed": 1, "skipped": 0, "failed": 0}
            resp = await client.post(
                "/api/watch-later/purge",
                json={"threshold": 50, "headless": True}
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_purge_no_videos(self, client):
        """Purge with threshold so high no videos qualify returns completed."""
        resp = await client.post(
            "/api/watch-later/purge",
            json={"threshold": 99, "headless": True}
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "completed"
        assert data["removed"] == 0

    @pytest.mark.asyncio
    async def test_purge_status_idle(self, client):
        resp = await client.get("/api/watch-later/purge/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "idle"
