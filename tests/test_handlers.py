# tests/test_handlers.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from youtube_helper.db.connection import get_connection
from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.events import EventBroadcaster
from youtube_helper.web.handlers import (
    handle_delete_playlist,
    handle_like,
    handle_remove_video,
    handle_unlike,
    register_all_handlers,
)
from youtube_helper.web.processor import QueueProcessor


class TestHandlerRegistration:
    def test_all_handlers_registered(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        broadcaster = EventBroadcaster()
        processor = QueueProcessor(db_path, broadcaster)
        register_all_handlers(processor)
        expected = [
            "sync",
            "scrape_watch_later",
            "export_watch_later",
            "purge_watch_later",
            "prune_exports",
            "create_playlist",
            "delete_playlist",
            "add_videos",
            "remove_video",
            "reorder_playlist",
            "like_video",
            "unlike_video",
        ]
        for op_type in expected:
            assert op_type in processor._handlers, (
                f"Missing handler: {op_type}"
            )


@pytest.fixture
def handler_db(tmp_path):
    """Create a temp database with migrations applied and test data seeded."""
    db_path = str(tmp_path / "handler_test.db")
    run_migrations(db_path)

    conn = get_connection(db_path)
    # Create a playlist
    conn.execute(
        "INSERT INTO playlists (id, title) VALUES (?, ?)",
        ("PL1", "Test Playlist"),
    )
    # Create videos
    for vid_id in ("V1", "V2", "V3"):
        conn.execute(
            "INSERT INTO videos (id, title) VALUES (?, ?)",
            (vid_id, f"Video {vid_id}"),
        )
    # Add videos to playlist
    for idx, vid_id in enumerate(("V1", "V2", "V3")):
        conn.execute(
            "INSERT INTO playlist_videos "
            "(playlist_id, video_id, playlist_item_id, position) "
            "VALUES (?, ?, ?, ?)",
            ("PL1", vid_id, f"PLI_{vid_id}", idx),
        )
    # Add a liked video
    conn.execute(
        "INSERT INTO liked_videos (video_id, liked_at) "
        "VALUES ('V1', datetime('now'))",
    )
    conn.commit()
    conn.close()
    return db_path


def _mock_settings(db_path):
    """Create a mock Settings that points at our test database."""
    mock = MagicMock()
    mock.db_path = db_path
    return mock


def _mock_youtube():
    """Create a mock YouTube API client."""
    youtube = MagicMock()
    youtube.playlists.return_value.delete.return_value.execute.return_value = None
    youtube.videos.return_value.rate.return_value.execute.return_value = None
    return youtube


def _mock_playlist_client():
    """Create a mock PlaylistClient."""
    client = MagicMock()
    client.remove_from_playlist.return_value = None
    return client


class TestDeletePlaylistSoftDeletes:
    @pytest.mark.asyncio
    async def test_delete_playlist_soft_deletes_videos(self, handler_db):
        """playlist_videos rows get removed_at set; playlist itself is deleted."""
        youtube = _mock_youtube()
        progress = AsyncMock()

        with (
            patch(
                "youtube_helper.config.settings.Settings",
                return_value=_mock_settings(handler_db),
            ),
            patch(
                "youtube_helper.web.handlers._get_youtube_client",
                return_value=(youtube, _mock_playlist_client()),
            ),
        ):
            await handle_delete_playlist(
                {"playlist_id": "PL1"}, progress,
            )

        conn = get_connection(handler_db)

        # playlist_videos rows should still exist with removed_at set
        rows = conn.execute(
            "SELECT * FROM playlist_videos WHERE playlist_id = 'PL1'",
        ).fetchall()
        assert len(rows) == 3, "All 3 rows should still exist (soft deleted)"
        for row in rows:
            assert row["removed_at"] is not None, (
                f"Video {row['video_id']} should have removed_at set"
            )

        # Active rows (removed_at IS NULL) should be zero
        active = conn.execute(
            "SELECT * FROM playlist_videos "
            "WHERE playlist_id = 'PL1' AND removed_at IS NULL",
        ).fetchall()
        assert len(active) == 0

        # Playlist metadata itself should be hard-deleted
        pl = conn.execute(
            "SELECT * FROM playlists WHERE id = 'PL1'",
        ).fetchone()
        assert pl is None, "Playlist metadata should be hard deleted"

        conn.close()


class TestRemoveVideoSoftDeletes:
    @pytest.mark.asyncio
    async def test_remove_video_soft_deletes(self, handler_db):
        """playlist_videos row gets removed_at set, not hard deleted."""
        progress = AsyncMock()

        with (
            patch(
                "youtube_helper.config.settings.Settings",
                return_value=_mock_settings(handler_db),
            ),
            patch(
                "youtube_helper.web.handlers._get_youtube_client",
                return_value=(_mock_youtube(), _mock_playlist_client()),
            ),
        ):
            await handle_remove_video(
                {"playlist_id": "PL1", "video_id": "V2"}, progress,
            )

        conn = get_connection(handler_db)

        # Row should still exist with removed_at set
        row = conn.execute(
            "SELECT * FROM playlist_videos "
            "WHERE playlist_id = 'PL1' AND video_id = 'V2'",
        ).fetchone()
        assert row is not None, "Row should still exist after soft delete"
        assert row["removed_at"] is not None, "removed_at should be set"

        # Other videos should be unaffected
        other = conn.execute(
            "SELECT * FROM playlist_videos "
            "WHERE playlist_id = 'PL1' AND video_id = 'V1'",
        ).fetchone()
        assert other["removed_at"] is None, "V1 should not be affected"

        conn.close()


class TestUnlikeSoftDeletes:
    @pytest.mark.asyncio
    async def test_unlike_soft_deletes(self, handler_db):
        """liked_videos row gets removed_at set, not hard deleted."""
        progress = AsyncMock()

        with (
            patch(
                "youtube_helper.config.settings.Settings",
                return_value=_mock_settings(handler_db),
            ),
            patch(
                "youtube_helper.web.handlers._get_youtube_client",
                return_value=(_mock_youtube(), _mock_playlist_client()),
            ),
        ):
            await handle_unlike({"video_id": "V1"}, progress)

        conn = get_connection(handler_db)

        row = conn.execute(
            "SELECT * FROM liked_videos WHERE video_id = 'V1'",
        ).fetchone()
        assert row is not None, "Row should still exist after soft delete"
        assert row["removed_at"] is not None, "removed_at should be set"

        conn.close()


class TestLikeClearsRemovedAt:
    @pytest.mark.asyncio
    async def test_like_clears_removed_at(self, handler_db):
        """Re-liking a previously unliked video clears removed_at."""
        progress = AsyncMock()

        # First, soft-delete the liked video (simulate unlike)
        conn = get_connection(handler_db)
        conn.execute(
            "UPDATE liked_videos SET removed_at = datetime('now') "
            "WHERE video_id = 'V1'",
        )
        conn.commit()
        # Verify it's soft-deleted
        row = conn.execute(
            "SELECT * FROM liked_videos WHERE video_id = 'V1'",
        ).fetchone()
        assert row["removed_at"] is not None, "Precondition: should be soft-deleted"
        conn.close()

        # Now re-like the video
        with (
            patch(
                "youtube_helper.config.settings.Settings",
                return_value=_mock_settings(handler_db),
            ),
            patch(
                "youtube_helper.web.handlers._get_youtube_client",
                return_value=(_mock_youtube(), _mock_playlist_client()),
            ),
        ):
            await handle_like({"video_id": "V1"}, progress)

        conn = get_connection(handler_db)
        row = conn.execute(
            "SELECT * FROM liked_videos WHERE video_id = 'V1'",
        ).fetchone()
        assert row is not None, "Row should exist"
        assert row["removed_at"] is None, (
            "removed_at should be cleared after re-liking"
        )
        assert row["liked_at"] is not None, "liked_at should be set"
        conn.close()
