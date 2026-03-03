from unittest.mock import MagicMock

import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.sync.engine import SyncEngine


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def mock_playlist_client():
    client = MagicMock()
    client.list_playlists.return_value = [
        {
            "id": "PL123",
            "snippet": {"title": "My Playlist", "description": "Test"},
            "status": {"privacyStatus": "private"},
            "contentDetails": {"itemCount": 2},
        }
    ]
    client.list_playlist_items.return_value = [
        {
            "id": "PLI1",
            "snippet": {
                "title": "Video One",
                "position": 0,
                "resourceId": {"videoId": "VID1"},
                "videoOwnerChannelTitle": "Channel A",
                "videoOwnerChannelId": "CHA",
            },
            "contentDetails": {
                "videoId": "VID1",
                "videoPublishedAt": "2024-01-01T00:00:00Z",
            },
        },
        {
            "id": "PLI2",
            "snippet": {
                "title": "Video Two",
                "position": 1,
                "resourceId": {"videoId": "VID2"},
                "videoOwnerChannelTitle": "Channel B",
                "videoOwnerChannelId": "CHB",
            },
            "contentDetails": {
                "videoId": "VID2",
                "videoPublishedAt": "2024-02-01T00:00:00Z",
            },
        },
    ]
    return client


@pytest.fixture
def sync_engine(db_path, mock_playlist_client):
    return SyncEngine(db_path, mock_playlist_client)


class TestSyncPlaylists:
    def test_syncs_playlists_to_db(self, sync_engine, db_path):
        sync_engine.sync_all()
        conn = get_connection(db_path)
        playlists = conn.execute(
            "SELECT * FROM playlists"
        ).fetchall()
        assert len(playlists) == 1
        assert playlists[0]["id"] == "PL123"
        assert playlists[0]["title"] == "My Playlist"
        conn.close()

    def test_syncs_videos_to_db(self, sync_engine, db_path):
        sync_engine.sync_all()
        conn = get_connection(db_path)
        videos = conn.execute("SELECT * FROM videos").fetchall()
        assert len(videos) == 2
        conn.close()

    def test_syncs_playlist_video_relationships(
        self, sync_engine, db_path
    ):
        sync_engine.sync_all()
        conn = get_connection(db_path)
        rels = conn.execute(
            "SELECT * FROM playlist_videos"
        ).fetchall()
        assert len(rels) == 2
        assert rels[0]["playlist_id"] == "PL123"
        conn.close()

    def test_sync_is_idempotent(self, sync_engine, db_path):
        sync_engine.sync_all()
        sync_engine.sync_all()
        conn = get_connection(db_path)
        videos = conn.execute("SELECT * FROM videos").fetchall()
        assert len(videos) == 2
        conn.close()

    def test_sync_returns_stats(self, sync_engine):
        stats = sync_engine.sync_all()
        assert stats["playlists"] == 1
        assert stats["videos"] == 2
        assert stats["relationships"] == 2
