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
