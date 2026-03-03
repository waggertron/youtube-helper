# tests/test_processor.py
import pytest

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.events import EventBroadcaster
from youtube_helper.web.processor import QueueProcessor
from youtube_helper.web.queue import QueueManager


class TestQueueProcessor:
    @pytest.mark.asyncio
    async def test_processes_pending_operation(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        broadcaster = EventBroadcaster()
        op_id = qm.submit("test_noop", {})
        processor = QueueProcessor(db_path, broadcaster)
        processor.register_handler("test_noop", self._noop_handler)
        await processor.process_one()
        op = qm.get_operation(op_id)
        assert op["status"] == "completed"

    @pytest.mark.asyncio
    async def test_handles_failure(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        broadcaster = EventBroadcaster()
        op_id = qm.submit("test_fail", {})
        processor = QueueProcessor(db_path, broadcaster)
        processor.register_handler("test_fail", self._fail_handler)
        await processor.process_one()
        op = qm.get_operation(op_id)
        assert op["status"] == "failed"
        assert "boom" in op["error"]

    @staticmethod
    async def _noop_handler(params, progress_callback):
        await progress_callback(100.0, "Done")

    @staticmethod
    async def _fail_handler(params, progress_callback):
        raise RuntimeError("boom")
