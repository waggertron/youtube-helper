# tests/test_web_watch_later.py
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
    async def test_scrape_queues(self, client):
        resp = await client.post("/api/watch-later/scrape")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_export_queues(self, client):
        resp = await client.post(
            "/api/watch-later/export",
            json={"target": "spacepope videos", "threshold": 50},
        )
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_purge_queues(self, client):
        resp = await client.post(
            "/api/watch-later/purge", json={"threshold": 50}
        )
        assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_prune_exports_queues(self, client):
        resp = await client.post("/api/watch-later/prune-exports")
        assert resp.status_code == 202
