# tests/test_queue.py
import json

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.queue import QueueManager


class TestQueueManager:
    def test_submit_operation(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        assert op_id == 1

    def test_list_operations(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        qm.submit("sync", {})
        qm.submit("scrape", {"headless": True})
        ops = qm.list_operations()
        assert len(ops) == 2
        assert ops[0]["type"] == "sync"
        assert ops[1]["type"] == "scrape"

    def test_get_operation(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {"verbose": True})
        op = qm.get_operation(op_id)
        assert op["type"] == "sync"
        assert json.loads(op["params"]) == {"verbose": True}
        assert op["status"] == "pending"

    def test_update_status(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="active", progress=50.0, message="Syncing...")
        op = qm.get_operation(op_id)
        assert op["status"] == "active"
        assert op["progress"] == 50.0

    def test_cancel_pending(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        result = qm.cancel_operation(op_id)
        assert result is True
        op = qm.get_operation(op_id)
        assert op["status"] == "cancelled"

    def test_cancel_active_fails(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="active")
        result = qm.cancel_operation(op_id)
        assert result is False

    def test_next_pending(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        run_migrations(db_path)
        qm = QueueManager(db_path)
        qm.submit("sync", {})
        qm.submit("scrape", {})
        op = qm.next_pending()
        assert op["type"] == "sync"
