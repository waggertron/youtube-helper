# tests/test_web_queue_routes.py
import pytest
from httpx import ASGITransport, AsyncClient

from youtube_helper.db.migrations import run_migrations
from youtube_helper.web.app import create_app
from youtube_helper.web.queue import QueueManager


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    run_migrations(path)
    return path


@pytest.fixture
def app(db_path):
    return create_app(db_path=db_path)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestQueueRoutes:
    @pytest.mark.asyncio
    async def test_list_queue_empty(self, client):
        resp = await client.get("/api/queue")
        assert resp.status_code == 200
        assert resp.json()["operations"] == []

    @pytest.mark.asyncio
    async def test_list_queue_with_items(self, client, db_path):
        qm = QueueManager(db_path)
        qm.submit("sync", {})
        resp = await client.get("/api/queue")
        assert len(resp.json()["operations"]) == 1

    @pytest.mark.asyncio
    async def test_cancel_pending(self, client, db_path):
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        resp = await client.delete(f"/api/queue/{op_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_retry_failed(self, client, db_path):
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="failed", error="Network error")
        resp = await client.post(f"/api/queue/{op_id}/retry")
        assert resp.status_code == 200
        op = qm.get_operation(op_id)
        assert op["status"] == "pending"

    @pytest.mark.asyncio
    async def test_skip_failed(self, client, db_path):
        qm = QueueManager(db_path)
        op_id = qm.submit("sync", {})
        qm.update_operation(op_id, status="failed")
        resp = await client.post(f"/api/queue/{op_id}/skip")
        assert resp.status_code == 200
        op = qm.get_operation(op_id)
        assert op["status"] == "skipped"
