# tests/test_web_videos.py
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
        "INSERT INTO videos (id, title, channel_name) "
        "VALUES ('V1', 'Video One', 'Ch A')"
    )
    conn.execute(
        "INSERT INTO liked_videos (video_id, liked_at) "
        "VALUES ('V1', datetime('now'))"
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


@pytest.fixture
def all_videos_db(db_path):
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title) VALUES ('PL1', 'Playlist One')"
    )
    conn.execute(
        "INSERT INTO playlists (id, title) VALUES ('PL2', 'Playlist Two')"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name) "
        "VALUES ('V1', 'Video One', 'Ch A')"
    )
    conn.execute(
        "INSERT INTO videos (id, title, channel_name) "
        "VALUES ('V2', 'Video Two', 'Ch B')"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('PL1', 'V1', 0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('PL2', 'V1', 0)"
    )
    conn.execute(
        "INSERT INTO playlist_videos (playlist_id, video_id, position) "
        "VALUES ('PL1', 'V2', 1)"
    )
    conn.execute(
        "INSERT INTO liked_videos (video_id, liked_at) "
        "VALUES ('V1', datetime('now'))"
    )
    conn.commit()
    conn.close()
    return db_path


class TestAllVideos:
    @pytest.fixture
    def app(self, all_videos_db):
        return create_app(db_path=all_videos_db)

    @pytest.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_list_all_videos(self, client):
        resp = await client.get("/api/videos")
        assert resp.status_code == 200
        videos = resp.json()["videos"]
        assert len(videos) == 2

    @pytest.mark.asyncio
    async def test_includes_playlist_names(self, client):
        resp = await client.get("/api/videos")
        videos = resp.json()["videos"]
        v1 = next(v for v in videos if v["id"] == "V1")
        # V1 is in both playlists
        assert "Playlist One" in v1["playlist_names"]
        assert "Playlist Two" in v1["playlist_names"]

    @pytest.mark.asyncio
    async def test_includes_is_liked(self, client):
        resp = await client.get("/api/videos")
        videos = resp.json()["videos"]
        v1 = next(v for v in videos if v["id"] == "V1")
        v2 = next(v for v in videos if v["id"] == "V2")
        assert v1["is_liked"] == 1
        assert v2["is_liked"] is None


class TestVideoRoutes:
    @pytest.mark.asyncio
    async def test_list_liked(self, client):
        resp = await client.get("/api/videos/liked")
        assert resp.status_code == 200
        assert len(resp.json()["videos"]) == 1

    @pytest.mark.asyncio
    async def test_like_video_queues(self, client):
        resp = await client.post("/api/videos/V1/like")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()

    @pytest.mark.asyncio
    async def test_unlike_video_queues(self, client):
        resp = await client.delete("/api/videos/V1/like")
        assert resp.status_code == 202
        assert "operation_id" in resp.json()
