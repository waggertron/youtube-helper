import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.watch_later.manager import WatchLaterManager


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def seeded_db(db_path):
    """Seed the DB with a Watch Later playlist and some videos."""
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO playlists (id, title, privacy_status, source) "
        "VALUES (?, ?, ?, ?)",
        ("WL", "Watch Later", "private", "browser"),
    )
    videos = [
        ("VID1", "Watched Fully", "Channel A", 90.0),
        ("VID2", "Watched Half", "Channel B", 50.0),
        ("VID3", "Barely Watched", "Channel C", 10.0),
        ("VID4", "Not Watched", "Channel D", 0.0),
        ("VID5", "Mostly Watched", "Channel A", 75.0),
    ]
    for idx, (vid_id, title, channel, progress) in enumerate(videos):
        conn.execute(
            "INSERT INTO videos "
            "(id, title, channel_name, watch_progress) "
            "VALUES (?, ?, ?, ?)",
            (vid_id, title, channel, progress),
        )
        conn.execute(
            "INSERT INTO playlist_videos "
            "(playlist_id, video_id, playlist_item_id, position) "
            "VALUES (?, ?, ?, ?)",
            ("WL", vid_id, f"PLI_{vid_id}", idx),
        )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def manager(seeded_db):
    return WatchLaterManager(seeded_db)


class TestGetWatchedVideos:
    def test_finds_videos_above_threshold(self, manager):
        watched = manager.get_watched_videos(threshold=50.0)
        ids = [v["id"] for v in watched]
        assert "VID1" in ids  # 90%
        assert "VID2" in ids  # 50%
        assert "VID5" in ids  # 75%
        assert "VID3" not in ids  # 10%
        assert "VID4" not in ids  # 0%

    def test_threshold_zero_returns_all_with_progress(self, manager):
        watched = manager.get_watched_videos(threshold=0.1)
        assert len(watched) == 4  # all except VID4


class TestGetUnwatchedVideos:
    def test_finds_videos_below_threshold(self, manager):
        unwatched = manager.get_unwatched_videos(threshold=50.0)
        ids = [v["id"] for v in unwatched]
        assert "VID3" in ids
        assert "VID4" in ids
        assert "VID1" not in ids


class TestExportPlaylistData:
    def test_exports_all_watch_later_videos(self, manager):
        data = manager.export_playlist_data("WL")
        assert len(data) == 5

    def test_export_includes_progress(self, manager):
        data = manager.export_playlist_data("WL")
        vid1 = next(v for v in data if v["id"] == "VID1")
        assert vid1["watch_progress"] == 90.0


class TestSaveScrapedVideos:
    def test_saves_scraped_data_to_db(self, db_path):
        manager = WatchLaterManager(db_path)
        scraped = [
            {
                "video_id": "NEW1",
                "title": "New Video",
                "channel": "New Channel",
                "duration_seconds": 600,
                "progress_percent": 25.0,
                "thumbnail_url": "https://example.com/thumb.jpg",
            }
        ]
        manager.save_scraped_videos(scraped)
        conn = get_connection(db_path)
        video = conn.execute(
            "SELECT * FROM videos WHERE id = 'NEW1'"
        ).fetchone()
        assert video is not None
        assert video["title"] == "New Video"
        assert video["watch_progress"] == 25.0
        rel = conn.execute(
            "SELECT * FROM playlist_videos "
            "WHERE video_id = 'NEW1' AND playlist_id = 'WL'"
        ).fetchone()
        assert rel is not None
        conn.close()


class TestRemoveVideosFromDb:
    def test_removes_videos(self, manager, seeded_db):
        removed = manager.remove_videos_from_db("WL", ["VID1", "VID2"])
        assert removed == 2
        conn = get_connection(seeded_db)
        remaining = conn.execute(
            "SELECT * FROM playlist_videos WHERE playlist_id = 'WL'"
        ).fetchall()
        assert len(remaining) == 3
        conn.close()
