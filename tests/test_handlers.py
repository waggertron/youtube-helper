# tests/test_handlers.py
from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.events import EventBroadcaster
from youtube_helper.web.handlers import register_all_handlers
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
