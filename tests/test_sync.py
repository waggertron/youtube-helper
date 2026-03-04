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
    client.get_video_details.return_value = {
        "VID1": {
            "id": "VID1",
            "contentDetails": {"duration": "PT3M45S"},
            "snippet": {
                "thumbnails": {
                    "medium": {"url": "https://i.ytimg.com/vi/VID1/mqdefault.jpg"}
                }
            },
        },
        "VID2": {
            "id": "VID2",
            "contentDetails": {"duration": "PT10M0S"},
            "snippet": {
                "thumbnails": {
                    "medium": {"url": "https://i.ytimg.com/vi/VID2/mqdefault.jpg"}
                }
            },
        },
    }
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


def _make_liked_api_response(items, next_page_token=None):
    """Build a mock YouTube videos().list(myRating='like') response."""
    resp = {"items": items}
    if next_page_token:
        resp["nextPageToken"] = next_page_token
    return resp


def _make_liked_item(video_id, title="Test Video", channel_id="CH1",
                     channel_title="Test Channel", duration="PT5M30S",
                     published_at="2024-06-15T12:00:00Z",
                     thumb_url="https://i.ytimg.com/vi/X/mqdefault.jpg"):
    """Build a single item as returned by videos().list(myRating='like')."""
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "channelId": channel_id,
            "channelTitle": channel_title,
            "publishedAt": published_at,
            "thumbnails": {
                "medium": {"url": thumb_url},
            },
        },
        "contentDetails": {
            "duration": duration,
        },
    }


class TestSyncLikedVideos:
    def test_upserts_videos_into_videos_table(self, db_path):
        """sync_liked_videos should insert/update rows in the videos table."""
        client = MagicMock()
        items = [
            _make_liked_item("LV1", title="Liked One", channel_id="CH_A",
                             channel_title="Channel A", duration="PT3M45S"),
            _make_liked_item("LV2", title="Liked Two", channel_id="CH_B",
                             channel_title="Channel B", duration="PT10M0S"),
        ]
        client.youtube.videos.return_value.list.return_value.execute.return_value = (
            _make_liked_api_response(items)
        )
        engine = SyncEngine(db_path, client)
        engine.sync_liked_videos()

        conn = get_connection(db_path)
        videos = conn.execute(
            "SELECT * FROM videos ORDER BY id"
        ).fetchall()
        conn.close()

        assert len(videos) == 2
        v1 = next(v for v in videos if v["id"] == "LV1")
        assert v1["title"] == "Liked One"
        assert v1["channel_id"] == "CH_A"
        assert v1["channel_name"] == "Channel A"
        assert v1["duration"] == 225  # 3*60 + 45
        v2 = next(v for v in videos if v["id"] == "LV2")
        assert v2["title"] == "Liked Two"
        assert v2["duration"] == 600  # 10*60

    def test_creates_liked_videos_entries(self, db_path):
        """sync_liked_videos should insert rows into the liked_videos table."""
        client = MagicMock()
        items = [
            _make_liked_item("LV1"),
            _make_liked_item("LV2"),
        ]
        client.youtube.videos.return_value.list.return_value.execute.return_value = (
            _make_liked_api_response(items)
        )
        engine = SyncEngine(db_path, client)
        engine.sync_liked_videos()

        conn = get_connection(db_path)
        liked = conn.execute(
            "SELECT * FROM liked_videos ORDER BY video_id"
        ).fetchall()
        conn.close()

        assert len(liked) == 2
        assert liked[0]["video_id"] == "LV1"
        assert liked[0]["liked_at"] is not None
        assert liked[0]["removed_at"] is None
        assert liked[1]["video_id"] == "LV2"

    def test_returns_correct_count(self, db_path):
        """sync_liked_videos should return the number of liked videos synced."""
        client = MagicMock()
        items = [
            _make_liked_item("LV1"),
            _make_liked_item("LV2"),
            _make_liked_item("LV3"),
        ]
        client.youtube.videos.return_value.list.return_value.execute.return_value = (
            _make_liked_api_response(items)
        )
        engine = SyncEngine(db_path, client)
        count = engine.sync_liked_videos()

        assert count == 3

    def test_pagination_fetches_all_pages(self, db_path):
        """sync_liked_videos should follow nextPageToken to fetch all pages."""
        client = MagicMock()
        page1_items = [_make_liked_item("LV1")]
        page2_items = [_make_liked_item("LV2")]
        client.youtube.videos.return_value.list.return_value.execute.side_effect = [
            _make_liked_api_response(page1_items, next_page_token="TOKEN_2"),
            _make_liked_api_response(page2_items),
        ]
        engine = SyncEngine(db_path, client)
        count = engine.sync_liked_videos()

        assert count == 2
        conn = get_connection(db_path)
        videos = conn.execute("SELECT * FROM videos").fetchall()
        liked = conn.execute("SELECT * FROM liked_videos").fetchall()
        conn.close()
        assert len(videos) == 2
        assert len(liked) == 2

    def test_idempotent_sync(self, db_path):
        """Running sync_liked_videos twice should not duplicate rows."""
        client = MagicMock()
        items = [_make_liked_item("LV1")]
        client.youtube.videos.return_value.list.return_value.execute.return_value = (
            _make_liked_api_response(items)
        )
        engine = SyncEngine(db_path, client)
        engine.sync_liked_videos()
        engine.sync_liked_videos()

        conn = get_connection(db_path)
        videos = conn.execute("SELECT * FROM videos").fetchall()
        liked = conn.execute("SELECT * FROM liked_videos").fetchall()
        conn.close()
        assert len(videos) == 1
        assert len(liked) == 1

    def test_clears_removed_at_on_re_sync(self, db_path):
        """If a video was previously unliked (removed_at set), re-syncing
        should clear removed_at."""
        # Pre-seed a soft-deleted liked video
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO videos (id, title) VALUES ('LV1', 'Old Title')"
        )
        conn.execute(
            "INSERT INTO liked_videos (video_id, liked_at, removed_at) "
            "VALUES ('LV1', '2024-01-01', '2024-06-01')"
        )
        conn.commit()
        conn.close()

        client = MagicMock()
        items = [_make_liked_item("LV1", title="Updated Title")]
        client.youtube.videos.return_value.list.return_value.execute.return_value = (
            _make_liked_api_response(items)
        )
        engine = SyncEngine(db_path, client)
        engine.sync_liked_videos()

        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT * FROM liked_videos WHERE video_id = 'LV1'"
        ).fetchone()
        video = conn.execute(
            "SELECT * FROM videos WHERE id = 'LV1'"
        ).fetchone()
        conn.close()

        assert row["removed_at"] is None
        assert video["title"] == "Updated Title"
