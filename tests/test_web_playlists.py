# tests/test_web_playlists.py
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

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


class TestPlaylistRoutes:
    @pytest.mark.asyncio
    async def test_list_playlists(self, client):
        resp = await client.get("/api/playlists")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["playlists"]) == 1
        assert data["playlists"][0]["title"] == "Test Playlist"

    @pytest.mark.asyncio
    async def test_get_playlist_videos(self, client):
        resp = await client.get("/api/playlists/PL1/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["videos"]) == 2
        assert data["videos"][0]["title"] == "Video One"

    @pytest.mark.asyncio
    async def test_get_nonexistent_playlist(self, client):
        resp = await client.get("/api/playlists/NOPE/videos")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_playlist(self, client):
        with patch(
            "youtube_helper.web.routes.playlists.handle_create_playlist",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = {"id": "PLnew", "title": "New Playlist"}
            resp = await client.post(
                "/api/playlists",
                json={"title": "New Playlist", "privacy": "private"},
            )
            assert resp.status_code == 200
            assert resp.json()["id"] == "PLnew"

    @pytest.mark.asyncio
    async def test_delete_playlist(self, client):
        with patch(
            "youtube_helper.web.routes.playlists.handle_delete_playlist",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = {"deleted": "PL1"}
            resp = await client.delete("/api/playlists/PL1")
            assert resp.status_code == 200
            assert resp.json()["deleted"] == "PL1"

    @pytest.mark.asyncio
    async def test_add_videos(self, client):
        with patch(
            "youtube_helper.web.routes.playlists.handle_add_videos",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = {"added": 1}
            resp = await client.post(
                "/api/playlists/PL1/videos", json={"video_ids": ["V3"]}
            )
            assert resp.status_code == 200
            assert resp.json()["added"] == 1

    @pytest.mark.asyncio
    async def test_remove_video(self, client):
        with patch(
            "youtube_helper.web.routes.playlists.handle_remove_video",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = {"removed": "V1"}
            resp = await client.delete("/api/playlists/PL1/videos/V1")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reorder(self, client):
        with patch(
            "youtube_helper.web.routes.playlists.handle_reorder",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = {"reordered": True}
            resp = await client.put(
                "/api/playlists/PL1/reorder", json={"video_ids": ["V2", "V1"]}
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_like_all(self, client):
        with patch(
            "youtube_helper.web.routes.playlists.handle_like_all",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = {"liked": 2}
            resp = await client.post("/api/playlists/PL1/like-all")
            assert resp.status_code == 200
            assert resp.json()["liked"] == 2

    @pytest.mark.asyncio
    async def test_like_all_already_liked(self, client, seeded_db):
        # Like both videos
        conn = get_connection(seeded_db)
        conn.execute(
            "INSERT INTO liked_videos (video_id, liked_at) "
            "VALUES ('V1', datetime('now'))"
        )
        conn.execute(
            "INSERT INTO liked_videos (video_id, liked_at) "
            "VALUES ('V2', datetime('now'))"
        )
        conn.commit()
        conn.close()
        resp = await client.post("/api/playlists/PL1/like-all")
        assert resp.status_code == 200
        assert resp.json()["message"] == "All videos already liked"

    @pytest.mark.asyncio
    async def test_playlist_videos_include_is_liked(self, client, seeded_db):
        # Like V1
        conn = get_connection(seeded_db)
        conn.execute(
            "INSERT INTO liked_videos (video_id, liked_at) "
            "VALUES ('V1', datetime('now'))"
        )
        conn.commit()
        conn.close()

        resp = await client.get("/api/playlists/PL1/videos")
        videos = resp.json()["videos"]
        v1 = next(v for v in videos if v["id"] == "V1")
        v2 = next(v for v in videos if v["id"] == "V2")
        assert v1["is_liked"] == 1
        assert v2["is_liked"] is None
